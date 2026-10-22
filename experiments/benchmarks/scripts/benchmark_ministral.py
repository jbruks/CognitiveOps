#!/usr/bin/env python3
"""Benchmark visual de Ministral 3 14B para ProjectRover.

Requisitos: Ollama en localhost:11434 y Pillow.
Uso: python3 benchmark_ministral.py
"""
import base64
import html
import io
import json
import statistics
import time
import urllib.error
import urllib.request
from pathlib import Path

from PIL import Image

IMG_DIR = Path('/home/devlin/CognitiveOps/merged_run')
OUT_DIR = Path('/home/devlin/CognitiveOps/benchmark_ministral')
MODEL = 'ministral-3:14b'
START, END = 1, 177
API_URL = 'http://localhost:11434/api/chat'

RESULTS_FILE = OUT_DIR / 'resultados.jsonl'
HTML_FILE = OUT_DIR / 'resultados.html'
ERRORS_FILE = OUT_DIR / 'errores.log'
SECTORS = ('izquierda', 'centro', 'derecha')
STATES = ('LIBRE', 'BLOQUEADO', 'DUDOSO')
SOILS = ('tierra', 'grava', 'asfalto', 'cemento', 'hierba', 'roca', 'otro')

PROMPT = """Eres el sistema de percepción visual de un rover terrestre.

Analiza la imagen y clasifica:

1. Suelo predominante:
tierra, grava, asfalto, cemento, hierba, roca u otro.

2. Transitabilidad aparente de los tres corredores:
izquierda, centro y derecha.

LIBRE: suelo visible, continuo y sin obstáculos ni
irregularidades importantes.

BLOQUEADO: barrera física evidente que impide el paso.

DUDOSO: piedras abundantes, terreno irregular,
pendiente incierta, vegetación que oculta el suelo
o información visual insuficiente.

Evalúa el espacio frontal próximo.
No confundas ausencia de barreras con suelo transitable.
No presupongas que el centro está libre.


Devuelve exclusivamente un json con los cuatro parametros suelo, izquierda, centro y derecha.
"""

SCHEMA = {
    'type': 'object',
    'properties': {
        'suelo': {'type': 'string', 'enum': list(SOILS)},
        **{s: {'type': 'string', 'enum': list(STATES)} for s in SECTORS},
    },
    'required': ['suelo', *SECTORS],
    'additionalProperties': False,
}


def run_model(image_path):
    payload = {
        'model': MODEL,
        'messages': [{
            'role': 'user',
            'content': PROMPT,
            'images': [base64.b64encode(image_path.read_bytes()).decode('ascii')],
        }],
        'format': SCHEMA,
        'stream': False,
        'keep_alive': '30m',
        'options': {'temperature': 0, 'num_predict': 100, 'num_ctx': 4096},
    }
    req = urllib.request.Request(
        API_URL,
        data=json.dumps(payload).encode('utf-8'),
        headers={'Content-Type': 'application/json'},
    )
    started = time.perf_counter()
    with urllib.request.urlopen(req, timeout=600) as response:
        data = json.load(response)
    elapsed = time.perf_counter() - started
    result = json.loads(data['message']['content'])
    if set(result.keys()) != {'suelo', *SECTORS}:
        raise ValueError(f'Campos inesperados: {result!r}')
    if result['suelo'] not in SOILS:
        raise ValueError(f'Suelo no válido: {result["suelo"]!r}')
    for sector in SECTORS:
        if result[sector] not in STATES:
            raise ValueError(f'Estado no válido en {sector}: {result[sector]!r}')
    return result, elapsed, data


def thumbnail_data_url(path):
    with Image.open(path) as image:
        image = image.convert('RGB')
        image.thumbnail((640, 480))
        buffer = io.BytesIO()
        image.save(buffer, format='JPEG', quality=75)
    return 'data:image/jpeg;base64,' + base64.b64encode(buffer.getvalue()).decode('ascii')


