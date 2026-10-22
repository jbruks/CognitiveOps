#!/usr/bin/env python3
"""ProjectRover: benchmark del worker Depth Anything V2 + OFFSEG (sin LLM).

Uso:
    python3 benchmark_vision_nn.py
    python3 benchmark_vision_nn.py --start 1 --end 177
    python3 benchmark_vision_nn.py --reset

Ejecutar en el ZBook, desde ~/CognitiveOps. No modifica vision_nn_worker.py.
"""
import argparse
import base64
import html
import io
import json
import os
import shutil
import statistics
import struct
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

ROOT = Path('/home/devlin/CognitiveOps')
IMG_DIR = ROOT / 'merged_run'
WORKER = ROOT / 'vision_nn_worker.py'
OUT = ROOT / 'benchmark_vision_nn'
VERSION = 1

# Se instrumenta una COPIA temporal del worker, no el original.
# El punto de inserción existe en la versión backup/laptop-20261021.
MARKER = '    # ========================================================\n    # RETURN JSON\n    # ========================================================'
INSTRUMENT = '''    # BENCHMARK_DIAGNOSTICS (only in transient copy, not original worker)
    if os.environ.get("ROVER_NN_DEBUG_FILE") and result.get("source") == "vision_nn_fusion":
        try:
            diagnostic = {"depth_score": depth_score, "off_mask": off_mask}
            if fit is not None:
                diagnostic.update({
                    "expected": expected,
                    "residual": residual,
                    "candidates": candidates.astype(np.uint8),
                    "valid": valid.astype(np.uint8),
                    "distance": distance,
                })
            np.savez_compressed(os.environ["ROVER_NN_DEBUG_FILE"], **diagnostic)
        except Exception as debug_exc:
            log("Benchmark diagnostic error: " + str(debug_exc))

'''


def read_exact(stream, n):
    chunks = []
    remaining = n
    while remaining:
        chunk = stream.read(remaining)
        if not chunk:
            raise EOFError('El worker terminó antes de devolver una respuesta.')
        chunks.append(chunk)
        remaining -= len(chunk)
    return b''.join(chunks)


def instrument_worker(original: Path, target: Path):
    code = original.read_text(encoding='utf-8')
    if code.count(MARKER) != 1:
        raise RuntimeError('No encuentro el punto de instrumentación en vision_nn_worker.py; no modificaré el original.')
    # Añadir os al worker instrumentado; no depende de cambios al archivo original.
    code = 'import os\n' + code if not code.startswith('#!') else code.replace('\n', '\nimport os\n', 1)
    code = code.replace(MARKER, INSTRUMENT + MARKER)
    target.write_text(code, encoding='utf-8')


def jpeg_thumb(path, max_width=520):
    with Image.open(path) as im:
        im = im.convert('RGB')
        im.thumbnail((max_width, 400))
        b = io.BytesIO()
        im.save(b, format='JPEG', quality=75)
    return 'data:image/jpeg;base64,' + base64.b64encode(b.getvalue()).decode('ascii')


def to_rgb_colormap(depth):
    finite = np.isfinite(depth)
    if not finite.any():
        return np.zeros((*depth.shape, 3), dtype=np.uint8)
    lo, hi = np.percentile(depth[finite], [2, 98])
    norm = np.clip((np.nan_to_num(depth, nan=lo) - lo) / max(hi - lo, 1e-6) * 255, 0, 255).astype('uint8')
    return cv2.cvtColor(cv2.applyColorMap(norm, cv2.COLORMAP_TURBO), cv2.COLOR_BGR2RGB)


