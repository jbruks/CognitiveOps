"""
test_gps_service.py

Script minimo para probar sensors/gps_service.py en Raspberry Pi.

Uso recomendado:

    python test_gps_service.py

O indicando puerto manualmente:

    python test_gps_service.py --port /dev/serial/by-id/TU_GPS
    python test_gps_service.py --port /dev/ttyUSB0
    python test_gps_service.py --port /dev/ttyACM0

Antes:
    pip install pyserial pynmea2
"""

import argparse
import glob
import time
import sys
from pathlib import Path


def auto_detect_gps_port():
    candidates = []

    candidates.extend(glob.glob("/dev/serial/by-id/*"))
    candidates.extend(glob.glob("/dev/ttyUSB*"))
    candidates.extend(glob.glob("/dev/ttyACM*"))

    if not candidates:
        return None

    # Preferimos by-id porque es estable entre reinicios.
    by_id = [p for p in candidates if p.startswith("/dev/serial/by-id/")]
    if by_id:
        return by_id[0]

    return candidates[0]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", default=None, help="Puerto serial del GPS")
    parser.add_argument("--baudrate", type=int, default=9600)
    parser.add_argument("--interval", type=float, default=1.0)
    args = parser.parse_args()

    # Permite importar si ejecutas desde la raiz del proyecto.
    project_root = Path(__file__).resolve().parent
    sys.path.insert(0, str(project_root))

    try:
        from sensors.gps_service import GPSService
    except ImportError:
        # Fallback si gps_service.py esta en el mismo directorio.
        from gps_service import GPSService

    port = args.port or auto_detect_gps_port()

    if not port:
        print("No se ha encontrado puerto GPS.")
        print("Prueba:")
        print("  ls -l /dev/serial/by-id/")
        print("  ls -l /dev/ttyUSB*")
        print("  ls -l /dev/ttyACM*")
        return

    print(f"Usando puerto GPS: {port}")
    print(f"Baudrate: {args.baudrate}")
    print("Arrancando GPSService...")

    gps = GPSService(port=port, baudrate=args.baudrate)

    try:
        gps.start()
        print("GPSService arrancado. Esperando datos...\n")

        while True:
            state = gps.get_state()

            print("----- GPS STATE -----")
            print(f"fix_ok:        {state['gps_fix_ok']}")
            print(f"position:      {state['position']}")
            print(f"altitude_m:    {state['altitude_m']}")
            print(f"speed_mps:     {state['speed_mps']}")
            print(f"heading_deg:   {state['estimated_heading_deg']}")
            print(f"heading_card:  {state['estimated_heading_cardinal']}")
            print(f"moved_recent:  {state['distance_moved_recent_m']}")
            print(f"movement:      {state['movement_state']}")
            print(f"confidence:    {state['confidence']}")
            print(f"satellites:    {state['num_satellites']}")
            print(f"hdop:          {state['hdop']}")
            print(f"fix_quality:   {state['fix_quality']}")
            print(f"age_s:         {state['last_update_age_s']}")
            print(f"reason:        {state['reason']}")
            print()

            time.sleep(args.interval)

    except KeyboardInterrupt:
        print("\nParando GPSService...")

    finally:
        gps.stop()
        print("GPSService detenido.")


if __name__ == "__main__":
    main()
