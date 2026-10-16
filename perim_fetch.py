#!/usr/bin/env python3
"""Fetch the active fire perimeter (FIRIS via Watch Duty tiles) around the Norte Fire and write perimeter.geojson."""
import math, gzip, json, urllib.request, os, datetime
import mapbox_vector_tile as mvt
os.chdir(os.path.dirname(os.path.abspath(__file__)))
Z=13; S,W,N,E = 33.42,-117.72,33.54,-117.56
def t2xy(lat,lon):
    n=2**Z; return int((lon+180)/360*n), int((1-math.log(math.tan(math.radians(lat))+1/math.cos(math.radians(lat)))/math.pi)/2*n)
x0,y1=t2xy(N,W); x1,y0=t2xy(S,E)
polys=[]; meta={}
for x in range(min(x0,x1),max(x0,x1)+1):
    for y in range(min(y0,y1),max(y0,y1)+1):
        req=urllib.request.Request(f'https://maptiles.watchduty.org/fireperimeters_active/{Z}/{x}/{y}',headers={'User-Agent':'Mozilla/5.0','Origin':'https://app.watchduty.org','Referer':'https://app.watchduty.org/'})
        try: raw=urllib.request.urlopen(req,timeout=20).read()
        except Exception: continue
        if not raw: continue
        try: raw=gzip.decompress(raw)
        except Exception: pass
        try: d=mvt.decode(raw)
        except Exception: continue
        lay=d.get('fireperimeters_active'); 
        if not lay: continue
        ext=lay.get('extent',4096); n=2**Z
        def px2ll(px,py):
            lon=(x+px/ext)/n*360-180
            # MVT y origin is top-left after decode? mapbox_vector_tile returns y flipped (origin bottom-left) by default
            yy=(y+(1-py/ext))/n
            lat=math.degrees(math.atan(math.sinh(math.pi*(1-2*yy))))
            return [round(lon,6),round(lat,6)]
        for f in lay['features']:
            g=f['geometry']; meta=f.get('properties',{}) or meta
            rings=g['coordinates'] if g['type']=='Polygon' else [r for mp in g['coordinates'] for r in mp]
            if g['type']=='Polygon': rings=[g['coordinates']]
            else: rings=g['coordinates']
            for poly in rings:
                polys.append([[px2ll(*pt) for pt in ring] for ring in poly])
# dissolve tile seams into one clean perimeter
try:
    from shapely.geometry import Polygon, MultiPolygon, mapping
    from shapely.ops import unary_union
    shp=[Polygon(r[0],r[1:]) for r in polys if len(r[0])>=4]
    u=unary_union([g.buffer(0) for g in shp]).buffer(0.00002).buffer(-0.00002).simplify(0.00003,preserve_topology=True)
    geoms=list(u.geoms) if hasattr(u,'geoms') else [u]
    polys=[[[list(c) for c in g.exterior.coords]]+[[list(c) for c in i.coords] for i in g.interiors] for g in geoms if g.area>1e-9]
    print('dissolved to',len(polys),'polygon(s)')
except Exception as e: print('dissolve skipped',e)
gj={'type':'FeatureCollection','features':[{'type':'Feature','properties':{'source':meta.get('source_display_string','FIRIS'),'date':meta.get('source_date_current',''),'fetched':datetime.datetime.now().isoformat(timespec='minutes')},'geometry':{'type':'MultiPolygon','coordinates':polys}}] if polys else []}
json.dump(gj,open('perimeter.geojson','w'))
print('perimeter polys',len(polys),'source',meta.get('source_display_string'),meta.get('source_date_current'))
