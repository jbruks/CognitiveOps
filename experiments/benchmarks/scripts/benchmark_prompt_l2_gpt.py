#!/usr/bin/env python3
"""Benchmark V0 prompt exacto vs V1 compacto de PerceptionModule.observe_llm.

No importa perception_module.py ni arranca cámara/GPS: extrae el literal AST.
No modifica el rover, procesa 0001..0177 por defecto. API OpenAI de pago.
"""
import argparse
import ast
import base64
import csv
import html
import json
import os
from pathlib import Path
import statistics
import time

PROMPT_COMPACT = '''You are the visual perception system of an Axial SCX10 II 4x4 rover, ~0.30 m wide, ~0.07 m minimum ground clearance. It traverses gravel, dirt, scattered small stones, grass, pavement, and moderately uneven continuous ground. Foreground perspective exaggerates stone size.

Assess ONLY immediate local navigation in exactly five rover-relative regions: left, front-left, front, front-right, right. For each return traversable (boolean) and risk (low|medium|high).

Mark obstacles only if they meaningfully restrict or endanger THIS rover: large rocks, rigid objects, walls, trunks, dense/rigid vegetation, holes, drops, water or genuinely blocked areas. Gravel, small loose stones, sparse grass, flexible weeds and minor unevenness are terrain, not individual obstacles, even when visually prominent. Do not assume an uncertain hazard is safely passable. Use image evidence only; don't choose an action or describe unrelated objects. Estimate region and distance_m for each reported obstacle.

Return ONLY valid JSON, with all five regions exactly once, obstacles possibly empty and confidence between 0 and 1:
{"regions":[{"name":"left","traversable":true,"risk":"low"},{"name":"front-left","traversable":true,"risk":"low"},{"name":"front","traversable":true,"risk":"low"},{"name":"front-right","traversable":true,"risk":"low"},{"name":"right","traversable":true,"risk":"low"}],"obstacles":[],"confidence":0.8}
Each obstacle: {"region":"front","distance_m":1.0}.'''


def extract_prompt(path):
    tree = ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == 'observe_llm':
            for sub in ast.walk(node):
                if isinstance(sub, ast.Assign) and any(isinstance(x, ast.Name) and x.id == 'perception_prompt' for x in sub.targets):
                    if isinstance(sub.value, ast.Constant) and isinstance(sub.value.value, str):
                        return sub.value.value
    raise RuntimeError('No se encuentra el texto literal perception_prompt en observe_llm de ' + str(path))


