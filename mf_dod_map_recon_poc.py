"""Experimental two-stage L4 map reading / L3 coordinate selection.

LAB ONLY. No rover imports, no movement commands. Requires a georeferenced
raster readable by rasterio and OPENAI_API_KEY for --model GPT.
"""
import argparse
import base64
from datetime import datetime, timezone
import json
import math
from pathlib import Path

def event(path, stage, **details):
    with Path(path).open("a", encoding="utf-8") as f:
        f.write(json.dumps({"utc":datetime.now(timezone.utc).isoformat(),
                            "stage":stage,"physical_actions":0,**details},
                           ensure_ascii=False, default=str)+"\n")

def parse_response(text, required):
    result=json.loads(text)
    if not isinstance(result,dict) or set(result)!=set(required):
        raise ValueError("Unexpected model response schema")
    return result

def image_response(client, model, instructions, image_data, context):
    response=client.responses.create(model=model, instructions=instructions,
        input=[{"role":"user","content":[
            {"type":"input_text","text":json.dumps(context,ensure_ascii=False)},
            {"type":"input_image","image_url":image_data}]}])
    return response.output_text, getattr(response,"id",None)

def pixel_to_wgs84(dataset, col, row):
    from rasterio.warp import transform
    if dataset.crs is None:
        raise ValueError("Map has no CRS; cannot derive GPS")
    if not all(math.isfinite(x) for x in (col,row)):
        raise ValueError("Non-finite image coordinate")
    if not (0 <= col < dataset.width and 0 <= row < dataset.height):
        raise ValueError("Image coordinate outside map")
    x,y=dataset.transform*(col+0.5,row+0.5)
    lon,lat=transform(dataset.crs,"EPSG:4326",[x],[y])
    if not (-180<=lon[0]<=180 and -90<=lat[0]<=90):
        raise ValueError("Coordinate transformation invalid")
    return round(lat[0],8),round(lon[0],8)

def run(args):
    from rasterio import open as open_raster
    from PIL import Image
    from io import BytesIO
    from openai import OpenAI
    if Path(args.journal).exists():
        raise FileExistsError("Journal exists: choose a new filename")
    client=OpenAI(timeout=90)
    with open_raster(args.map) as ds:
        if ds.crs is None:
            raise ValueError("Map CRS missing; use a georeferenced raster")
        # Preview is resized, so the model's coordinate system is preview pixels.
        arr=ds.read(indexes=list(range(1,min(ds.count,3)+1)),out_shape=(min(ds.count,3),
                max(1,round(ds.height*min(1,1024/max(ds.width,ds.height)))),
                max(1,round(ds.width*min(1,1024/max(ds.width,ds.height))))),
                masked=True)
        import numpy as np
        channels=[]
        for layer in arr:
            raw=layer.filled(0).astype(float)
            vals=raw[np.isfinite(raw)]
            low,high=np.percentile(vals,[2,98]) if vals.size else (0,1)
            if high<=low: high=low+1
            channels.append(np.uint8(np.clip((raw-low)/(high-low)*255,0,255)))
        while len(channels)<3: channels.append(channels[-1])
        img=Image.fromarray(np.stack(channels[:3],axis=-1).transpose(1,2,0),"RGB")
        buff=BytesIO();img.save(buff,format="JPEG",quality=85)
        data="data:image/jpeg;base64,"+base64.b64encode(buff.getvalue()).decode()
        context={"mission":args.mission,"map_preview_size":[img.width,img.height],
                 "reference_note":"Visible features are hypotheses, not field verified. Operator must approve before navigation.",
                 "site_context":Path(args.context).read_text(encoding="utf-8")[:4000] if args.context else ""}
        event(args.journal,"INPUT",mission=args.mission,map=str(args.map),
              source_crs=str(ds.crs),width=ds.width,height=ds.height,
              preview_size=[img.width,img.height],context=context)
        l4text,l4id=image_response(client,args.model,
          "You are L4 mission planner for a civilian mapping reconnaissance simulation. "
          "Inspect the supplied aerial map and classify only visibly supported features "
          "(such as airstrip, buildings, paths), acknowledging ambiguity. "
          "Propose up to 4 HIGH-LEVEL observation objectives, not routes or GPS. "
          "Use the mission and site context, no site access or terrain safety claims. "
          "Return only JSON: {objectives:[{id,feature,goal}],reason}.",data,context)
        l4=parse_response(l4text,("objectives","reason"))
        if not isinstance(l4["objectives"],list) or not (1<=len(l4["objectives"])<=4):
            raise ValueError("Invalid L4 objective count")
        ids=set()
        for obj in l4["objectives"]:
            if not isinstance(obj,dict) or set(obj)!={"id","feature","goal"} or not all(isinstance(v,str) and v for v in obj.values()) or obj["id"] in ids:
                raise ValueError("Invalid L4 objective")
            ids.add(obj["id"])
        event(args.journal,"L4_PLAN",model=args.model,request_id=l4id,output=l4)
        print(json.dumps({"L4_plan":l4},indent=2,ensure_ascii=False))
        if input("Approve ALL objectives for OFFLINE coordinate proposal? Type YES: ").strip()!="YES":
            event(args.journal,"OPERATOR_ABORT");return
        event(args.journal,"OPERATOR_APPROVED_FOR_OFFLINE_ONLY",ids=list(ids))
        for obj in l4["objectives"]:
            l3context={**context,"objective":obj}
            l3text,l3id=image_response(client,args.model,
              "You are L3 map-reading navigation planner for OFFLINE analysis only. "
              "Given ONE approved high-level goal and this aerial image, propose ONE "
              "image pixel location for a POSSIBLE observation point, not a driving route. "
              "Coordinates must be preview-image PIXELS, x right y down, within supplied "
              "image dimensions. Do not claim access, traversability or actual visibility. "
              "If uncertain, explicitly return feasible:false and null x/y. "
              "Return JSON only {feasible:boolean,x:number|null,y:number|null,reason:string}.",
              data,l3context)
            l3=parse_response(l3text,("feasible","x","y","reason"))
            if not isinstance(l3["feasible"],bool) or not isinstance(l3["reason"],str):
                raise ValueError("Malformed L3 proposal")
            result={"objective_id":obj["id"],"proposal":l3,
                    "status":"UNVERIFIED_NOT_APPROVED_FOR_PHYSICAL_USE"}
            if l3["feasible"]:
                if any(isinstance(l3[k],bool) or not isinstance(l3[k],(int,float)) for k in ("x","y")):
                    raise ValueError("Invalid L3 pixel coordinates")
                px,py=l3["x"],l3["y"]
                col=px*ds.width/img.width;row=py*ds.height/img.height
                lat,lon=pixel_to_wgs84(ds,col,row)
                result["calculated_gps"]={"latitude":lat,"longitude":lon}
            event(args.journal,"L3_GEO_PROPOSAL",model=args.model,request_id=l3id,
                  input_objective=obj,output=result)
            print(json.dumps(result,indent=2,ensure_ascii=False))
        event(args.journal,"END",state="OFFLINE_GEO_PROPOSALS_UNVERIFIED")

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--map",required=True,help="GeoTIFF or other rasterio georeferenced raster")
    p.add_argument("--mission",default="Reconnoitre the area. Identify visible features and propose observation objectives.")
    p.add_argument("--context",help="Optional site-context plain text")
    p.add_argument("--model",default="gpt-5.4")
    p.add_argument("--journal",required=True)
    args=p.parse_args()
    run(args)

if __name__=="__main__":
    main()
