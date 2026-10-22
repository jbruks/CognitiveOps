#!/usr/bin/env python3
"""V3 tres sectores + confidence, reutiliza benchmark original anterior."""
import argparse, base64, csv, html, json, os, statistics, time
from pathlib import Path

PROMPT_V3 = '''You are the visual perception system of an Axial SCX10 II 4x4 rover,
0.30 m wide, with 0.07 m minimum ground clearance.
Assess safe traversability in three rover-relative corridors: LEFT, FRONT, RIGHT.
Consider the rover's width. It traverses dirt, gravel, pavement, grass,
scattered small stones and moderately uneven ground. Perspective can make
small foreground stones look much larger. Sparse grass, flexible weeds and
minor unevenness are usually passable. Large rocks, rigid obstacles, walls,
dense vegetation, holes, drops and water can block passage.
Mark false if safe passage cannot be established from the image. Do not
invent distances or choose an action. Return ONLY JSON with three booleans
in LEFT, FRONT, RIGHT order and a global confidence from 0 to 1:
{"passable":[true,false,true],"confidence":0.85}'''

def load_jsonl(p):
    if not p.exists(): return []
    return [json.loads(s) for s in p.read_text(encoding='utf-8').splitlines() if s.strip()]

def validate(s):
    d=json.loads(s)
    if not isinstance(d,dict) or set(d)!={'passable','confidence'}:raise ValueError('Claves inválidas')
    if not isinstance(d['passable'],list) or len(d['passable'])!=3 or any(type(x)!=bool for x in d['passable']):raise ValueError('passable inválido')
    if isinstance(d['confidence'],bool) or not isinstance(d['confidence'],(float,int)) or not 0 <= d['confidence'] <= 1:raise ValueError('confidence inválida')
    return d

def three(d):
    m={r['name']:r['traversable'] for r in d['regions']}
    return [m['left'] and m['front-left'], m['front-left'] and m['front'] and m['front-right'], m['front-right'] and m['right']]