def normalized(raw):
    x = json.loads(raw)
    regions = x.get('regions', [])
    expected = ('left', 'front-left', 'front', 'front-right', 'right')
    if not isinstance(regions, list) or sorted(str(z.get('name')) for z in regions) != sorted(expected):
        raise ValueError('No aparecen las cinco regiones correctamente')
    for z in regions:
        if not isinstance(z.get('traversable'), bool) or z.get('risk') not in ('low','medium','high'):
            raise ValueError('Región con formato incorrecto')
    obs = x.get('obstacles', [])
    if not isinstance(obs, list):
        raise ValueError('obstacles no es lista')
    for o in obs:
        if o.get('region') not in expected:
            raise ValueError('Región de obstáculo desconocida')
    conf = x.get('confidence')
    if not isinstance(conf, (int, float)) or not 0 <= float(conf) <= 1:
        raise ValueError('confidence inválida')
    return x


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--repo', type=Path, default=Path.home()/'CognitiveOps')
    ap.add_argument('--images', type=Path)
    ap.add_argument('--out', type=Path)
    ap.add_argument('--model', default='gpt-5.4')
    ap.add_argument('--start', type=int, default=1)
    ap.add_argument('--end', type=int, default=177)
    ap.add_argument('--variants', default='original,compacto', help='original,compacto o una de ellas')
    ap.add_argument('--max-output-tokens', type=int, default=500)
    ap.add_argument('--reset', action='store_true')
    args = ap.parse_args()
    from openai import OpenAI
    import cv2
    if not os.getenv('OPENAI_API_KEY'):
        raise SystemExit('Falta OPENAI_API_KEY')
    repo = args.repo.expanduser()
    imgdir = (args.images or repo/'merged_run').expanduser()
    out = (args.out or repo/'benchmark_prompt_l2_gpt').expanduser()
    out.mkdir(parents=True, exist_ok=True)
    original = extract_prompt(repo/'perception_module.py')
    prompts = {'original': original, 'compacto': PROMPT_COMPACT}
    variants = [x.strip() for x in args.variants.split(',') if x.strip()]
    if any(v not in prompts for v in variants):
        raise SystemExit('Variantes: original,compacto')
    (out/'prompts.json').write_text(json.dumps({v:prompts[v] for v in variants},ensure_ascii=False,indent=2),encoding='utf-8')
    paths = [(i, imgdir/f'{i:04d}.jpg') for i in range(args.start, args.end+1)]
    missing = [str(p) for _,p in paths if not p.is_file()]
    if missing: raise SystemExit('Faltan imágenes: '+', '.join(missing[:8]))
    jsonl = out/'resultados.jsonl'
    if args.reset and jsonl.exists():
        jsonl.unlink()
    results = []
    if jsonl.exists():
        for line in jsonl.read_text(encoding='utf-8').splitlines():
            if line.strip():
                results.append(json.loads(line))
    done = {(x['foto'],x['variante']) for x in results if x.get('error') is None}
    client = OpenAI(timeout=120.0, max_retries=0)
    print(f'Modelo: {args.model} | Fotos: {len(paths)} | Variantes: {variants}',flush=True)
    print(f'Prompt original: {len(original)} caracteres | compacto: {len(PROMPT_COMPACT)} caracteres',flush=True)
    print('ATENCIÓN: llamadas facturables a la API de OpenAI.',flush=True)
    with jsonl.open('a',encoding='utf-8') as fout:
        for i,path in paths:
            # MISMO preprocesado que observe_llm: resize OpenCV y JPEG por defecto.
            frame = cv2.imread(str(path))
            if frame is None: raise RuntimeError('No se puede leer '+str(path))
            frame = cv2.resize(frame, (320,240))
            ok,jpg = cv2.imencode('.jpg',frame)
            if not ok: raise RuntimeError('Falló JPEG '+str(path))
            image_url='data:image/jpeg;base64,'+base64.b64encode(jpg.tobytes()).decode('ascii')
            for v in variants:
                key=(path.name,v)
                if key in done:
                    print(f'[{i:04d}] {v}: ya procesada',flush=True)
                    continue
                start=time.perf_counter()
                rec={'foto':path.name,'variante':v,'modelo':args.model,'error':None}
                try:
                    r=client.responses.create(model=args.model,input=[{'role':'user','content':[
                        {'type':'input_text','text':prompts[v]},
                        {'type':'input_image','image_url':image_url},
                    ]}],temperature=0,max_output_tokens=args.max_output_tokens)
                    rec['latencia_s']=round(time.perf_counter()-start,3)
                    rec['respuesta']=r.output_text.strip()
                    rec['tokens_entrada']=getattr(getattr(r,'usage',None),'input_tokens',None)
                    rec['tokens_salida']=getattr(getattr(r,'usage',None),'output_tokens',None)
                    rec['tokens_total']=getattr(getattr(r,'usage',None),'total_tokens',None)
                    try:
                        rec['parsed']=normalized(rec['respuesta'])
                        rec['valido']=True
                    except Exception as e:
                        rec['parsed']=None
                        rec['valido']=False
                        rec['error_formato']=str(e)
                except Exception as e:
                    rec['latencia_s']=round(time.perf_counter()-start,3)
                    rec['error']=repr(e)
                    rec['valido']=False
                results.append(rec)
                fout.write(json.dumps(rec,ensure_ascii=False)+'\n');fout.flush()
                print(f'[{i:04d}] {v:8s} {rec["latencia_s"]:6.2f}s '
                      f'valido={rec["valido"]} error={str(rec["error"])[:85]}',flush=True)
                if rec['error']:
                    raise SystemExit('Error de API. Ejecución detenida; vuelve a lanzar para reanudar.')
    csvfile=out/'resultados.csv'
    fields=['foto','variante','modelo','latencia_s','tokens_entrada','tokens_salida','tokens_total','valido','error']
    with csvfile.open('w',encoding='utf-8',newline='') as f:
        wr=csv.DictWriter(f,fields,extrasaction='ignore');wr.writeheader();wr.writerows(results)
    summary={}
    for v in variants:
        rows=[r for r in results if r['variante']==v and r.get('error') is None]
        times=[r['latencia_s'] for r in rows]
        summary[v]={'n':len(rows),'validos':sum(r.get('valido',False) for r in rows),
                    'latencia_media_s':round(statistics.mean(times),3) if times else None,
                    'latencia_mediana_s':round(statistics.median(times),3) if times else None,
                    'latencia_p95_s':round(sorted(times)[int(.95*(len(times)-1))],3) if times else None,
                    'tokens_entrada_total':sum(r.get('tokens_entrada') or 0 for r in rows),
                    'tokens_salida_total':sum(r.get('tokens_salida') or 0 for r in rows)}
    (out/'resumen.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False),encoding='utf-8')
    # Comparación por fotografía, sin afirmar que la coincidencia implica seguridad.
    pairs={}
    for r in results:
        if r.get('parsed') is not None:
            pairs.setdefault(r['foto'],{})[r['variante']]=r['parsed']
    disagreements=[]
    for foto,pair in pairs.items():
        if 'original' not in pair or 'compacto' not in pair: continue
        a={x['name']:x for x in pair['original']['regions']}
        b={x['name']:x for x in pair['compacto']['regions']}
        changed=[name for name in a if a[name].get('traversable') != b[name].get('traversable')
                 or a[name].get('risk') != b[name].get('risk')]
        disagreements.append({'foto':foto,'regiones_distintas':changed,
                              'num_obstaculos_original':len(pair['original']['obstacles']),
                              'num_obstaculos_compacto':len(pair['compacto']['obstacles'])})
    (out/'diferencias.json').write_text(json.dumps(disagreements,indent=2,ensure_ascii=False),encoding='utf-8')
    rows=[]
    for r in results:
        original=html.escape(r.get('respuesta','') or r.get('error',''))
        rows.append('<tr><td>'+html.escape(r['foto'])+'</td><td>'+html.escape(r['variante'])+'</td><td>'+str(r.get('latencia_s',''))+'</td><td>'+str(r.get('tokens_entrada',''))+'</td><td>'+str(r.get('tokens_salida',''))+'</td><td>'+str(r.get('valido',''))+'</td><td><pre>'+original+'</pre></td></tr>')
    report='''<!doctype html><meta charset="utf-8"><title>Benchmark Prompt L2 GPT</title>
<style>body{font:14px system-ui;margin:22px;color:#253047}table{border-collapse:collapse;width:100%}td,th{border:1px solid #ddd;padding:8px;vertical-align:top}th{background:#eee}pre{white-space:pre-wrap;overflow-wrap:anywhere;max-width:800px}</style><h1>ProjectRover — Prompt original vs compacto</h1><p>Los tiempos miden SOLO la llamada a la API, no captura/SSH ni el ciclo total. Las diferencias de decisión no establecen cuál es segura.</p>'''
    report+='<pre>'+html.escape(json.dumps(summary,indent=2,ensure_ascii=False))+'</pre>'
    report+='<table><tr><th>Imagen</th><th>Variante</th><th>Tiempo (s)</th><th>Tokens entrada</th><th>Tokens salida</th><th>JSON válido</th><th>Respuesta</th></tr>'+''.join(rows)+'</table>'
    (out/'resultados.html').write_text(report,encoding='utf-8')
    print('\nRESULTADOS:',out,'\n',json.dumps(summary,indent=2,ensure_ascii=False),flush=True)

if __name__ == '__main__': main()
