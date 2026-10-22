#!/usr/bin/env python3

import csv
import json
import os
import struct
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path.home() / "CognitiveOps"

FOTOS = ROOT / "merged_run"
WORKER = ROOT / "vision_nn_worker_v2.py"

SALIDA = ROOT / "benchmark_vision_nn_v2"
PANELES = SALIDA / "paneles_v2"
JSONL = SALIDA / "resultados_v2.jsonl"
CSV = SALIDA / "comparativa_v1_v2.csv"

V1 = ROOT / "benchmark_vision_nn" / "resultados.jsonl"

SALIDA.mkdir(parents=True, exist_ok=True)
PANELES.mkdir(parents=True, exist_ok=True)

fotos = sorted(FOTOS.glob("*.jpg"))

if not fotos:
    raise SystemExit(f"No se encontraron fotografías en {FOTOS}")

if not WORKER.exists():
    raise SystemExit(f"No existe {WORKER}")

print(f"Worker: {WORKER}")
print(f"Fotos: {len(fotos)}")
print(f"Resultados: {SALIDA}")
print(flush=True)

env = os.environ.copy()
env["ROVER_NN_V2_DEBUG_DIR"] = str(PANELES)

worker = subprocess.Popen(
    [sys.executable, str(WORKER)],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=(SALIDA / "worker_stderr.log").open("w"),
    env=env,
    bufsize=0,
)

def read_exact(stream, n):
    data = bytearray()

    while len(data) < n:
        chunk = stream.read(n - len(data))

        if not chunk:
            raise RuntimeError(
                "El worker terminó antes de devolver "
                f"{n} bytes"
            )

        data.extend(chunk)

    return bytes(data)


resultados = []

try:
    with JSONL.open("w", encoding="utf-8") as output:

        for i, foto in enumerate(fotos, 1):

            inicio = time.perf_counter()

            print(
                f"[{i:03d}/{len(fotos):03d}] "
                f"{foto.name} ... ",
                end="",
                flush=True,
            )

            datos = foto.read_bytes()

            worker.stdin.write(
                struct.pack("!I", len(datos))
            )
            worker.stdin.write(datos)
            worker.stdin.flush()

            header = read_exact(worker.stdout, 4)

            size = struct.unpack("!I", header)[0]

            payload = read_exact(worker.stdout, size)

            resultado = json.loads(payload)

            resultado["imagen"] = foto.name

            output.write(
                json.dumps(resultado, ensure_ascii=False) + "\n"
            )
            output.flush()

            resultados.append(resultado)

            tiempo = time.perf_counter() - inicio

            if "error" in resultado:
                print(
                    f"ERROR: {resultado['error']}",
                    flush=True,
                )
            else:
                regiones = resultado.get("regions", {})

                def porcentaje(sector):
                    return 100 * regiones.get(
                        sector, {}
                    ).get("candidate_fraction", 0)

                print(
                    f"{tiempo:.2f}s | "
                    f"I={porcentaje('left'):.1f}% "
                    f"C={porcentaje('front'):.1f}% "
                    f"D={porcentaje('right'):.1f}%",
                    flush=True,
                )

finally:
    if worker.poll() is None:
        worker.stdin.close()
        worker.wait(timeout=30)


# ============================================================
# COMPARACIÓN CON V1
# ============================================================

def cargar_v1(path):
    datos = {}

    if not path.exists():
        return datos

    for numero, linea in enumerate(
        path.read_text(encoding="utf-8").splitlines(), 1
    ):
        if not linea.strip():
            continue

        registro = json.loads(linea)

        # Admitir diferentes nombres de identificación.
        nombre = (
            registro.get("imagen")
            or registro.get("photo")
            or registro.get("filename")
            or registro.get("file")
            or f"{numero:04d}.jpg"
        )

        nombre = Path(str(nombre)).name
        if nombre.isdigit():
            nombre = f"{int(nombre):04d}.jpg"

        # Algunas versiones del benchmark almacenan
        # la respuesta del worker dentro de "result".
        respuesta = registro.get("result", registro)

        datos[nombre] = respuesta

    return datos


v1 = cargar_v1(V1)

with CSV.open("w", newline="", encoding="utf-8") as f:

    writer = csv.writer(f)

    writer.writerow([
        "imagen",
        "sector",
        "v1_candidatos_pct",
        "v2_global_pct",
        "v2_local_pct",
        "v2_combinado_pct",
        "incremento_v2_pct",
    ])

    for resultado in resultados:

        nombre = resultado["imagen"]

        anterior = v1.get(nombre, {})

        for sector in ("left", "front", "right"):

            r1 = anterior.get("regions", {}).get(sector, {})
            r2 = resultado.get("regions", {}).get(sector, {})

            viejo = r1.get("candidate_fraction")
            global_v2 = r2.get("global_candidate_fraction")
            local_v2 = r2.get("local_candidate_fraction")
            nuevo = r2.get("candidate_fraction")

            def pct(valor):
                return (
                    round(100 * float(valor), 2)
                    if valor is not None
                    else None
                )

            incremento = (
                round(100 * (nuevo - viejo), 2)
                if nuevo is not None and viejo is not None
                else None
            )

            writer.writerow([
                nombre,
                sector,
                pct(viejo),
                pct(global_v2),
                pct(local_v2),
                pct(nuevo),
                incremento,
            ])


correctas = sum(
    1 for r in resultados if "error" not in r
)

print("\n====================================")
print("BENCHMARK V2 FINALIZADO")
print("====================================")
print(f"Imágenes procesadas: {len(resultados)}")
print(f"Imágenes correctas:  {correctas}")
print(f"Errores:             {len(resultados) - correctas}")
print(f"JSONL:               {JSONL}")
print(f"Paneles:             {PANELES}")
print(f"Comparativa:         {CSV}")
