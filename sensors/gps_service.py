"""
gps_service.py

Modulo puro de GPS para Raspberry Pi con GPS USB/serial.

Responsabilidades:
- Leer mensajes NMEA desde un GPS conectado por USB.
- Mantener la ultima posicion valida.
- Validar calidad basica del fix.
- Mantener historico de posiciones.
- Estimar movimiento, velocidad y heading a partir del historico GPS.
- Devolver un estado limpio para que otros modulos lo usen.

No contiene:
- destino
- mision
- ruta
- L2/L3/L4
- decisiones tacticas

Dependencias:
    pip install pyserial pynmea2

Uso basico:

    from gps_service import GPSService

    gps = GPSService(port="/dev/serial/by-id/usb-XXXX", baudrate=9600)
    gps.start()

    while True:
        state = gps.get_state()
        print(state)

    gps.stop()

Notas:
- El heading GPS solo es fiable si el rover se ha desplazado varios metros.
- Para micro-movimientos de 20-50 cm, el GPS no da orientacion instantanea fiable.
"""

from __future__ import annotations

import math
import threading
import time
from dataclasses import dataclass, asdict
from typing import Optional, List, Dict, Any

from utils.xlogger import XLogger


try:
    import serial
except ImportError:
    serial = None

try:
    import pynmea2
except ImportError:
    pynmea2 = None


EARTH_RADIUS_M = 6371000.0


@dataclass
class GPSPosition:
    lat: float
    lon: float
    timestamp: float
    altitude_m: Optional[float] = None
    speed_mps: Optional[float] = None
    num_satellites: Optional[int] = None
    hdop: Optional[float] = None
    fix_quality: Optional[int] = None


@dataclass
class GPSState:
    gps_fix_ok: bool
    position: Optional[Dict[str, float]]
    altitude_m: Optional[float]
    speed_mps: Optional[float]
    estimated_heading_deg: Optional[float]
    estimated_heading_cardinal: str
    distance_moved_recent_m: Optional[float]
    movement_state: str
    confidence: str
    num_satellites: Optional[int]
    hdop: Optional[float]
    fix_quality: Optional[int]
    last_update_age_s: Optional[float]
    reason: str


