"""Replay approved offline L3 GPS proposals into deterministic guidance.

No hardware, no L1/L2, no motor commands. Takes a previously written map
recon journal and an explicit SIMULATED origin. Does not re-call GPT.
"""
import argparse
import json
import math
from pathlib import Path

def guidance(lat1,lon1,lat2,lon2,heading_deg=None):
    values=(lat1,lon1,lat2,lon2)
    if not all(isinstance(x,(float,int)) and not isinstance(x,bool) and math.isfinite(x) for x in values):
        raise ValueError("GPS coordinates must be finite numbers")
    if not all(-90<=lat<=90 for lat in (lat1,lat2)) or not all(-180<=lon<=180 for lon in (lon1,lon2)):
        raise ValueError("GPS coordinates out of bounds")
    a,b=math.radians(lat1),math.radians(lat2)
    dl=math.radians(lon2-lon1)
    h=math.sin((b-a)/2)**2+math.cos(a)*math.cos(b)*math.sin(dl/2)**2
    distance=6371000*2*math.atan2(math.sqrt(h),math.sqrt(max(0,1-h)))
    east=math.sin(dl)*math.cos(b)
    north=math.cos(a)*math.sin(b)-math.sin(a)*math.cos(b)*math.cos(dl)
    bearing=(math.degrees(math.atan2(east,north))+360)%360 if distance>0.001 else None
    out={"distance_m":round(distance,2),"bearing_deg":round(bearing,2) if bearing is not None else None}
    if heading_deg is not None:
        if not isinstance(heading_deg,(int,float)) or not math.isfinite(heading_deg):
            raise ValueError("Invalid heading")
        out["heading_error_deg"]=round((bearing-heading_deg+180)%360-180,2) if bearing is not None else None
    return out

def replay(journal,lat,lon,heading=None):
    rows=[json.loads(line) for line in Path(journal).read_text(encoding="utf-8").splitlines() if line.strip()]
    if not any(x.get("stage")=="OPERATOR_APPROVED_FOR_OFFLINE_ONLY" for x in rows):
        raise ValueError("Journal has no offline operator approval")
    out=[]
    for cycle,row in enumerate((x for x in rows if x.get("stage")=="L3_GEO_PROPOSAL"),1):
        target=row["output"].get("calculated_gps")
        item={"cycle":cycle,"input_stage":"L3_GEO_PROPOSAL","objective_id":row["output"]["objective_id"],
              "llm_request_id":row.get("request_id"),
              "origin":{"latitude":lat,"longitude":lon,"heading_deg":heading},
              "target":target,"physical_actions":0}
        if target:
            item["guidance"]=guidance(lat,lon,target["latitude"],target["longitude"],heading)
            item["status"]="SIMULATED_GUIDANCE_ONLY"
        else:
            item["status"]="NO_VALID_TARGET"
        out.append(item)
    if not out:
        raise ValueError("Journal contains no L3 proposals")
    return out

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--journal",required=True)
    p.add_argument("--start-lat",type=float,required=True)
    p.add_argument("--start-lon",type=float,required=True)
    p.add_argument("--heading",type=float)
    p.add_argument("--output",required=True,help="New JSONL path (will not overwrite)")
    a=p.parse_args()
    path=Path(a.output)
    with path.open("x",encoding="utf-8") as f:
        for item in replay(a.journal,a.start_lat,a.start_lon,a.heading):
            f.write(json.dumps(item,ensure_ascii=False)+"\n")
            print(json.dumps(item,ensure_ascii=False))
    print("Guidance replay saved:",path)

if __name__=="__main__":
    main()
