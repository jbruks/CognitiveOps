#!/usr/bin/env python3
"""ProjectRover: benchmark V2.1 de TODO el conjunto 0001..0177.

Ejecutar con ~/depth-env/bin/python3 benchmark_vision_nn_v2_1.py
No modifica el worker V1 ni el rover. No exige que V1 esté presente para ejecutar.
"""
import base64
import csv
import html
import json
import os
import re
import statistics
import struct
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
WORKER = ROOT / 'vision_nn_worker_v2_1.py'
FOTOS = ROOT / 'merged_run'
OUT = ROOT / 'benchmark_vision_nn_v2_1'
PANEL = OUT / 'paneles'
V1 = ROOT / 'benchmark_vision_nn' / 'resultados.jsonl'


def read_exact(stream, n):
    data = bytearray()
    while len(data) < n:
        chunk = stream.read(n - len(data))
        if not chunk:
            raise EOFError(f'Worker finalizado. Leídos {len(data)}/{n} bytes')
        data.extend(chunk)
    return bytes(data)


def load_v1(path):
    old = {}
    if not path.exists():
        return old
    for line in path.read_text(encoding='utf-8').splitlines():
        if not line.strip():
            continue
        item = json.loads(line)
        name = item.get('archivo') or item.get('imagen')
        if name:
            old[Path(name).name] = item.get('resultado', item.get('result', item))
    return old


def pct(region, key):
    if not isinstance(region, dict):
        return None
    val = region.get(key)
    return round(100 * float(val), 2) if val is not None else None


def html_report(records, v1):
    def esc(x):
        return html.escape(str(x))
    lines = [
        '<!doctype html><html lang="es"><meta charset="utf-8">',
        '<title>ProjectRover V1 vs V2.1 · 177 fotos</title>',
        '<style>body{font:14px system-ui;margin:22px;background:#f4f5f7;color:#1b2530}',
        'table{border-collapse:collapse;background:white;width:100%}',
        'th,td{border:1px solid #cbd1d9;padding:7px;vertical-align:top}',
        'th{background:#25324a;color:white;position:sticky;top:0}',
        'img{width:950px;max-width:100%}small{color:#536173}</style>',
        '<h1>ProjectRover · benchmark V1 / V2.1</h1>',
        '<p>177 imágenes numeradas. V2.1 = mapa de profundidad + OFFSEG + ',
        'detector global + discontinuidades respecto a mediana local simétrica. ',
        'Los porcentajes son píxeles candidatos, NO precisión ni probabilidad de choque. ',
        'accepted=False en todos los resultados. Distancias sin calibrar.</p>',
        '<p>Panel: arriba [original | profundidad | OFFSEG]; ',
        'abajo [azul=global, amarillo=local, blanco=ambos | fusión roja | contraste local].</p>',
        '<table><tr><th>Foto</th><th>Panel V2.1</th><th>Sector</th><th>V1 %</th>',
        '<th>V2.1 global %</th><th>V2.1 local %</th><th>V2.1 fusión %</th>',
        '<th>R²</th><th>Tiempo s</th></tr>'
    ]
    for item in records:
        name = item['archivo']
        r = item['resultado']
        old = v1.get(name, {})
        imgname = item['numero']
        imgrel = f'paneles/{imgname:04d}.jpg'
        for j, sector in enumerate(('left', 'front', 'right')):
            reg = r.get('regions', {}).get(sector, {})
            prior = old.get('regions', {}).get(sector, {})
            lines.append('<tr>')
            if j == 0:
                lines.append(f'<td rowspan="3">{esc(name)}</td>')
                lines.append(f'<td rowspan="3"><img loading="lazy" src="{esc(imgrel)}"></td>')
            lines.extend([f'<td>{esc(sector)}</td>',
                          f'<td>{esc(pct(prior,"candidate_fraction"))}</td>',
                          f'<td>{esc(pct(reg,"global_candidate_fraction"))}</td>',
                          f'<td>{esc(pct(reg,"local_candidate_fraction"))}</td>',
                          f'<td><b>{esc(pct(reg,"candidate_fraction"))}</b></td>'])
            if j == 0:
                fit = r.get('fit') or {}
                lines.append(f'<td rowspan="3">{esc(fit.get("r2","—"))} / {esc(r.get("geometry_confidence"))}</td>')
                lines.append(f'<td rowspan="3">{esc(item.get("elapsed_s"))}</td>')
            lines.append('</tr>')
    lines.append('</table></html>')
    (OUT / 'resultados_v2_1.html').write_text('\n'.join(lines), encoding='utf-8')