def make_panels(image_path: Path, npz_path: Path, number: int, vis_dir: Path):
    """Graba paneles JPEG pequeños para el HTML; muestra datos reales del worker."""
    original = np.asarray(Image.open(image_path).convert('RGB'))
    h, w = original.shape[:2]
    panel = original.copy()
    for x in (w // 3, 2 * w // 3):
        cv2.line(panel, (x, 0), (x, h - 1), (255, 255, 255), 2)
    images = [panel]
    if npz_path.exists():
        with np.load(npz_path) as z:
            depth = z['depth_score']
            off = z['off_mask']
            depth_rgb = to_rgb_colormap(depth)
            colors = np.array([[80, 80, 80], [45, 170, 70], [225, 160, 40], [200, 70, 180]], dtype=np.uint8)
            off_rgb = colors[np.clip(off, 0, 3)]
            overlay = original.copy()
            if 'candidates' in z:
                cand = z['candidates'].astype(bool)
                overlay[cand] = (0.4 * overlay[cand] + 0.6 * np.array([255, 40, 40])).astype(np.uint8)
            images += [depth_rgb, off_rgb, overlay]
    else:
        images += [np.full_like(original, 150) for _ in range(3)]
    titles = ['Original · sectores', 'Depth Anything · relativo', 'OFFSEG · clases 0/1/2/3', 'Candidatos · rojo']
    thumb_w = 420
    panel_w = thumb_w
    panel_h = int(round(h * thumb_w / w))
    canvas = Image.new('RGB', (2 * panel_w, 2 * (panel_h + 30)), '#f1f3f6')
    from PIL import ImageDraw
    draw = ImageDraw.Draw(canvas)
    for i, (array, title) in enumerate(zip(images, titles)):
        im = Image.fromarray(array).resize((panel_w, panel_h), Image.Resampling.BILINEAR)
        x = (i % 2) * panel_w
        y = (i // 2) * (panel_h + 30)
        canvas.paste(im, (x, y + 25))
        draw.text((x + 8, y + 5), title, fill='#142034')
    vis_dir.mkdir(parents=True, exist_ok=True)
    dest = vis_dir / f'{number:04d}.jpg'
    canvas.save(dest, quality=78, optimize=True)
    return dest


def load_previous(file: Path):
    records = {}
    if file.exists():
        for line in file.read_text(encoding='utf-8').splitlines():
            try:
                r = json.loads(line)
                if r.get('benchmark_version') == VERSION:
                    records[int(r['numero'])] = r
            except (ValueError, KeyError, TypeError):
                pass
    return records


def fmt(value, digits=3):
    return '—' if value is None else f'{value:.{digits}f}'


def build_html(records, image_dir, out_dir, start, end):
    timings = [r['elapsed_s'] for r in records.values() if r.get('elapsed_s') is not None]
    rows = []
    for n in sorted(records):
        r = records[n]
        d = r.get('resultado', {})
        regions = d.get('regions') or {}
        panels = out_dir / 'panels' / f'{n:04d}.jpg'
        visual = f'<img loading="lazy" src="{jpeg_thumb(panels, 840)}">' if panels.exists() else 'Sin visualización'
        def region_cell(name):
            v = regions.get(name) or {}
            return ('<td><small>candidatos: ' + fmt(v.get('candidate_fraction'), 4) + '<br>'
                    + 'OFFSEG transitable: ' + fmt(v.get('traversable_fraction'), 4) + '<br>'
                    + 'p25 distancia: ' + fmt(v.get('distance_p25_m')) + ' m</small></td>')
        fit = d.get('fit') or {}
        note = html.escape(str(d.get('error', '')))
        rows.append(f'<tr><td>{n:04d}</td><td>{visual}</td>'
                    + region_cell('left') + region_cell('front') + region_cell('right')
                    + f'<td>{html.escape(str(d.get("geometry_confidence", "—")))}<br>'
                    + f'R²: {fmt(fit.get("r2"), 4)}<br>'
                    + f'inliers: {fmt(fit.get("inliers"), 3)}<br>'
                    + f'temporal: {html.escape(str(d.get("temporal_stability", "—")))}</td>'
                    + f'<td>{fmt(d.get("depth_time_s"))}</td><td>{fmt(d.get("offseg_time_s"))}</td>'
                    + f'<td>{fmt(r.get("elapsed_s"))}</td><td>{note}</td></tr>')
    mean = fmt(statistics.mean(timings)) if timings else '—'
    median = fmt(statistics.median(timings)) if timings else '—'
    document = '''<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>ProjectRover · Benchmark Vision NN</title><style>
body{font:14px Arial,sans-serif;margin:20px;color:#263242;background:#f5f6f8}h1{margin-bottom:8px}
.table{overflow-x:auto}table{border-collapse:collapse;background:white;width:100%}th,td{border:1px solid #d8dce3;padding:8px;text-align:center;vertical-align:middle}
th{background:#25324a;color:white;position:sticky;top:0}img{width:840px;max-width:100%;height:auto}td:nth-child(2){min-width:440px}
small{line-height:1.7}p{line-height:1.5}</style></head><body>
<h1>ProjectRover · Benchmark Depth Anything V2 + OFFSEG</h1>
<p>''' + f'{len(records)}/{end-start+1} imágenes · tiempo medio {mean} s · mediana {median} s' + '''</p>
<p><b>Paneles:</b> profundidad relativa (no metros); OFFSEG: etiquetas numéricas sin nombres de clases verificados;
 candidatos: diferencias positivas respecto al plano estimado. Las distancias p25 son <b>estimaciones geométricas no calibradas</b>.
 El campo <code>accepted</code> permanece en False por diseño del worker original. No autoriza movimiento.</p>
<div class="table"><table><thead><tr><th>Foto</th><th>Original / Profundidad / OFFSEG / Candidatos</th>
<th>Izquierda</th><th>Centro</th><th>Derecha</th><th>Geometría</th><th>Depth s</th><th>OFFSEG s</th><th>Total s</th><th>Error</th></tr></thead><tbody>''' + ''.join(rows) + '''</tbody></table></div></body></html>'''
    (out_dir / 'resultados.html').write_text(document, encoding='utf-8')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--start', type=int, default=1)
    ap.add_argument('--end', type=int, default=177)
    ap.add_argument('--images', type=Path, default=IMG_DIR)
    ap.add_argument('--worker', type=Path, default=WORKER)
    ap.add_argument('--out', type=Path, default=OUT)
    ap.add_argument('--reset', action='store_true', help='Reinicia resultados; conserva originales')
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    if args.reset:
        for name in ('resultados.jsonl', 'resultados.html', 'errores.log'):
            (args.out / name).unlink(missing_ok=True)
        shutil.rmtree(args.out / 'panels', ignore_errors=True)
    if not args.worker.is_file():
        sys.exit(f'Falta {args.worker}. Restaura vision_nn_worker.py antes de ejecutar.')
    if not args.images.is_dir():
        sys.exit(f'No existe la carpeta {args.images}')
    result_file = args.out / 'resultados.jsonl'
    records = load_previous(result_file)
    pending = [n for n in range(args.start, args.end + 1) if n not in records and (args.images / f'{n:04d}.jpg').is_file()]
    print(f'Worker: {args.worker}\nFotos: {args.images}\nPendientes: {len(pending)}', flush=True)
    if not pending:
        build_html(records, args.images, args.out, args.start, args.end)
        print(f'Informe: {args.out / "resultados.html"}')
        return
    with tempfile.TemporaryDirectory(prefix='rover_nn_') as tmp:
        # Copia temporal situada fuera del proyecto: el worker usa rutas absolutas para OFFSEG.
        work_copy = Path(tmp) / 'worker_instrumented.py'
        diagnostics = Path(tmp) / 'debug.npz'
        instrument_worker(args.worker, work_copy)
        env = os.environ.copy()
        env['ROVER_NN_DEBUG_FILE'] = str(diagnostics)
        # Conectar stderr a un log para evitar saturar un pipe sin lector.
        with (args.out / 'worker_stderr.log').open('a', encoding='utf-8') as log:
            proc = subprocess.Popen([sys.executable, '-u', str(work_copy)], stdin=subprocess.PIPE,
                                    stdout=subprocess.PIPE, stderr=log, env=env, bufsize=0)
            try:
                for idx, n in enumerate(pending, 1):
                    path = args.images / f'{n:04d}.jpg'
                    print(f'[{n:04d}] ({idx}/{len(pending)})...', end=' ', flush=True)
                    diagnostics.unlink(missing_ok=True)
                    start_time = time.perf_counter()
                    try:
                        payload = path.read_bytes()
                        proc.stdin.write(struct.pack('!I', len(payload)) + payload)
                        proc.stdin.flush()
                        size = struct.unpack('!I', read_exact(proc.stdout, 4))[0]
                        if size > 10_000_000:
                            raise RuntimeError(f'Tamaño de respuesta imposible: {size}')
                        result = json.loads(read_exact(proc.stdout, size))
                        elapsed = time.perf_counter() - start_time
                        try:
                            make_panels(path, diagnostics, n, args.out / 'panels')
                        except Exception as e:
                            print(f'Advertencia: no se pudo generar el panel: {e}', flush=True)
                        record = {'benchmark_version': VERSION, 'numero': n, 'archivo': path.name,
                                  'elapsed_s': round(elapsed, 4), 'resultado': result}
                        with result_file.open('a', encoding='utf-8') as f:
                            f.write(json.dumps(record, ensure_ascii=False, allow_nan=False) + '\n')
                        records[n] = record
                        print(f'{elapsed:.2f}s · geometría={result.get("geometry_confidence", "—")} · '
                              f'error={result.get("error", "—")}', flush=True)
                        if len(records) % 5 == 0:
                            build_html(records, args.images, args.out, args.start, args.end)
                    except (BrokenPipeError, EOFError, ValueError, RuntimeError) as e:
                        with (args.out / 'errores.log').open('a', encoding='utf-8') as f:
                            f.write(f'[{n:04d}] {e}\n')
                        print(f'ERROR: {e} (ver worker_stderr.log)', flush=True)
                        break
            except KeyboardInterrupt:
                print('\nInterrumpido. Puedes reanudar ejecutando el mismo comando.', flush=True)
            finally:
                if proc.poll() is None:
                    proc.terminate()
                    try:
                        proc.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                        proc.wait()
                build_html(records, args.images, args.out, args.start, args.end)
    print(f'\nProcesadas: {len(records)}\nHTML: {args.out / "resultados.html"}\nJSONL: {result_file}')


if __name__ == '__main__':
    main()
