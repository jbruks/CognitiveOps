#!/usr/bin/env python3
"""Benchmark ProjectRover: dos prompts VLM independientes (suelo y obstáculos).

Uso: python3 benchmark_ministral_v3.py
Requisitos: Ollama en localhost:11434 y Pillow.
Cada respuesta se guarda inmediatamente; la ejecución se puede reanudar.
"""
import base64
import html
import io
import json
import statistics
import time
import urllib.request
from pathlib import Path

from PIL import Image

IMG_DIR = Path('/home/devlin/CognitiveOps/merged_run')
OUT_DIR = Path('/home/devlin/CognitiveOps/benchmark_ministral')
MODEL = 'ministral-3:14b'
START, END = 1, 177
API_URL = 'http://localhost:11434/api/chat'
VERSION = 3

# Archivos nuevos: se conserva intacto el benchmark anterior (v2).
RESULTS_FILE = OUT_DIR / 'resultados_v3.jsonl'
HTML_FILE = OUT_DIR / 'resultados_v3.html'
ERRORS_FILE = OUT_DIR / 'errores_v3.log'
SECTORS = ('izquierda', 'centro', 'derecha')
STATES = ('LIBRE', 'BLOQUEADO', 'DUDOSO')
SOILS = ('tierra', 'grava', 'asfalto', 'cemento', 'hierba', 'roca', 'otro')

PROMPT_SUELO = """Eres la percepción visual de un rover terrestre.

Identifica únicamente el material predominante del suelo
inmediatamente frente al rover.

Elige una palabra:
tierra, grava, asfalto, cemento, hierba, roca u otro.

Describe lo visible, sin inventar detalles.
Devuelve exclusivamente JSON con la clave suelo."""

PROMPT_OBSTACULOS = """Eres un detector visual de OBJETOS físicos para un rover terrestre.

Observa la zona frontal próxima y divídela en tres sectores:
izquierda, centro y derecha.

Detecta únicamente objetos físicos visibles:

- Piedras o rocas individuales.
- Troncos y árboles.
- Arbustos y setos.
- Postes.
- Muros, paredes, vallas y verjas.
- Vehículos y personas.
- Otros objetos físicos.

Clasifica cada sector:

BLOQUEADO: hay un objeto físico visible que obstaculiza el paso.

LIBRE: no hay objetos físicos visibles que obstaculicen el sector.

DUDOSO: no puedes determinar si hay objetos por mala
visibilidad u oclusión.

No evalúes el suelo, su textura, pendiente o transitabilidad.

Una superficie de grava o roca NO es por sí sola un obstáculo.
Solo cuenta piedras individuales que sobresalgan y obstaculicen.

Ignora objetos lejanos.
No inventes distancias ni obstáculos.

Responde exclusivamente en JSON.."""

SCHEMA_SUELO = {
    'type': 'object',
    'properties': {'suelo': {'type': 'string', 'enum': list(SOILS)}},
    'required': ['suelo'],
    'additionalProperties': False,
}
SCHEMA_OBSTACULOS = {
    'type': 'object',
    'properties': {s: {'type': 'string', 'enum': list(STATES)} for s in SECTORS},
    'required': list(SECTORS),
    'additionalProperties': False,
}
METRIC_KEYS = (
    'load_duration', 'prompt_eval_count', 'prompt_eval_duration',
    'eval_count', 'eval_duration', 'total_duration',
)


def run_model(image_b64, prompt, schema):
    payload = {
        'model': MODEL,
        'messages': [{'role': 'user', 'content': prompt, 'images': [image_b64]}],
        'format': schema,
        'stream': False,
        'keep_alive': '30m',
        'options': {'temperature': 0, 'num_predict': 80, 'num_ctx': 4096},
    }
    request = urllib.request.Request(
        API_URL,
        data=json.dumps(payload).encode('utf-8'),
        headers={'Content-Type': 'application/json'},
    )
    started = time.perf_counter()
    with urllib.request.urlopen(request, timeout=600) as response:
        data = json.load(response)
    elapsed = time.perf_counter() - started
    result = json.loads(data['message']['content'])
    if set(result) != set(schema['required']):
        raise ValueError(f'Campos inesperados: {result!r}')
    for field in schema['required']:
        if result[field] not in schema['properties'][field]['enum']:
            raise ValueError(f'Valor incorrecto en {field}: {result[field]!r}')
    metrics = {key: data.get(key) for key in METRIC_KEYS}
    return result, round(elapsed, 3), metrics


def thumbnail_data_url(path):
    with Image.open(path) as image:
        image = image.convert('RGB')
        image.thumbnail((640, 480))
        buffer = io.BytesIO()
        image.save(buffer, format='JPEG', quality=75)
    return 'data:image/jpeg;base64,' + base64.b64encode(buffer.getvalue()).decode('ascii')


def append_record(record):
    with RESULTS_FILE.open('a', encoding='utf-8') as file:
        file.write(json.dumps(record, ensure_ascii=False) + '\n')


def load_previous():
    records = {}
    if RESULTS_FILE.exists():
        for line in RESULTS_FILE.read_text(encoding='utf-8').splitlines():
            if not line.strip():
                continue
            try:
                record = json.loads(line)
                if record.get('version') != VERSION or record.get('modelo') != MODEL:
                    continue
                number = record['numero']
                if not isinstance(number, int):
                    continue
                # Múltiples snapshots por imagen: prevalece el más reciente.
                records[number] = record
            except (ValueError, KeyError, TypeError):
                continue
    return records


