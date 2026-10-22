#!/usr/bin/env python3
"""ProjectRover: GPT V3.2 (3 sectores + confidence); compara con V0, V3 y V3.1 existentes.
No modifica el rover. Las llamadas a la API son de pago.
"""
import argparse
import base64
import csv
import html
import json
import os
import statistics
import time
from pathlib import Path

PROMPT_V32 = '''You are the visual perception system of an Axial SCX10 II 4x4 rover,
0.30 m wide, with approximately 0.07 m minimum ground clearance.

For immediate local navigation, assess three rover-relative corridors:
LEFT, FRONT, RIGHT. Each corridor is a possible path for the full rover,
not merely a patch of drivable ground. A corridor is passable only when
there is clearance for the rover's entire 0.30 m width without colliding
with a visible rigid obstacle in its immediate path.

The rover can traverse gravel, dirt, grass, scattered small stones,
flexible weeds and moderately uneven continuous terrain. Camera
perspective may exaggerate the size of nearby stones. Do not block a
corridor solely because of small loose stones, light vegetation or
moderately uneven ground that this off-road rover can cross.

Posts, fences, gates, walls, trunks, rigid branches, dense vegetation,
large rocks, holes, drops and water may physically block a corridor.
A drivable-looking surface underneath or beside a rigid barrier does
NOT make the corridor passable. Pay particular attention to thin posts,
horizontal fence bars, branches and barriers crossing the rover's path.
If an obstacle intersects the immediate corridor, mark it false even
when the ground itself is traversable. Do not treat an obstacle outside
the corridor as blocking it; do not assume a gap is wide enough without
visual evidence. If a possible physical collision or drop cannot be
resolved from the image, mark that corridor false and lower confidence.
Do not invent precise distances. Do not choose an action.

Return ONLY valid JSON with exactly these keys, in LEFT, FRONT, RIGHT order:
{"passable":[true,false,true],"confidence":0.85}
Confidence is a global number from 0 to 1.'''

CRITICAS = [15, 21, 23, 25, 29, 32, 33, 36, 40, 42, 44, 48, 49,
            51, 53, 55, 57, 60, 64, 66, 67, 76, 97, 99, 100, 102,
            104, 115, 127, 134, 145, 150, 154, 156, 160, 163, 170]
NAMES = ('LEFT', 'FRONT', 'RIGHT')


def load(path):
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]


def validate(text):
    data = json.loads(text)
    if not isinstance(data, dict) or set(data) != {'passable', 'confidence'}:
        raise ValueError('Campos esperados: passable y confidence')
    p = data['passable']
    if not isinstance(p, list) or len(p) != 3 or any(type(x) is not bool for x in p):
        raise ValueError('passable debe contener tres booleanos')
    c = data['confidence']
    if type(c) not in (int, float) or not 0 <= c <= 1:
        raise ValueError('confidence fuera de [0,1]')
    return data


def v0_three(data):
    m = {r['name']:bool(r['traversable']) for r in data['regions']}
    # Comparación estricta: los sectores de V0 no coinciden necesariamente con V3.
    return [m['left'] and m['front-left'],
            m['front-left'] and m['front'] and m['front-right'],
            m['front-right'] and m['right']]


