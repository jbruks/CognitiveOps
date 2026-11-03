"""Build an independent SYNTHETIC rural reconnaissance map.

Creates a 1024x768 RGB GeoTIFF in EPSG:3857 for offline cognition.
All geometry is invented: never use these GPS coordinates for a rover.
Requires rasterio, Pillow, numpy. Existing MF-DoD code is unchanged.
"""
import argparse
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
import rasterio
from rasterio.transform import from_origin

def generate(output):
    w,h=1024,768
    image=Image.new("RGB",(w,h),(122,155,103))
    draw=ImageDraw.Draw(image)
    # Terrain texture and different-looking scene from an airfield.
    draw.polygon([(0,0),(440,0),(390,200),(215,340),(0,300)],fill=(80,125,75))
    draw.polygon([(680,0),(1024,0),(1024,285),(760,310),(640,180)],fill=(74,116,69))
    draw.polygon([(0,560),(430,510),(580,768),(0,768)],fill=(173,164,110))
    draw.polygon([(730,525),(1024,485),(1024,768),(770,768)],fill=(94,142,93))
    # Unpaved forked track + east-west gravel road.
    draw.line([(90,410),(900,395)],fill=(185,172,140),width=36)
    draw.line([(95,410),(915,392)],fill=(209,197,163),width=22)
    draw.line([(490,750),(495,410),(420,240),(300,50)],fill=(176,165,135),width=35)
    draw.line([(490,750),(495,410),(420,240),(300,50)],fill=(213,197,159),width=21)
    draw.line([(490,410),(615,275),(710,190)],fill=(179,165,134),width=21)
    draw.line([(490,410),(615,275),(710,190)],fill=(207,193,160),width=12)
    # Barn/yard cluster: distinct rooftops and gravel.
    draw.rectangle([535,445,710,605],fill=(178,170,140))
    draw.rectangle([555,465,638,504],fill=(154,84,67))
    draw.rectangle([657,488,693,561],fill=(109,102,90))
    draw.rectangle([555,524,633,563],fill=(113,102,90))
    # Water body east and south with shoreline, separate from roads.
    draw.ellipse([790,550,988,720],fill=(180,173,130))
    draw.ellipse([802,558,973,705],fill=(60,124,118))
    draw.ellipse([835,586,945,680],fill=(68,134,133))
    # Orchard rows, regular patterns near southwest.
    for y in range(540,705,36):
        for x in range(90,325,38):
            draw.ellipse([x-9,y-9,x+9,y+9],fill=(49,103,51))
    # Tree patches northeast.
    for x,y in [(810,70),(850,90),(910,82),(790,145),(950,160),
                (725,75),(860,238),(917,235),(780,280),(985,290)]:
        draw.ellipse([x-22,y-22,x+22,y+22],fill=(47,97,49))
    rgb=np.array(image)
    dst=Path(output)
    dst.parent.mkdir(parents=True,exist_ok=True)
    if dst.exists():
        raise FileExistsError(f"Refusing to overwrite {dst}")
    # Invented projected origin near (0,0); deliberately not a real site.
    transform=from_origin(0,0,0.5,0.5)
    with rasterio.open(dst,"w",driver="GTiff",height=h,width=w,count=3,
                        dtype="uint8",crs="EPSG:3857",transform=transform) as ds:
        ds.write(np.moveaxis(rgb,-1,0))
    print(f"SYNTHETIC LAB MAP: {dst} ({w}x{h}, EPSG:3857)")
    print("NOT A REAL LOCATION; coordinates must never be used for physical navigation.")

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output",default="mission_packages/rural_crossroads_lab/rural_crossroads.tif")
    generate(p.parse_args().output)

if __name__=="__main__":
    main()