def complete(record):
    return 'suelo' in record and 'obstaculos' in record


def build_html(records):
    rows = []
    soil_times, obstacle_times, total_times = [], [], []
    count_completed = 0
    for record in sorted(records.values(), key=lambda r: r['numero']):
        number = record['numero']
        path = IMG_DIR / record['archivo']
        image_html = (
            f'<img loading="lazy" src="{thumbnail_data_url(path)}" alt="Foto {number:04d}">'
            if path.is_file() else 'Imagen no disponible'
        )
        soil = html.escape(str(record.get('suelo', {}).get('suelo', '—')))
        obstacle = record.get('obstaculos', {})
        cells = []
        for sector in SECTORS:
            state = str(obstacle.get(sector, '—'))
            css = state.lower() if state in STATES else 'error'
            cells.append(f'<td class="{css}">{html.escape(state)}</td>')
        ts = record.get('tiempo_suelo')
        to = record.get('tiempo_obstaculos')
        tt = (ts + to) if ts is not None and to is not None else None
        if ts is not None:
            soil_times.append(ts)
        if to is not None:
            obstacle_times.append(to)
        if tt is not None:
            total_times.append(tt)
        if complete(record):
            count_completed += 1
        fmt = lambda x: f'{x:.2f}' if x is not None else '—'
        rows.append(
            f'<tr><td>{number:04d}</td><td>{image_html}</td><td>{soil}</td>'
            f'{"".join(cells)}<td>{fmt(ts)}</td><td>{fmt(to)}</td><td>{fmt(tt)}</td></tr>'
        )

    def average(values):
        return f'{statistics.mean(values):.2f} s' if values else '—'

    document = f'''<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ProjectRover | Ministral 14B · Dos prompts</title>
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
<h1>ProjectRover · Ministral 3 14B · Dos prompts independientes</h1>
<p><strong>Modelo:</strong> {html.escape(MODEL)} ·
<strong>Imágenes completadas:</strong> {count_completed}/{END - START + 1}</p>
<p><strong>Media suelo:</strong> {average(soil_times)} ·
<strong>Media obstáculos:</strong> {average(obstacle_times)} ·
<strong>Media total:</strong> {average(total_times)}</p>
<p>Cada imagen se analiza dos veces: clasificación de suelo y transitabilidad de corredores.
LIBRE es una observación visual, no autorización de movimiento.</p>
<div class="table-wrap"><table><thead><tr>
<th>Nº</th><th>Fotografía</th><th>Suelo</th><th>Izquierda</th>
<th>Centro</th><th>Derecha</th><th>Suelo (s)</th><th>Obstáculos (s)</th><th>Total (s)</th>
</tr></thead><tbody>{''.join(rows)}</tbody></table></div>
</body></html>'''
    HTML_FILE.write_text(document, encoding='utf-8')


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if not IMG_DIR.is_dir():
        raise SystemExit(f'No existe la carpeta: {IMG_DIR}')
    records = load_previous()
    print(f'Modelo: {MODEL}\nFotos: {IMG_DIR}\nCompletadas previamente: '
          f'{sum(complete(r) for r in records.values())}', flush=True)
    try:
        for number in range(START, END + 1):
            path = IMG_DIR / f'{number:04d}.jpg'
            if not path.is_file():
                print(f'[{number:04d}] No existe: omitida', flush=True)
                continue
            record = records.get(number, {
                'version': VERSION, 'modelo': MODEL,
                'numero': number, 'archivo': path.name,
            })
            if complete(record):
                continue
            print(f'[{number:04d}] Analizando...', flush=True)
            # Preparar la misma fotografía una sola vez para las dos consultas.
            image_b64 = base64.b64encode(path.read_bytes()).decode('ascii')
            for task, prompt, schema in (
                ('suelo', PROMPT_SUELO, SCHEMA_SUELO),
                ('obstaculos', PROMPT_OBSTACULOS, SCHEMA_OBSTACULOS),
            ):
                if task in record:
                    continue
                try:
                    result, seconds, metrics = run_model(image_b64, prompt, schema)
                    record[task] = result
                    record['tiempo_' + task] = seconds
                    record['metricas_' + task] = metrics
                    append_record(record)
                    records[number] = record
                    print(f'    {task}: {result} | {seconds:.2f}s', flush=True)
                except KeyboardInterrupt:
                    raise
                except Exception as error:
                    message = f'[{number:04d}] {task.upper()} ERROR: {error}'
                    print('    ' + message, flush=True)
                    with ERRORS_FILE.open('a', encoding='utf-8') as file:
                        file.write(message + '\n')
            if number % 5 == 0:
                build_html(records)
    except KeyboardInterrupt:
        print('\nInterrumpido; respuestas completadas guardadas.', flush=True)
    finally:
        build_html(records)
        print(f'\nCompletadas: {sum(complete(r) for r in records.values())}')
        print(f'HTML: {HTML_FILE}')
        print(f'JSONL: {RESULTS_FILE}')


if __name__ == '__main__':
    main()