def summary(values):
    if not values:
        return {}
    values = sorted(values)
    return dict(n=len(values), media_s=round(statistics.mean(values), 3),
                mediana_s=round(statistics.median(values), 3),
                p95_s=round(values[int(.95*(len(values)-1))], 3))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--repo', type=Path, default=Path.home()/'CognitiveOps')
    ap.add_argument('--baseline', type=Path, help='JSONL de V0 (original)')
    ap.add_argument('--v3', type=Path, help='JSONL de V3 anterior')
    ap.add_argument('--v31', type=Path, help='JSONL de V3.1 anterior')
    ap.add_argument('--out', type=Path, help='Carpeta de salida independiente')
    ap.add_argument('--all', action='store_true', help='Procesar las 177 fotos (por defecto solo las críticas)')
    ap.add_argument('--start', type=int, default=1)
    ap.add_argument('--end', type=int, default=177)
    ap.add_argument('--model', default='gpt-5.4')
    ap.add_argument('--reset', action='store_true', help='Repetir V3.2 y facturar nuevas llamadas')
    args = ap.parse_args()
    if not os.getenv('OPENAI_API_KEY'):
        raise SystemExit('Falta OPENAI_API_KEY')
    try:
        import cv2
        from openai import OpenAI
    except ImportError as e:
        raise SystemExit(f'Instala dependencias: pip install openai opencv-python ({e})')

    repo = args.repo.expanduser().resolve()
    v0_path = (args.baseline or repo/'benchmark_prompt_l2_gpt'/'resultados.jsonl').expanduser()
    v3_path = (args.v3 or repo/'benchmark_prompt_l2_v3'/'resultados_v3.jsonl').expanduser()
    v31_path = (args.v31 or repo/'benchmark_prompt_l2_v31'/'resultados_v31.jsonl').expanduser()
    out = (args.out or repo/'benchmark_prompt_l2_v32').expanduser()
    out.mkdir(parents=True, exist_ok=True)
    v0 = {r['foto']:r for r in load(v0_path) if r.get('variante')=='original' and r.get('valido')}
    v3 = {r['foto']:r for r in load(v3_path) if r.get('variante')=='v3' and r.get('valido')}
    v31 = {r['foto']:r for r in load(v31_path) if r.get('variante')=='v31' and r.get('valido')}
    if not v0:
        raise SystemExit(f'No hay resultados V0 originales en {v0_path}. Usa --baseline RUTA')
    if not v3:
        print(f'Aviso: no se encontraron V3 anteriores en {v3_path}; se comparará solo con V0.')
    dest = out/'resultados_v32.jsonl'
    config = dict(model=args.model, prompt=PROMPT_V32, image_size=[320,240], max_output_tokens=100)
    config_path = out/'configuracion.json'
    if config_path.exists() and not args.reset:
        prev_config=json.loads(config_path.read_text(encoding='utf-8'))
        if prev_config != config:
            raise SystemExit('Cambiaron modelo/prompt: usa otra --out o --reset para evitar mezclar resultados')
    config_path.write_text(json.dumps(config, indent=2), encoding='utf-8')
    (out/'prompt_v32.txt').write_text(PROMPT_V32, encoding='utf-8')
    if args.reset and dest.exists():
        dest.unlink()
    prev=load(dest)
    done={r['foto'] for r in prev if r.get('valido')}
    selected = range(args.start, args.end+1) if args.all else [i for i in CRITICAS if args.start<=i<=args.end]
    client = OpenAI(timeout=120, max_retries=0)
    print(f'V0: {len(v0)}; V3: {len(v3)}; V3.1: {len(v31)}. Solo se consulta a GPT para V3.2.', flush=True)
    with dest.open('a', encoding='utf-8') as handle:
        for number in selected:
            foto=f'{number:04d}.jpg'
            if foto in done:
                continue
            if foto not in v0:
                print(f'{foto}: falta V0, omitida'); continue
            image_path=repo/'merged_run'/foto
            frame=cv2.imread(str(image_path))
            if frame is None:
                raise SystemExit(f'No se encuentra foto: {image_path}')
            frame=cv2.resize(frame, (320,240))
            ok, encoded=cv2.imencode('.jpg', frame)
            if not ok:
                raise SystemExit(f'No se pudo codificar {foto}')
            url='data:image/jpeg;base64,'+base64.b64encode(encoded.tobytes()).decode('ascii')
            item=dict(foto=foto, variante='v32', modelo=args.model, valido=False, error=None)
            t=time.perf_counter()
            try:
                response=client.responses.create(model=args.model,
                    input=[{'role':'user','content':[
                        {'type':'input_text','text':PROMPT_V32},
                        {'type':'input_image','image_url':url}]}],
                    temperature=0, max_output_tokens=100)
                item['latencia_s']=round(time.perf_counter()-t,3)
                item['respuesta']=response.output_text.strip()
                item['tokens_entrada']=response.usage.input_tokens
                item['tokens_salida']=response.usage.output_tokens
                try:
                    item['parsed']=validate(item['respuesta'])
                    item['valido']=True
                except (ValueError, json.JSONDecodeError) as exc:
                    item['error_formato']=str(exc)
            except Exception as exc:
                item['latencia_s']=round(time.perf_counter()-t,3)
                item['error']=repr(exc)
            handle.write(json.dumps(item, ensure_ascii=False)+'\n')
            handle.flush()
            prev.append(item)
            print(f'{foto}: {item["latencia_s"]:.3f}s, válido={item["valido"]}', flush=True)
            if item['error']:
                raise SystemExit('Error de API: se ha parado para evitar consumo inesperado.')

    latest={r['foto']:r for r in prev if r.get('valido')}
    rows=[]
    for foto in sorted(latest):
        if foto not in v0:
            continue
        a=v0[foto]; b=latest[foto]; c=v3.get(foto); d=v31.get(foto)
        p0=v0_three(a['parsed']); p1=b['parsed']['passable']
        p3=c['parsed']['passable'] if c else None
        p31=d['parsed']['passable'] if d else None
        # Comparar además la región estrictamente central de V0 para no confundir zonas laterales.
        front_v0=next(r['traversable'] for r in a['parsed']['regions'] if r['name']=='front')
        row=dict(foto=foto, v0_3=json.dumps(p0), v3=json.dumps(p3), v31=json.dumps(p31), v32=json.dumps(p1),
                 v0_front_central=front_v0,
                 v32_libera_v0=','.join(NAMES[k] for k in range(3) if not p0[k] and p1[k]),
                 v32_bloquea_v0=','.join(NAMES[k] for k in range(3) if p0[k] and not p1[k]),
                 v32_libera_frente_central=bool(not front_v0 and p1[1]),
                 v32_vs_v3=','.join(NAMES[k] for k in range(3) if p3 is not None and p3[k]!=p1[k]),
                 v32_vs_v31=','.join(NAMES[k] for k in range(3) if p31 is not None and p31[k]!=p1[k]),
                 confianza_v3=c['parsed']['confidence'] if c else None,
                 confianza_v31=d['parsed']['confidence'] if d else None,
                 confianza_v32=b['parsed']['confidence'],
                 tiempo_v0=a['latencia_s'], tiempo_v3=c['latencia_s'] if c else None,
                 tiempo_v31=d['latencia_s'] if d else None,
                 tiempo_v32=b['latencia_s'], tokens_salida_v32=b.get('tokens_salida'))
        rows.append(row)
    with (out/'comparativa_v0_v3_v31_v32.csv').open('w',encoding='utf-8',newline='') as f:
        if rows:
            w=csv.DictWriter(f, fieldnames=rows[0].keys());w.writeheader();w.writerows(rows)
    res=dict(fotos=len(rows), v0=summary([r['tiempo_v0'] for r in rows]),
             v3=summary([r['tiempo_v3'] for r in rows if r['tiempo_v3'] is not None]),
             v31=summary([r['tiempo_v31'] for r in rows if r['tiempo_v31'] is not None]),
             v32=summary([r['tiempo_v32'] for r in rows]),
             discrepancias_v32_vs_v3=sum(bool(r['v32_vs_v3']) for r in rows),
             discrepancias_v32_vs_v31=sum(bool(r['v32_vs_v31']) for r in rows),
             v32_libera_frente_central_v0=sum(r['v32_libera_frente_central'] for r in rows),
             v32_libera_sector_v0_and=sum(len(r['v32_libera_v0'].split(',')) for r in rows if r['v32_libera_v0']),
             v32_bloquea_sector_v0_and=sum(len(r['v32_bloquea_v0'].split(',')) for r in rows if r['v32_bloquea_v0']),
             nota='V0 no es ground truth; diferencias entre 5 y 3 regiones requieren revisión visual.')
    (out/'resumen.json').write_text(json.dumps(res, indent=2, ensure_ascii=False),encoding='utf-8')
    tr=[]
    for row in rows:
        src=(repo/'merged_run'/row['foto']).resolve().as_uri()
        css=' class="alert"' if row['v32_libera_frente_central'] else ''
        tr.append(f'<tr{css}><td><img width="230" src="{html.escape(src)}"><br>{row["foto"]}</td>'
                  f'<td>{html.escape(row["v0_3"])}</td><td>{html.escape(str(row["v3"]))}</td><td>{html.escape(str(row["v31"]))}</td>'
                  f'<td>{html.escape(row["v32"])}</td><td>{html.escape(row["v32_vs_v3"])}</td><td>{html.escape(row["v32_vs_v31"])}</td>'
                  f'<td>{row["tiempo_v32"]:.3f}</td></tr>')
    page='<!doctype html><meta charset="utf-8"><style>body{font:14px sans-serif;margin:20px}table{border-collapse:collapse}td,th{border:1px solid #ccc;padding:7px}tr.alert{background:#ffdddd}pre{white-space:pre-wrap}</style>'
    page+='<h1>ProjectRover — V0 / V3 / V3.1 / V3.2</h1><p>Orden LEFT FRONT RIGHT. V0 en 3 sectores usa AND; V0 central se compara aparte. Rojo: V3.2 libera frente CENTRAL bloqueado por V0.</p>'
    page+='<pre>'+html.escape(json.dumps(res, indent=2,ensure_ascii=False))+'</pre>'
    page+='<table><tr><th>Foto</th><th>V0 AND</th><th>V3</th><th>V3.1</th><th>V3.2</th><th>Cambios vs V3</th><th>Cambios vs V3.1</th><th>Segundos V3.2</th></tr>'+''.join(tr)+'</table>'
    (out/'resultados.html').write_text(page,encoding='utf-8')
    print(json.dumps(res,indent=2,ensure_ascii=False))
    print('Archivos guardados en:',out)

if __name__=='__main__':
    main()