def main():
    if not WORKER.exists():
        sys.exit(f'No existe {WORKER}')
    all_pics = sorted(p for p in FOTOS.glob('*.jpg') if re.fullmatch(r'\d{4}\.jpg', p.name))
    numbered = {p.name: p for p in all_pics}
    expected = [f'{i:04d}.jpg' for i in range(1, 178)]
    missing = [name for name in expected if name not in numbered]
    if missing:
        sys.exit('Faltan fotografías: ' + ', '.join(missing))
    # El conjunto del benchmark se limita a las 177 fotos esperadas;
    # ignora explícitamente yolo_test_0060.jpg y otras imágenes adicionales.
    pictures = [numbered[n] for n in expected]
    PANEL.mkdir(parents=True, exist_ok=True)
    for stale in PANEL.glob('*.jpg'):
        stale.unlink()
    env = os.environ.copy()
    env['ROVER_NN_V2_DEBUG_DIR'] = str(PANEL)
    # Compatibilidad: mismo nombre de variable de depuración que V2.
    logfile = (OUT / 'worker_stderr.log').open('w')
    worker = subprocess.Popen([sys.executable, str(WORKER)], stdin=subprocess.PIPE,
                              stdout=subprocess.PIPE, stderr=logfile, env=env, bufsize=0)
    records = []
    try:
        with (OUT / 'resultados_v2_1.jsonl').open('w', encoding='utf-8') as f:
            for i, picture in enumerate(pictures, start=1):
                start = time.perf_counter()
                payload = picture.read_bytes()
                worker.stdin.write(struct.pack('!I', len(payload)))
                worker.stdin.write(payload)
                worker.stdin.flush()
                size = struct.unpack('!I', read_exact(worker.stdout, 4))[0]
                if size > 10_000_000:
                    raise RuntimeError(f'Respuesta JSON inválida: {size} bytes')
                result = json.loads(read_exact(worker.stdout, size))
                if 'error' in result:
                    raise RuntimeError(f'Frame {picture.name}: {result["error"]}')
                record = {'numero': i, 'archivo': picture.name,
                          'elapsed_s': round(time.perf_counter() - start, 4),
                          'resultado': result}
                records.append(record)
                f.write(json.dumps(record, ensure_ascii=False) + '\n')
                f.flush()
                regs = result.get('regions', {})
                summary = ' '.join(f'{name}={pct(regs.get(name),"candidate_fraction")}%'
                                   for name in ('left','front','right'))
                print(f'[{i:03d}/177] {picture.name} {record["elapsed_s"]:.2f}s '
                      f'{summary} {"ERROR: "+str(result["error"]) if "error" in result else ""}', flush=True)
    finally:
        if worker.poll() is None:
            worker.stdin.close()
            try:
                worker.wait(timeout=30)
            except subprocess.TimeoutExpired:
                worker.kill()
                worker.wait()
        logfile.close()
    missing_panels = [f'{i:04d}.jpg' for i in range(1, 178)
                      if not (PANEL / f'{i:04d}.jpg').exists()]
    if missing_panels:
        raise RuntimeError('Faltan paneles: ' + ', '.join(missing_panels[:10]))
    old = load_v1(V1)
    with (OUT / 'comparativa_v1_v2_1.csv').open('w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['foto','sector','v1_pct','v2_1_global_pct','v2_1_local_pct','v2_1_fusion_pct',
                         'aumento_vs_v1_puntos_pct'])
        for item in records:
            r = item['resultado']
            for sector in ('left','front','right'):
                prior = pct(old.get(item['archivo'], {}).get('regions', {}).get(sector), 'candidate_fraction')
                reg = r.get('regions', {}).get(sector, {})
                combo = pct(reg, 'candidate_fraction')
                writer.writerow([item['archivo'],sector,prior,pct(reg,'global_candidate_fraction'),
                                 pct(reg,'local_candidate_fraction'),combo,
                                 round(combo-prior,2) if combo is not None and prior is not None else ''])
    html_report(records, old)
    failures = sum('error' in i['resultado'] for i in records)
    print(f'\nCompletado: {len(records)} imágenes; errores={failures}; paneles={len(list(PANEL.glob("*.jpg")))}')
    print('Resultados:', OUT)
    if not old:
        print('ATENCIÓN: no se encontró V1. Se generó V2.1 y el CSV tendrá columnas V1 vacías.')


if __name__ == '__main__':
    main()