def build_html(records):
    rows = []
    valid = 0
    timings = []
    for record in sorted(records.values(), key=lambda r: r['numero']):
        result = record.get('resultado', {})
        path = IMG_DIR / record['archivo']
        image_html = (
            f'<img loading="lazy" src="{thumbnail_data_url(path)}" alt="Foto {record["numero"]:04d}">'
            if path.is_file() else '<span>Imagen no disponible</span>'
        )
        ok = all(k in result for k in ('suelo', *SECTORS))
        if ok:
            valid += 1
            timings.append(record['segundos'])
        soil = html.escape(str(result.get('suelo', '—')))
        cells = []
        for sector in SECTORS:
            value = str(result.get(sector, '—'))
            cls = value.lower() if value in STATES else 'error'
            cells.append(f'<td class="{cls}">{html.escape(value)}</td>')
        rows.append(
            f'<tr><td>{record["numero"]:04d}</td><td>{image_html}</td>'
            f'<td>{soil}</td>{"".join(cells)}<td>{record["segundos"]:.2f}</td></tr>'
        )
    average = f'{statistics.mean(timings):.2f} s' if timings else '—'
    document = f'''<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ProjectRover | Ministral 14B</title>
<style>
body{{font-family:Arial,sans-serif;margin:24px;background:#f5f6f8;color:#222}}
h1{{margin-bottom:8px}}p{{line-height:1.5}}
.table-wrap{{overflow-x:auto}}table{{width:100%;border-collapse:collapse;background:white}}
th,td{{padding:10px;border:1px solid #ddd;text-align:center}}
th{{background:#28354a;color:white;position:sticky;top:0}}
img{{max-width:480px;width:100%;height:auto}}td:nth-child(2){{min-width:240px}}
.libre{{background:#d4f5dc}}.bloqueado{{background:#ffd5d5}}
.dudoso{{background:#fff1bc}}.error{{background:#eee}}
</style></head><body>
<h1>ProjectRover · Benchmark Ministral 3 14B</h1>
<p><strong>Modelo:</strong> {html.escape(MODEL)} ·
<strong>Imágenes completadas:</strong> {valid}/{END - START + 1} ·
<strong>Latencia media:</strong> {average}</p>
<p>Suelo predominante y estado visual de los tres corredores próximos.
LIBRE no garantiza ausencia de riesgos ocultos ni autoriza por sí solo el avance.</p>
<div class="table-wrap"><table><thead><tr>
<th>Nº</th><th>Fotografía</th><th>Suelo</th><th>Izquierda</th>
<th>Centro</th><th>Derecha</th><th>Tiempo (s)</th>
</tr></thead><tbody>{''.join(rows)}</tbody></table></div>
</body></html>'''
    HTML_FILE.write_text(document, encoding='utf-8')


def load_previous():
    records = {}
    if RESULTS_FILE.exists():
        for line in RESULTS_FILE.read_text(encoding='utf-8').splitlines():
            if not line.strip():
                continue
            try:
                record = json.loads(line)
                # Excluir pruebas anteriores sin suelo o de otro prompt/modelo.
                if (record.get('version') == 2 and record.get('modelo') == MODEL
                        and all(k in record.get('resultado', {}) for k in ('suelo', *SECTORS))):
                    records[record['numero']] = record
            except (ValueError, KeyError):
                continue
    return records


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    records = load_previous()
    print(f'Modelo: {MODEL}\nFotos: {IMG_DIR}\nReanudadas: {len(records)}', flush=True)
    if not IMG_DIR.is_dir():
        raise SystemExit(f'No existe la carpeta: {IMG_DIR}')
    try:
        for number in range(START, END + 1):
            if number in records:
                continue
            path = IMG_DIR / f'{number:04d}.jpg'
            if not path.is_file():
                print(f'[{number:04d}] No existe: omitida', flush=True)
                continue
            print(f'[{number:04d}] Analizando...', flush=True)
            try:
                result, seconds, data = run_model(path)
                record = {
                    'version': 2,
                    'modelo': MODEL,
                    'numero': number,
                    'archivo': path.name,
                    'resultado': result,
                    'segundos': round(seconds, 3),
                    **{key: data.get(key) for key in (
                        'load_duration', 'prompt_eval_count', 'prompt_eval_duration',
                        'eval_count', 'eval_duration', 'total_duration')},
                }
                with RESULTS_FILE.open('a', encoding='utf-8') as file:
                    file.write(json.dumps(record, ensure_ascii=False) + '\n')
                records[number] = record
                print(f'    {result} | {seconds:.2f}s', flush=True)
                if len(records) % 5 == 0:
                    build_html(records)
            except (Exception, KeyboardInterrupt) as error:
                if isinstance(error, KeyboardInterrupt):
                    print('\nInterrumpido; resultados guardados.', flush=True)
                    break
                message = f'[{number:04d}] ERROR: {error}'
                print(message, flush=True)
                with ERRORS_FILE.open('a', encoding='utf-8') as file:
                    file.write(message + '\n')
    finally:
        build_html(records)
        print(f'\nCompletadas: {len(records)}')
        print(f'HTML: {HTML_FILE}')
        print(f'JSONL: {RESULTS_FILE}')


if __name__ == '__main__':
    main()
