#!/usr/bin/env python3
"""Build index.html for the Norte Fire street map. Run: python3 build.py"""
import json, html, datetime, os, re
from urllib.parse import urlparse
OK_HOSTS={'x.com','twitter.com','youtube.com','www.youtube.com'}
def safe_link(u):
    try: pu=urlparse(u)
    except Exception: return None
    if pu.scheme!='https' or pu.netloc.lower() not in OK_HOSTS: return None
    return html.escape(u, quote=True)
os.chdir(os.path.dirname(os.path.abspath(__file__)))
osm = json.load(open('osm.json'))['elements']
posts = json.load(open('posts_keep.json'))

STREETS = {  # name -> (label, color, kind)
 'Camino Las Ramblas': ('Camino Las Ramblas', '#ff3b30', 'evac boundary'),
 'Avenida Calita': ('Avenida Calita', '#ff9500', 'homes impacted'),
 'Via la Mirada': ('Via La Mirada', '#ff9500', 'homes impacted / structures'),
 'Via de Agua': ('Via De Agua', '#ff9500', 'homes impacted'),
 'Calle Esperanza': ('Calle Esperanza', '#ff9500', 'structures impacted'),
 'Avenida California': ('Avenida California', '#ffcc00', 'structure threat'),
 'Paseo Aliso': ('Paseo Aliso', '#ffcc00', 'structure threat'),
 'Camino Capistrano': ('Camino Capistrano', '#5ac8fa', 'route'),
 'San Diego Freeway': ('I-5 (San Diego Fwy)', '#8e8e93', 'evac boundary'),
 'Prima Deshecha Landfill': ('Prima Deshecha Landfill ("San Juan dump")', '#af52de', 'evac boundary'),
}
feats = []
for e in osm:
    t = e.get('tags', {}); n = t.get('name')
    if n not in STREETS: continue
    if n == 'San Diego Freeway' and 'I 5' not in (t.get('ref') or ''): continue
    label, color, kind = STREETS[n]
    coords = [[p['lon'], p['lat']] for p in e.get('geometry', [])]
    if not coords: continue
    poly = (n == 'Prima Deshecha Landfill')
    feats.append({'type':'Feature','properties':{'name':label,'color':color,'kind':kind,'key':n},
                  'geometry':{'type':'Polygon' if poly else 'LineString','coordinates':[coords] if poly else coords}})
gj = {'type':'FeatureCollection','features':feats}
found = sorted({f['properties']['key'] for f in feats})
missing = [k for k in STREETS if k not in found]

posts.sort(key=lambda p: -p.get('post_created',0))
cards = []
for p in posts:
    link = safe_link(p.get('post_link',''))
    if not link: continue
    ts = datetime.datetime.fromtimestamp(p.get('post_created',0), datetime.timezone(datetime.timedelta(hours=-7))).strftime('%-I:%M %p')
    who = p.get('influencer_name') or re.sub(r'https?://(www\.)?(x|twitter)\.com/([^/]+)/.*', r'@\3', link)
    txt = html.escape((p.get('text') or '')[:400])
    if p.get('post_type') == 'youtube-video':
        vid = re.fullmatch(r'https://(www\.)?youtube\.com/watch\?v=([\w-]{6,20})', link); 
        body = f'<iframe loading="lazy" src="https://www.youtube.com/embed/{vid.group(2)}" allowfullscreen></iframe>' if vid else ''
        cards.append(f'<article class="card yt"><div class="meta">YouTube · {html.escape(who)} · {ts} PT</div>{body}<p>{txt}</p><a href="{link}" target="_blank" rel="noopener">Open on YouTube ↗</a></article>')
    else:
        if '/anyuser/' in link or not re.fullmatch(r'https://(x|twitter)\.com/\w{1,15}/status/\d+', link): continue
        cards.append(f'<article class="card"><blockquote class="twitter-tweet" data-theme="dark" data-dnt="true"><p>{txt}</p>&mdash; {html.escape(who)} <a href="{link}">{ts} PT</a></blockquote></article>')
built = datetime.datetime.now().strftime('%b %-d, %Y %-I:%M %p PT')

page = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Norte Fire Street Map</title>
<meta name="description" content="Where the Norte Fire streets are in San Juan Capistrano and the requested evacuation area. Informational only.">
<meta name="robots" content="noindex">
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
:root{{--bg:#111;--panel:#1c1c1e;--fg:#f2f2f7;--muted:#9a9aa0;--line:#2c2c2e;--acc:#ff3b30}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--fg);font:15px/1.45 -apple-system,system-ui,Segoe UI,Roboto,sans-serif}}
header{{padding:12px 16px;background:#000;border-bottom:1px solid var(--line)}}
h1{{margin:0;font-size:20px}}h1 span{{color:var(--acc)}}
.sub{{color:var(--muted);font-size:13px;margin-top:2px}}
.warn{{background:#3a1d00;color:#ffd08a;padding:8px 16px;font-size:13px;border-bottom:1px solid #5a2e00}}
.wrap{{display:grid;grid-template-columns:1fr 380px;height:calc(100vh - 118px)}}
#map{{height:100%;min-height:420px}}
aside{{overflow:auto;background:var(--panel);border-left:1px solid var(--line);padding:12px 14px}}
h2{{font-size:13px;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);margin:16px 0 8px}}
.legend div{{display:flex;align-items:center;gap:8px;padding:4px 0;cursor:pointer}}.legend div:hover{{color:#fff}}
.sw{{width:22px;height:5px;border-radius:3px;flex:none}}.sw.p{{height:14px;border-radius:3px;opacity:.6}}
.k{{color:var(--muted);font-size:12px;margin-left:auto}}
.links a{{display:block;padding:7px 10px;margin:4px 0;background:#2c2c2e;border-radius:8px;color:#fff;text-decoration:none}}.links a:hover{{background:#3a3a3c}}
.card{{margin:8px 0;padding:8px;background:#000;border:1px solid var(--line);border-radius:10px;font-size:13px}}
.card iframe{{width:100%;aspect-ratio:16/9;border:0;border-radius:6px}}.meta{{color:var(--muted);font-size:12px;margin-bottom:6px}}.card a{{color:#5ac8fa}}
.twitter-tweet{{margin:0!important}}
.leaflet-tooltip.lbl{{background:rgba(0,0,0,.75);color:#fff;border:0;font-weight:600;padding:2px 6px}}
footer{{padding:10px 16px;color:var(--muted);font-size:12px;border-top:1px solid var(--line)}}
@media(max-width:860px){{.wrap{{grid-template-columns:1fr;height:auto}}#map{{height:62vh}}aside{{border-left:0;border-top:1px solid var(--line)}}}}
</style></head><body>
<header><h1><span>Norte Fire</span> street map · San Juan Capistrano / San Clemente</h1>
<div class="sub">Where the streets named in Watch Duty updates actually are, and the requested evacuation area. Built {built}.</div></header>
<div class="warn">Informational only, not an official source. For orders and zones use <a style="color:#ffd08a" href="https://protect.genasys.com/search" target="_blank">Genasys Protect</a>, <a style="color:#ffd08a" href="https://app.watchduty.org/i/124958" target="_blank">Watch Duty</a>, and <a style="color:#ffd08a" href="https://www.ocfa.org/" target="_blank">OCFA</a>. If you are told to leave, leave.</div>
<div class="wrap">
<div id="map"></div>
<aside>
<h2>Requested evacuation (per radio traffic, 1:02 PM)</h2>
<p style="margin:0 0 6px;font-size:13px">All streets off <b>Camino Las Ramblas</b> down to <b>I-5</b> and around to the <b>San Juan dump</b> (Prima Deshecha Landfill). The shaded red area is an approximate sketch of that description, not an official zone.</p>
<h2>Streets in the updates (click to zoom)</h2>
<div class="legend" id="legend"></div>
<h2>Official resources</h2>
<div class="links">
<a href="https://protect.genasys.com/search" target="_blank">Genasys Protect: evacuation zones by address</a>
<a href="https://app.watchduty.org/i/124958" target="_blank">Watch Duty incident page</a>
<a href="https://www.ocfa.org/" target="_blank">Orange County Fire Authority</a>
<a href="https://www.alertoc.gov/" target="_blank">AlertOC sign-up</a>
<a href="https://quickmap.dot.ca.gov/" target="_blank">Caltrans QuickMap (I-5 status)</a>
<a href="https://www.sanjuancapistrano.org/" target="_blank">City of San Juan Capistrano</a>
</div>
<h2>Social posts (via LunarCrush search)</h2>
<div id="feed">{''.join(cards)}</div>
</aside></div>
<footer>Map data © OpenStreetMap contributors. Street geometry from OSM; posts from a LunarCrush custom search. Snapshot page, refresh for updates.</footer>
<script>
const GJ={json.dumps(gj)};
const map=L.map('map',{{zoomControl:true}}).setView([33.474,-117.655],14);
L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png',{{maxZoom:19,attribution:'© OpenStreetMap'}}).addTo(map);
// approximate evacuation sketch: Camino Las Ramblas corridor down to I-5, east toward the landfill
const evac=[[33.4645,-117.667],[33.4675,-117.670],[33.472,-117.669],[33.478,-117.666],[33.483,-117.662],[33.489,-117.650],[33.492,-117.632],[33.489,-117.621],[33.482,-117.620],[33.476,-117.628],[33.470,-117.640],[33.4655,-117.650],[33.462,-117.660]];
L.polygon(evac,{{color:'#ff3b30',weight:2,dashArray:'6 6',fillColor:'#ff3b30',fillOpacity:.12}}).addTo(map).bindTooltip('Approximate requested evacuation area (unofficial sketch)',{{sticky:true}});
const groups={{}};
L.geoJSON(GJ,{{style:f=>({{color:f.properties.color,weight:f.geometry.type==='Polygon'?2:6,opacity:.95,fillOpacity:.25}}),
 onEachFeature:(f,l)=>{{l.bindTooltip(f.properties.name,{{className:'lbl',sticky:true}});(groups[f.properties.name]=groups[f.properties.name]||[]).push(l);}}}}).addTo(map);
const leg=document.getElementById('legend');
Object.entries(groups).forEach(([name,ls])=>{{const p=ls[0].feature.properties;const d=document.createElement('div');
 d.innerHTML=`<span class="sw ${{ls[0].feature.geometry.type==='Polygon'?'p':''}}" style="background:${{p.color}}"></span>${{name}}<span class="k">${{p.kind}}</span>`;
 d.onclick=()=>{{map.fitBounds(L.featureGroup(ls).getBounds().pad(.4));ls.forEach(l=>l.openTooltip());}};leg.appendChild(d);}});
// label impacted streets permanently
['Avenida Calita','Via La Mirada','Via De Agua','Calle Esperanza','Avenida California','Camino Las Ramblas'].forEach(n=>{{const ls=groups[n];if(!ls)return;const c=L.featureGroup(ls).getBounds().getCenter();L.marker(c,{{opacity:0}}).addTo(map).bindTooltip(n,{{permanent:true,className:'lbl',direction:'top'}});}});
L.control.scale({{imperial:true}}).addTo(map);
</script>
<script async src="https://platform.twitter.com/widgets.js" charset="utf-8"></script>
</body></html>'''
open('index.html','w').write(page)
print('features', len(feats), 'found', found, 'MISSING', missing, 'cards', len(cards))