class GPSService:
    """
    Servicio puro de GPS.

    Este modulo solo sabe:
    - donde esta el rover
    - si el fix GPS parece valido
    - hacia donde se ha movido recientemente
    - cuanto se ha movido recientemente

    No sabe:
    - a donde quiere ir el rover
    - que mision hay
    - que accion debe ejecutarse
    """

    def __init__(
        self,
        #port: str = "/dev/ttyUSB0",
        port: str = "/dev/serial/by-id/usb-u-blox_AG_-_www.u-blox.com_u-blox_7_-_GPS_GNSS_Receiver-if00",
        baudrate: int = 9600,
        history_size: int = 30,
        min_heading_distance_m: float = 3.0,
        stale_after_s: float = 5.0,
        max_good_hdop: float = 2.5,
        min_good_satellites: int = 5,
        moving_speed_threshold_mps: float = 0.15,
    ):
        self.port = port
        self.baudrate = baudrate
        self.history_size = history_size
        self.min_heading_distance_m = min_heading_distance_m
        self.stale_after_s = stale_after_s
        self.max_good_hdop = max_good_hdop
        self.min_good_satellites = min_good_satellites
        self.moving_speed_threshold_mps = moving_speed_threshold_mps

        self._current: Optional[GPSPosition] = None
        self._history: List[GPSPosition] = []

        self._serial = None
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Ciclo de vida
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Abre el puerto serial e inicia la lectura GPS en segundo plano."""
        XLogger.log("class GPSService: start: ", "begin")
        if serial is None:
            raise ImportError("Falta pyserial. Instala con: pip install pyserial")
        if pynmea2 is None:
            raise ImportError("Falta pynmea2. Instala con: pip install pynmea2")

        if self._running:
            return

        self._serial = serial.Serial(
            self.port,
            self.baudrate,
            timeout=1,
        )
        self._running = True
        self._thread = threading.Thread(target=self._read_loop, daemon=True)
        self._thread.start()
        XLogger.log("class GPSService: start: ", " end ok")

    def stop(self) -> None:
        """Detiene la lectura y cierra el puerto serial."""
        self._running = False

        if self._thread is not None:
            self._thread.join(timeout=2.0)

        if self._serial is not None:
            try:
                self._serial.close()
            except Exception:
                pass

        self._thread = None
        self._serial = None

    # ------------------------------------------------------------------
    # Estado publico
    # ------------------------------------------------------------------

    def get_state(self) -> Dict[str, Any]:
        """Devuelve el estado GPS actual como diccionario estable."""
        XLogger.log("class GPSService: get_state: ", "begin")
        with self._lock:
            current = self._current
            history = list(self._history)

        now = time.time()
        fix_ok, reason, confidence = self._evaluate_fix(current, now)

        estimated_heading = self._estimate_heading_from_history(history)
        distance_recent = self._distance_between_history_edges(history)
        movement_state = self._estimate_movement_state(current, distance_recent)

        state = GPSState(
            gps_fix_ok=fix_ok,
            position=(
                {"lat": current.lat, "lon": current.lon}
                if current is not None
                else None
            ),
            altitude_m=current.altitude_m if current else None,
            speed_mps=round(current.speed_mps, 3) if current and current.speed_mps is not None else None,
            estimated_heading_deg=round(estimated_heading, 1) if estimated_heading is not None else None,
            estimated_heading_cardinal=cardinal_from_bearing(estimated_heading),
            distance_moved_recent_m=round(distance_recent, 2) if distance_recent is not None else None,
            movement_state=movement_state,
            confidence=confidence,
            num_satellites=current.num_satellites if current else None,
            hdop=current.hdop if current else None,
            fix_quality=current.fix_quality if current else None,
            last_update_age_s=round(now - current.timestamp, 2) if current else None,
            reason=reason,
        )
        XLogger.log("class GPSService: get_state: state obtained: state: ", state)

        return asdict(state)

    def get_position(self) -> Optional[GPSPosition]:
        """Devuelve la ultima posicion como objeto GPSPosition."""
        with self._lock:
            return self._current

    def get_history(self) -> List[GPSPosition]:
        """Devuelve una copia del historico de posiciones."""
        with self._lock:
            return list(self._history)

    # ------------------------------------------------------------------
    # Inyeccion para tests/simulacion
    # ------------------------------------------------------------------

    def update_position_for_test(
        self,
        lat: float,
        lon: float,
        altitude_m: Optional[float] = None,
        speed_mps: Optional[float] = None,
        num_satellites: Optional[int] = 8,
        hdop: Optional[float] = 1.5,
        fix_quality: Optional[int] = 1,
    ) -> None:
        """Permite probar el servicio sin GPS fisico."""
        pos = GPSPosition(
            lat=lat,
            lon=lon,
            timestamp=time.time(),
            altitude_m=altitude_m,
            speed_mps=speed_mps,
            num_satellites=num_satellites,
            hdop=hdop,
            fix_quality=fix_quality,
        )
        self._store_position(pos)

    # ------------------------------------------------------------------
    # Loop interno
    # ------------------------------------------------------------------

    def _read_loop(self) -> None:
        while self._running:
            try:
                raw = self._serial.readline().decode("ascii", errors="ignore").strip()
                if not raw.startswith("$"):
                    continue

                msg = pynmea2.parse(raw)
                pos = self._position_from_nmea(msg)

                if pos is not None:
                    self._store_position(pos)

            except Exception:
                # En produccion podeis conectar esto a XLogger.
                # No conviene romper el hilo por una frase NMEA corrupta.
                continue

    def _position_from_nmea(self, msg) -> Optional[GPSPosition]:
        """
        Extrae posicion desde mensajes NMEA comunes.
        Soporta principalmente GGA y RMC.
        """
        now = time.time()
        sentence_type = getattr(msg, "sentence_type", None)

        # GGA: fix quality, satelites, HDOP, altitud.
        if sentence_type == "GGA":
            if not msg.latitude or not msg.longitude:
                return None

            fix_quality = int(msg.gps_qual) if str(msg.gps_qual).isdigit() else 0
            num_satellites = int(msg.num_sats) if str(msg.num_sats).isdigit() else None

            try:
                hdop = float(msg.horizontal_dil)
            except Exception:
                hdop = None

            try:
                altitude_m = float(msg.altitude)
            except Exception:
                altitude_m = None

            return GPSPosition(
                lat=float(msg.latitude),
                lon=float(msg.longitude),
                timestamp=now,
                altitude_m=altitude_m,
                num_satellites=num_satellites,
                hdop=hdop,
                fix_quality=fix_quality,
            )

        # RMC: posicion, estado y velocidad sobre suelo.
        if sentence_type == "RMC":
            if getattr(msg, "status", None) != "A":
                return None
            if not msg.latitude or not msg.longitude:
                return None

            speed_mps = None
            try:
                # spd_over_grnd viene en nudos.
                speed_mps = float(msg.spd_over_grnd) * 0.514444
            except Exception:
                pass

            return GPSPosition(
                lat=float(msg.latitude),
                lon=float(msg.longitude),
                timestamp=now,
                speed_mps=speed_mps,
                fix_quality=1,
            )

        return None

    def _store_position(self, pos: GPSPosition) -> None:
        with self._lock:
            # Si RMC llega sin calidad y ya habia GGA reciente,
            # preservamos satelites/hdop/altitud anteriores.
            if self._current is not None:
                if pos.num_satellites is None:
                    pos.num_satellites = self._current.num_satellites
                if pos.hdop is None:
                    pos.hdop = self._current.hdop
                if pos.altitude_m is None:
                    pos.altitude_m = self._current.altitude_m
                if pos.speed_mps is None:
                    pos.speed_mps = self._current.speed_mps

            self._current = pos
            self._history.append(pos)

            if len(self._history) > self.history_size:
                self._history = self._history[-self.history_size:]

    # ------------------------------------------------------------------
    # Evaluacion GPS
    # ------------------------------------------------------------------

    def _evaluate_fix(
        self,
        current: Optional[GPSPosition],
        now: float,
    ) -> tuple[bool, str, str]:
        if current is None:
            return False, "No GPS position available", "NONE"

        age = now - current.timestamp
        if age > self.stale_after_s:
            return False, "GPS position is stale", "LOW"

        if current.fix_quality is not None and current.fix_quality <= 0:
            return False, "GPS has no valid fix", "LOW"

        confidence = "MEDIUM"

        if current.num_satellites is not None:
            if current.num_satellites < self.min_good_satellites:
                return True, "GPS fix valid but satellite count is low", "LOW"

        if current.hdop is not None:
            if current.hdop > self.max_good_hdop:
                return True, "GPS fix valid but HDOP is high", "LOW"

        if (
            current.num_satellites is not None
            and current.num_satellites >= self.min_good_satellites
            and current.hdop is not None
            and current.hdop <= self.max_good_hdop
        ):
            confidence = "HIGH"

        return True, "GPS fix valid", confidence

    def _estimate_heading_from_history(
        self,
        history: List[GPSPosition],
    ) -> Optional[float]:
        """
        Estima heading por desplazamiento GPS.
        Devuelve grados:
            0=N, 90=E, 180=S, 270=W

        Solo devuelve heading si hay desplazamiento suficiente.
        """
        if len(history) < 2:
            return None

        newest = history[-1]

        for oldest in history:
            d = haversine_distance_m(
                oldest.lat,
                oldest.lon,
                newest.lat,
                newest.lon,
            )
            if d >= self.min_heading_distance_m:
                return bearing_deg(
                    oldest.lat,
                    oldest.lon,
                    newest.lat,
                    newest.lon,
                )

        return None

    def _distance_between_history_edges(
        self,
        history: List[GPSPosition],
    ) -> Optional[float]:
        if len(history) < 2:
            return None

        oldest = history[0]
        newest = history[-1]

        return haversine_distance_m(
            oldest.lat,
            oldest.lon,
            newest.lat,
            newest.lon,
        )

    def _estimate_movement_state(
        self,
        current: Optional[GPSPosition],
        distance_recent: Optional[float],
    ) -> str:
        if current is None:
            return "UNKNOWN"

        if current.speed_mps is not None:
            if current.speed_mps >= self.moving_speed_threshold_mps:
                return "MOVING"
            return "STATIONARY"

        if distance_recent is None:
            return "UNKNOWN"

        if distance_recent >= self.min_heading_distance_m:
            return "MOVING"

        return "STATIONARY_OR_NOISY"


# ----------------------------------------------------------------------
# Funciones geograficas puras
# ----------------------------------------------------------------------

def haversine_distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(d_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return EARTH_RADIUS_M * c


def bearing_deg(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Bearing inicial desde punto 1 hacia punto 2.
    0=N, 90=E, 180=S, 270=W.
    """
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_lambda = math.radians(lon2 - lon1)

    y = math.sin(d_lambda) * math.cos(phi2)
    x = (
        math.cos(phi1) * math.sin(phi2)
        - math.sin(phi1) * math.cos(phi2) * math.cos(d_lambda)
    )

    theta = math.atan2(y, x)
    return (math.degrees(theta) + 360.0) % 360.0


def normalize_angle_deg(angle: float) -> float:
    """Normaliza un angulo a rango [-180, 180]."""
    return (angle + 180.0) % 360.0 - 180.0


def cardinal_from_bearing(deg: Optional[float]) -> str:
    if deg is None:
        return "UNKNOWN"

    directions = [
        "N", "NE", "E", "SE",
        "S", "SW", "W", "NW",
    ]
    idx = int((deg + 22.5) // 45) % 8
    return directions[idx]