def stats(x):
    if not x:return None
    x=sorted(x)
    return {'n':len(x),'media_s':round(statistics.mean(x),3),'mediana_s':round(statistics.median(x),3),'p95_s':round(x[int(.95*(len(x)-1))],3),'max_s':round(x[-1],3)}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--repo',type=Path,default=Path.home()/'CognitiveOps')
    ap.add_argument('--baseline',type=Path,help='Ruta resultados.jsonl del benchmark V0/V1')
    ap.add_argument('--out',type=Path)
    ap.add_argument('--start',type=int,default=1)
    ap.add_argument('--end',type=int,default=177)
    ap.add_argument('--model',default='gpt-5.4')
    ap.add_argument('--reset',action='store_true')
    args=ap.parse_args()
    from openai import OpenAI
    import cv2
    if not os.getenv('OPENAI_API_KEY'):raise SystemExit('OPENAI_API_KEY no configurada')
    repo=args.repo.expanduser()
    baseline=(args.baseline or repo/'benchmark_prompt_l2_gpt'/'resultados.jsonl').expanduser()
    out=(args.out or repo/'benchmark_prompt_l2_v3').expanduser()
    out.mkdir(parents=True,exist_ok=True)
    v0={x['foto']:x for x in load_jsonl(baseline) if x.get('variante')=='original' and x.get('valido') and isinstance(x.get('parsed'),dict)}
    if not v0:raise SystemExit(f'No encontré originales válidos en {baseline}. Indica --baseline RUTA')
    (out/'prompt_v3.txt').write_text(PROMPT_V3,encoding='utf-8')
    dest=out/'resultados_v3.jsonl'
    if args.reset and dest.exists():dest.unlink()
    prev=load_jsonl(dest)
    done={x['foto'] for x in prev if x.get('valido')}
    client=OpenAI(timeout=120,max_retries=0)
    print(f'Reutilizando {len(v0)} respuestas originales. Solo se facturan peticiones V3 nuevas.',flush=True)
    with dest.open('a',encoding='utf-8') as f:
        for i in range(args.start,args.end+1):
            photo=f'{i:04d}.jpg'
            if photo not in v0 or photo in done:continue
            pic=repo/'merged_run'/photo
            frame=cv2.imread(str(pic))
            if frame is None:raise SystemExit(f'Falta {pic}')
            frame=cv2.resize(frame,(320,240))
            ok,jpeg=cv2.imencode('.jpg',frame)
            if not ok:raise SystemExit(f'Error JPEG {photo}')
            url='data:image/jpeg;base64,'+base64.b64encode(jpeg.tobytes()).decode('ascii')
            rec={'foto':photo,'variante':'v3','modelo':args.model,'error':None,'valido':False}
            t=time.perf_counter()
            try:
                r=client.responses.create(model=args.model,input=[{'role':'user','content':[
                    {'type':'input_text','text':PROMPT_V3},{'type':'input_image','image_url':url}]}],
                    temperature=0,max_output_tokens=100)
                rec['latencia_s']=round(time.perf_counter()-t,3)
                rec['respuesta']=r.output_text.strip()
                rec['tokens_entrada']=getattr(r.usage,'input_tokens',None)
                rec['tokens_salida']=getattr(r.usage,'output_tokens',None)
                try:
                    rec['parsed']=validate(rec['respuesta']);rec['valido']=True
                except Exception as exc:rec['error_formato']=str(exc)
            except Exception as exc:
                rec['latencia_s']=round(time.perf_counter()-t,3);rec['error']=repr(exc)
            f.write(json.dumps(rec,ensure_ascii=False)+'\n');f.flush();prev.append(rec)
            print(f'{photo}: {rec["latencia_s"]:.3f}s valid={rec["valido"]}',flush=True)
            if rec['error']:raise SystemExit('Error API; vuelve a lanzar para continuar.')
    valid={x['foto']:x for x in prev if x.get('valido')}
    names=('LEFT','FRONT','RIGHT')
    rows=[]
    for photo in sorted(v0):
        if photo not in valid:continue
        a=v0[photo];b=valid[photo];x=three(a['parsed']);y=b['parsed']['passable']
        liberal=[names[i] for i in range(3) if not x[i] and y[i]]
        cautious=[names[i] for i in range(3) if x[i] and not y[i]]
        rows.append({'foto':photo,'v0_left':x[0],'v0_front':x[1],'v0_right':x[2],
                     'v3_left':y[0],'v3_front':y[1],'v3_right':y[2],
                     'confianza_v0':a['parsed'].get('confidence'),'confianza_v3':b['parsed']['confidence'],
                     'tiempo_v0_s':a['latencia_s'],'tiempo_v3_s':b['latencia_s'],
                     'tokens_v0_entrada':a.get('tokens_entrada'),'tokens_v3_entrada':b.get('tokens_entrada'),
                     'tokens_v0_salida':a.get('tokens_salida'),'tokens_v3_salida':b.get('tokens_salida'),
                     'v3_libera_sector_bloqueado_v0':','.join(liberal),'v3_bloquea_sector_libre_v0':','.join(cautious)})
    with (out/'comparativa_v0_v3.csv').open('w',encoding='utf-8',newline='') as f:
        if rows:
            writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    resumen={'fotografias_comparadas':len(rows),'original':stats([r['tiempo_v0_s'] for r in rows]),
             'v3':stats([r['tiempo_v3_s'] for r in rows]),
             'tokens_v0_entrada':sum(r['tokens_v0_entrada'] or 0 for r in rows),
             'tokens_v3_entrada':sum(r['tokens_v3_entrada'] or 0 for r in rows),
             'tokens_v0_salida':sum(r['tokens_v0_salida'] or 0 for r in rows),
             'tokens_v3_salida':sum(r['tokens_v3_salida'] or 0 for r in rows),
             'fotos_discrepantes':sum(bool(r['v3_libera_sector_bloqueado_v0'] or r['v3_bloquea_sector_libre_v0']) for r in rows),
             'sectores_que_v3_libera':sum(len(r['v3_libera_sector_bloqueado_v0'].split(',')) for r in rows if r['v3_libera_sector_bloqueado_v0']),
             'sectores_que_v3_bloquea':sum(len(r['v3_bloquea_sector_libre_v0'].split(',')) for r in rows if r['v3_bloquea_sector_libre_v0']),
             'aviso':'V0 es referencia, no verdad de terreno; las diferencias no determinan seguridad.'}
    (out/'resumen.json').write_text(json.dumps(resumen,indent=2,ensure_ascii=False),encoding='utf-8')
    tr=[]
    for row in rows:
        src=(repo/'merged_run'/row['foto']).as_uri()
        danger=bool(row['v3_libera_sector_bloqueado_v0'])
        tr.append('<tr'+(' class="alert"' if danger else '')+'><td><img width="220" src="'+html.escape(src)+'"><br>'+row['foto']+'</td>'
                  +'<td>'+str([row['v0_left'],row['v0_front'],row['v0_right']])+'</td>'
                  +'<td>'+str([row['v3_left'],row['v3_front'],row['v3_right']])+'</td>'
                  +'<td>'+html.escape(row['v3_libera_sector_bloqueado_v0'])+'</td>'
                  +'<td>'+str(row['tiempo_v0_s'])+' / '+str(row['tiempo_v3_s'])+'</td></tr>')
    page='<!doctype html><meta charset="utf-8"><title>L2 V0 vs V3</title><style>body{font:14px system-ui;margin:20px}table{border-collapse:collapse}td,th{border:1px solid #ccc;padding:8px}tr.alert{background:#ffe1e1}pre{white-space:pre-wrap}</style>'
    page+='<h1>ProjectRover: L2 original frente a V3</h1><p>Orden: LEFT, FRONT, RIGHT. V0 reducido con AND conservador. Rojo: V3 autoriza una dirección bloqueada por V0; no implica que V0 tenga razón.</p>'
    page+='<pre>'+html.escape(json.dumps(resumen,indent=2,ensure_ascii=False))+'</pre>'
    page+='<table><tr><th>Foto</th><th>V0</th><th>V3</th><th>V3 libera</th><th>Tiempo V0/V3 (s)</th></tr>'+''.join(tr)+'</table>'
    (out/'resultados.html').write_text(page,encoding='utf-8')
    print(json.dumps(resumen,indent=2,ensure_ascii=False),flush=True)
    print('Resultados:',out)

if __name__=='__main__':main()
