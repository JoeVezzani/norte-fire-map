#!/usr/bin/env python3
"""Build index.html + og.png for the Norte Fire street map. Run: python3 build.py"""
import json, html, datetime, os, re, math, io, urllib.request, urllib.parse
from urllib.parse import urlparse
def jss(o):
    """JSON safe for inline <script>: escape <, >, & and U+2028/2029."""
    return json.dumps(o).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026').replace('\u2028','\\u2028').replace('\u2029','\\u2029')
os.chdir(os.path.dirname(os.path.abspath(__file__)))
SITE = 'https://joevezzani.github.io/norte-fire-map/'
PT = datetime.timezone(datetime.timedelta(hours=-7))
osm = json.load(open('osm.json'))['elements']
posts = json.load(open('posts_store.json'))
facts = json.load(open('facts.json'))
try: wd = json.load(open('wd.json'))
except Exception: wd = {'event':{},'data':{},'reports':[],'photos':[]}
def J(o): return json.dumps(o).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026')
def _num(v): return float(v) if isinstance(v,(int,float)) and not isinstance(v,bool) else None
from urllib.parse import urlparse as _up
def _ok_img(u):
    try: pu=_up(u)
    except Exception: return False
    return pu.scheme=='https' and pu.netloc=='images.watchduty.org' and re.fullmatch(r'/uploads/[\w./-]+\.(jpe?g|png|webp)',pu.path or '') is not None
_ZONE=re.compile(r'^[A-Z]{2,4}\s?\d{1,3}$')
def _strip(h): return re.sub(r'<[^>]+>','',html.unescape(h or '')).strip()
def _pt(iso):
    try: return datetime.datetime.fromisoformat(iso.replace('Z','+00:00')).astimezone(PT).strftime('%-I:%M %p')
    except Exception: return ''
_a=wd.get('data',{}).get('acreage')
if isinstance(_a,(int,float)) and _a>0: facts['acres']=f'{float(_a):g}'
_c=wd.get('data',{}).get('containment')
if isinstance(_c,(int,float)) and 0<=_c<=100: facts['containment']=f'{float(_c):g}%'
elif not facts.get('containment'): facts['containment']='0%'
_zrx=re.compile(r'^[A-Z]{2,4} ?\d{1,3}$')
_wd_orders=[z.strip() for z in str(wd.get('data',{}).get('evacuation_orders') or '').split(',') if _zrx.match(z.strip())]
for z in _wd_orders: facts.setdefault('order_zones',{}).setdefault(z,'Watch Duty / OCFA')
_wd_warn=[z.strip() for z in str(wd.get('data',{}).get('evacuation_warnings') or '').split(',') if _zrx.match(z.strip())]
for z in _wd_warn: facts.setdefault('warning_zones',{}).setdefault(z,'Watch Duty / OCFA')
wd_reports=[(_pt(r['t']),_strip(r['msg'])) for r in wd.get('reports',[]) if r.get('msg')]
_prx=re.compile(r'^https://images\.watchduty\.org/uploads/[\w/.-]+\.(jpe?g|png|webp)$',re.I)
wd_photos=[p for p in wd.get('photos',[]) if p.get('media') and isinstance(p.get('lat'),(int,float)) and isinstance(p.get('lng'),(int,float)) and _prx.match(str(p['media'][0]))]
try:
    perim = json.load(open('perimeter.geojson'))
    if not perim.get('features'): perim=None
except Exception: perim = None
try: wind = json.load(open('wind.json'))
except Exception: wind = {'obs':[],'hourly':[],'fetched':''}
# street mentions in the last 90 minutes of posts
import collections, time as _time
_cut=_time.time()-5400
_rx=re.compile(r'\b((?:Camino|Avenida|Via|Calle|Paseo|Rancho|Ortega|Portico)\s+(?:de\s+|la\s+|el\s+|las\s+|los\s+|del\s+)?[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',re.I)
_stop={'down','in','and','to','is','are','has','have','fire','area','off','near','at','on','the','where','with','from','for','by','as','was','were','this','that','now','today'}
_cnt=collections.Counter()
for _p in posts:
    if _p.get('post_created',0)<_cut: continue
    for m in _rx.findall(_p.get('text') or ''):
        w=m.split()
        while len(w)>2 and w[-1].lower() in _stop: w.pop()
        if w[-1].lower() in _stop or len(w)<2: continue
        n=' '.join(x.capitalize() if x.lower() not in ('de','la','el','las','los','del') else x.lower() for x in w)
        _cnt[n]+=1
mentions=[(n,c) for n,c in _cnt.most_common(12) if c>=2]


# ---- layers: key -> label, group, color
G_ORDER, G_IMPACT, G_THREAT, G_ORIGIN, G_REF = 'Evacuation boundary', 'Homes impacted', 'Structures threatened', 'Fire origin area', 'Reference'
COLORS = {G_ORDER:'#e5484d', G_IMPACT:'#f76b15', G_THREAT:'#f5b400', G_ORIGIN:'#b91c1c', G_REF:'#7c8a99'}
STREETS = {
 'Camino Las Ramblas': ('Camino Las Ramblas', G_ORDER),
 'San Diego Freeway': ('Interstate 5', G_ORDER),
 'Prima Deshecha Landfill': ('Prima Deshecha Landfill (the "San Juan dump")', G_ORDER),
 'Avenida Calita': ('Avenida Calita', G_IMPACT),
 'Via la Mirada': ('Via La Mirada', G_IMPACT),
 'Via de Agua': ('Via De Agua', G_IMPACT),
 'Calle Esperanza': ('Calle Esperanza', G_IMPACT),
 'Avenida California': ('Avenida California', G_THREAT),
 'Paseo Aliso': ('Paseo Aliso', G_THREAT),
 'Avenida Placida': ('Avenida Placida', G_THREAT),
 'La Novia Avenue': ('La Novia Avenue', G_THREAT),
 'Via Cerro Rebal': ('Via Cerro Rebal', G_THREAT),
 'Portico Del Norte': ('Portico Del Norte', G_ORIGIN),
 'Eminencia Del Norte': ('Eminencia Del Norte', G_ORIGIN),
 'Camino Capistrano': ('Camino Capistrano', G_REF),
 'Avenida La Pata': ('Avenida La Pata', G_REF),
 'Camino Del Avion': ('Camino Del Avion', G_REF),
 'Avenida Pico': ('Avenida Pico', G_REF),
 'Avenida Vista Hermosa': ('Avenida Vista Hermosa', G_REF),
}
feats = []
for e in osm:
    t = e.get('tags', {}); n = t.get('name')
    if n not in STREETS: continue
    if n == 'San Diego Freeway' and 'I 5' not in (t.get('ref') or ''): continue
    label, grp = STREETS[n]
    coords = [[p['lon'], p['lat']] for p in e.get('geometry', [])]
    if len(coords) < 2: continue
    poly = (n == 'Prima Deshecha Landfill')
    feats.append({'type':'Feature','properties':{'name':label,'group':grp,'color':COLORS[grp],'key':n},
                  'geometry':{'type':'Polygon' if poly else 'LineString','coordinates':[coords] if poly else coords}})
gj = {'type':'FeatureCollection','features':feats}
def _clip_lat(name, lo, hi):
    out=[]
    for e in osm:
        if e.get('tags',{}).get('name')!=name: continue
        seg=[[p['lon'],p['lat']] for p in e.get('geometry',[]) if lo<=p['lat']<=hi]
        if len(seg)>=2: out.append(seg)
    return out
closure_lines=[{'name':'I-5 hard closure: San Juan Creek Rd to Camino De Los Mares (requested 1:29 PM)','lines':_clip_lat('San Diego Freeway',33.455,33.488)},
               {'name':'Avenida La Pata southbound closed: Ortega Hwy to Avenida Vista Hermosa (requested 1:54 PM)','lines':_clip_lat('Avenida La Pata',33.460,33.520)}]
found = {f['properties']['key'] for f in feats}
missing = [k for k in STREETS if k not in found]

# ---- posts
OK_HOSTS = {'x.com','twitter.com','youtube.com','www.youtube.com','www.reddit.com','reddit.com'}
def safe_link(u):
    try: pu = urlparse(u or '')
    except Exception: return None
    if pu.scheme != 'https' or pu.netloc.lower() not in OK_HOSTS: return None
    return html.escape(u, quote=True)
seen=set(); cards=[]; n_posts=0
for p in sorted(posts, key=lambda p: -p.get('post_created',0)):
    link = safe_link(p.get('post_link'))
    if not link or link in seen: continue
    seen.add(link)
    ts = datetime.datetime.fromtimestamp(p.get('post_created',0), PT).strftime('%-I:%M %p')
    who = p.get('influencer_name') or re.sub(r'https?://(www\.)?(x|twitter)\.com/([^/]+)/.*', r'@\3', link)
    txt = html.escape((p.get('text') or '')[:420])
    pt = p.get('post_type')
    if pt == 'youtube-video':
        vid = re.fullmatch(r'https://(www\.)?youtube\.com/watch\?v=([\w-]{6,20})', link)
        if not vid: continue
        cards.append(f'<article class="post video"><div class="meta"><span>YouTube</span><span>{html.escape(who)}</span><time>{ts}</time></div><iframe loading="lazy" src="https://www.youtube.com/embed/{vid.group(2)}" title="Norte Fire video" allowfullscreen></iframe><p>{txt}</p></article>')
    elif pt == 'tweet':
        if '/anyuser/' in link or not re.fullmatch(r'https://(x|twitter)\.com/\w{1,15}/status/\d+', link): continue
        cards.append(f'<article class="post"><blockquote class="twitter-tweet" data-theme="dark" data-dnt="true" data-conversation="none"><p>{txt}</p>&mdash; {html.escape(who)} <a href="{link}">{ts}</a></blockquote></article>')
    elif pt == 'reddit-post':
        cards.append(f'<article class="post"><div class="meta"><span>Reddit</span><span>{html.escape(who)}</span><time>{ts}</time></div><p>{txt}</p><a class="out" href="{link}" target="_blank" rel="noopener">Open on Reddit</a></article>')
    else: continue
    n_posts += 1
now = datetime.datetime.now(PT)
live_vid = re.sub(r'[^\w-]','',str(facts.get('live_video',{}).get('id',''))) if facts.get('live_video') else ''
# posts pinned to the streets they name (last 3 h), keyed by the label used on the map
_labels={v[0].lower():v[0] for v in STREETS.values()}
_alias={'via la mirada':'Via La Mirada','via de agua':'Via De Agua','camino las ramblas':'Camino Las Ramblas','portico del norte':'Portico Del Norte','eminencia del norte':'Eminencia Del Norte','la novia':'La Novia Avenue','via cerro rebal':'Via Cerro Rebal','avenida la pata':'Avenida La Pata'}
street_posts={}
_cut3=_time.time()-10800
for _p in sorted(posts,key=lambda p:-p.get('post_created',0)):
    if _p.get('post_created',0)<_cut3: continue
    _l=safe_link(_p.get('post_link'))
    if not _l or '/anyuser/' in _l: continue
    _t=(_p.get('text') or '')
    _tl=_t.lower()
    hit=set()
    for k,lab in list(_labels.items())+list(_alias.items()):
        if k in _tl: hit.add(lab)
    for lab in hit:
        lst=street_posts.setdefault(lab,[])
        if len(lst)<6: lst.append({'t':datetime.datetime.fromtimestamp(_p.get('post_created',0),PT).strftime('%-I:%M %p'),'who':(_p.get('influencer_name') or re.sub(r'https?://(www\.)?(x|twitter)\.com/([^/]+)/.*',r'@\3',html.unescape(_l)))[:30],'link':html.unescape(_l),'text':_t[:140],'kind':'video' if _p.get('post_type')=='youtube-video' or 'video' in _tl or 'footage' in _tl or 'live' in _tl else 'post'})
# auto front: downwind-most 15% of perimeter vertices, up to 8 points
if perim:
    try:
        _wd=(wind['obs'][0]['dir'] if wind.get('obs') else 70)
        _th=math.radians((_wd+180)%360)
        _pts=[p for poly in perim['features'][0]['geometry']['coordinates'] for ring in poly for p in ring]
        _lat0=sum(p[1] for p in _pts)/len(_pts)
        _proj=lambda p:(p[0]-(-117.65))*math.cos(math.radians(_lat0))*math.sin(_th)+(p[1]-33.48)*math.cos(_th)
        _pts.sort(key=_proj,reverse=True)
        _top=_pts[:max(8,len(_pts)//7)]
        _step=max(1,len(_top)//8)
        facts['front']=[[round(p[1],5),round(p[0],5)] for p in _top[::_step]][:8]
        _pd=perim['features'][0]['properties'].get('date','')
        if _pd:
            facts['front_time']=datetime.datetime.strptime(_pd[:19],'%Y-%m-%d %H:%M:%S').replace(tzinfo=datetime.timezone.utc).astimezone(PT).isoformat()
        facts['front_note']=f"Downwind edge of the FIRIS perimeter mapped {datetime.datetime.fromisoformat(facts['front_time']).strftime('%-I:%M %p')} PT, taken automatically from the perimeter"
    except Exception as _e: print('front auto failed',_e)
zones_txt=', '.join(sorted(facts.get('order_zones',{}).keys()))
guidance=open('guidance.html').read().replace('{ZONES}',html.escape(zones_txt))
guidance2=open('guidance2.html').read()
built = now.strftime('%b %-d, %Y, %-I:%M %p PT')

def li(items): return ''.join(f'<li>{i}</li>' for i in items)
# official agency posts -> timeline
AGENCY={'ocfireauthority':'OCFA','ocsheriff':'OC Sheriff','cityofsjc':'City of SJC','sanclementecity':'City of San Clemente','cal_fire':'CAL FIRE','caltransd12':'Caltrans','ocgov':'OC Gov','capousd':'Capistrano USD'}
agency_tl=[]
for _p in posts:
    _u=_up(_p.get('post_link') or '')
    _host=(_u.hostname or '').lower().rstrip('.'); _handle=(_u.path or '').strip('/').split('/')[0].lower()
    if _host in ('x.com','www.x.com','twitter.com','www.twitter.com') and _handle in AGENCY and re.fullmatch(r'/\w{1,15}/status/\d+/?',_u.path or '') and _p.get('text'):
        v=AGENCY[_handle]
        if True:
            agency_tl.append([datetime.datetime.fromtimestamp(_p['post_created'],PT).strftime('%-I:%M %p'), v+': '+re.sub(r'\s*https?://\S+','',_p['text']).replace('\n',' ').strip()[:300]])
# auto change log: compare live state to last build
try: prev=json.load(open('state_prev.json'))
except Exception: prev={}
cur={'acres':facts.get('acres'),'containment':facts.get('containment'),'orders':','.join(sorted(facts.get('order_zones',{}).keys())),'perim':(perim['features'][0]['properties'].get('date') if perim else None),'wd_reports':len(wd.get('reports',[]))}
try: auto_tl=json.load(open('auto_timeline.json'))
except Exception: auto_tl=[]
_nowt=now.strftime('%-I:%M %p')
if prev:
    if prev.get('acres')!=cur['acres'] and cur['acres']: auto_tl.append([_nowt,f"Acreage updated to {cur['acres']} (Watch Duty / OCFA)."])
    if prev.get('containment')!=cur['containment'] and cur['containment'] is not None: auto_tl.append([_nowt,f"Containment now {cur['containment']}."])
    if prev.get('orders')!=cur['orders']: auto_tl.append([_nowt,f"Evacuation order zones now: {cur['orders'].replace(',',', ')}."])
    if prev.get('perim')!=cur['perim'] and cur['perim']: auto_tl.append([_nowt,"New FIRIS fire perimeter mapped; map updated."])
json.dump(cur,open('state_prev.json','w')); json.dump(auto_tl[-40:],open('auto_timeline.json','w'))
def _dedupe(items):
    seen=set(); out=[]
    for t,m in items:
        k=(t,m[:60])
        if k in seen: continue
        seen.add(k); out.append([t,m])
    return out
tl_all=_dedupe(facts['timeline']+agency_tl+auto_tl)
def _k(t):
    h,m=t.split()[0].split(':'); h=int(h)%12+(12 if 'PM' in t else 0); return h*60+int(m)
timeline = ''.join(f'<li><time>{t}</time><span>{html.escape(s)}</span></li>' for t,s in sorted(tl_all, key=lambda x:-_k(x[0])))
zones = facts['zones']
desc = f"Norte Fire, San Clemente and San Juan Capistrano: where Camino Las Ramblas, Via La Mirada, Avenida Calita and the other streets in the evacuation updates are, with official zone links."

page = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" id="vp" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no,viewport-fit=cover">
<title>Norte Fire Map: Evacuation Streets in San Juan Capistrano and San Clemente</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="{SITE}">
<meta property="og:type" content="website"><meta property="og:site_name" content="Norte Fire Map">
<meta property="og:title" content="Norte Fire: where the evacuation streets are">
<meta property="og:description" content="{desc}">
<meta property="og:url" content="{SITE}"><meta property="og:image" content="{SITE}og.png?v={int(now.timestamp())}">
<meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="Norte Fire: where the evacuation streets are">
<meta name="twitter:description" content="{desc}"><meta name="twitter:image" content="{SITE}og.png?v={int(now.timestamp())}">
<meta http-equiv="Content-Security-Policy" content="default-src 'self'; script-src 'self' 'unsafe-inline' https://unpkg.com https://platform.twitter.com https://cdn.syndication.twimg.com; style-src 'self' 'unsafe-inline' https://unpkg.com https://fonts.googleapis.com https://platform.twitter.com; font-src https://fonts.gstatic.com; img-src * data: blob:; connect-src https://services.arcgis.com https://geocode.arcgis.com https://api.weather.gov https://air-quality-api.open-meteo.com https://platform.twitter.com https://cdn.syndication.twimg.com https://api.twitter.com https://syndication.twitter.com; frame-src https://www.youtube.com https://platform.twitter.com https://syndication.twitter.com; child-src https://www.youtube.com https://platform.twitter.com https://syndication.twitter.com; base-uri 'self'; form-action 'self'">
<meta name="theme-color" content="#0b0d10">
<link rel="icon" href="favicon.svg" type="image/svg+xml"><link rel="icon" href="favicon-32.png" sizes="32x32" type="image/png"><link rel="apple-touch-icon" href="apple-touch-icon.png"><link rel="manifest" href="site.webmanifest">
<meta name="apple-mobile-web-app-title" content="Norte Fire"><meta name="geo.region" content="US-CA"><meta name="geo.placename" content="San Juan Capistrano, California">
<script type="application/ld+json">{jss({"@context":"https://schema.org","@type":"WebPage","name":"Norte Fire Map","url":SITE,"description":desc,"dateModified":now.isoformat(),"about":{"@type":"Event","name":"Norte Fire","startDate":"2026-10-16T11:30:00-07:00","location":{"@type":"Place","name":"San Clemente / San Juan Capistrano, Orange County, CA"}}})}</script>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter+Tight:wght@500;600;700&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script src="spread.js?v={int(now.timestamp())}"></script>
<script src="icons.js?v={int(now.timestamp())}"></script>
<style>
:root{{--bg:#0b0d10;--panel:#12151a;--card:#171b21;--fg:#e8ebef;--muted:#8b95a3;--line:#242a33;--red:#e5484d;--orange:#f76b15;--amber:#f5b400;--gray:#7c8a99;--hdr:56px;--tabs:48px}}
*{{box-sizing:border-box}}html,body{{height:100%}}
body{{margin:0;background:var(--bg);color:var(--fg);font:15px/1.5 Inter,system-ui,-apple-system,sans-serif;-webkit-font-smoothing:antialiased}}
h1,h2,h3{{font-family:"Inter Tight",Inter,system-ui,sans-serif;letter-spacing:-.01em;margin:0}}
a{{color:#8ec5ff}}
header{{height:var(--hdr);display:flex;align-items:center;gap:14px;padding:0 16px;border-bottom:1px solid var(--line);background:var(--bg)}}
header h1{{font-size:17px;font-weight:600}}header h1 b{{color:var(--red);font-weight:700}}
header .upd{{margin-left:auto;color:var(--muted);font-size:12px;white-space:nowrap}}
.layout{{display:grid;grid-template-columns:minmax(0,1fr) 400px;height:calc(100% - var(--hdr))}}
#map{{height:100%;background:#1c2128;touch-action:none;-webkit-user-select:none;user-select:none;-webkit-touch-callout:none;overscroll-behavior:none}}
aside{{overflow-y:auto;border-left:1px solid var(--line);background:var(--panel);padding:0 18px 40px;-webkit-overflow-scrolling:touch}}
section{{padding:18px 0;border-bottom:1px solid var(--line)}}section:last-child{{border:0}}
h2{{font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);margin-bottom:10px;display:flex;align-items:center;gap:7px}}h2 .hi{{display:inline-flex;width:16px;height:16px;flex:none}}h2 .hi .ic{{width:16px;height:16px}}
.notice{{background:#2a1a0a;border:1px solid #4a2d0d;color:#f3d9a4;border-radius:8px;padding:10px 12px;font-size:13px;margin:14px 0 0}}
.notice a{{color:#ffd68a}}
.stats{{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}}
.stat{{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:10px}}
.stat b{{display:block;font-family:"Inter Tight",sans-serif;font-size:20px;font-weight:600;font-variant-numeric:tabular-nums}}.stat span{{font-size:12.5px;color:var(--muted)}}
.zones{{display:flex;flex-wrap:wrap;gap:6px;margin-top:10px}}.zones span{{background:#2a1215;border:1px solid #5a1f24;color:#ffb3b6;border-radius:999px;padding:3px 10px;font-size:12px;font-weight:500}}
.sub{{color:var(--muted);font-size:13px;margin:8px 0 0}}
.leg h3{{font-size:13px;font-weight:600;margin:12px 0 4px;display:flex;align-items:center;gap:8px}}
.leg h3 i{{width:12px;height:12px;border-radius:3px;display:inline-block}}
.leg ul{{list-style:none;margin:0;padding:0}}
.leg li{{padding:6px 0 6px 20px;font-size:14px;cursor:pointer;color:#cfd6de;display:flex}}.leg li:hover{{color:#fff}}.leg li.miss{{color:var(--muted);cursor:default}}
.leg li small{{margin-left:auto;color:var(--muted);font-size:12px}}
.tl{{list-style:none;margin:0;padding:0}}.tl li{{display:grid;grid-template-columns:64px 1fr;gap:10px;padding:6px 0;font-size:13.5px;border-bottom:1px dashed var(--line)}}.tl li:last-child{{border:0}}
.tl time{{color:var(--muted);font-variant-numeric:tabular-nums;font-size:12.5px;padding-top:1px}}
.links{{display:grid;gap:6px}}.links a{{display:flex;justify-content:space-between;padding:10px 12px;background:var(--card);border:1px solid var(--line);border-radius:8px;color:var(--fg);text-decoration:none;font-size:14px}}.links a:hover{{border-color:#3a434f}}.links a small{{color:var(--muted);text-align:right}}
.post{{margin:10px 0;padding:10px;background:var(--card);border:1px solid var(--line);border-radius:10px;font-size:13.5px}}
.post .meta{{display:flex;gap:10px;color:var(--muted);font-size:12px;margin-bottom:6px}}.post .meta time{{margin-left:auto;font-variant-numeric:tabular-nums}}
.post iframe{{width:100%;aspect-ratio:16/9;border:0;border-radius:6px}}.post p{{margin:6px 0 0}}.post .out{{font-size:13px}}
.twitter-tweet{{margin:0!important}}
.lbl{{background:rgba(11,13,16,.85);color:#fff;border:0;border-radius:4px;font:600 12px Inter,sans-serif;padding:3px 7px;box-shadow:none}}
.lbl::before{{display:none}}
.leaflet-control-layers{{background:var(--panel);color:var(--fg);border:1px solid var(--line)!important;border-radius:8px!important;font:13px Inter,sans-serif}}
.leaflet-bar a{{background:var(--panel);color:var(--fg);border-color:var(--line)}}
.leaflet-control-attribution{{background:rgba(11,13,16,.7)!important;color:var(--muted)!important;font-size:10px}}.leaflet-control-attribution a{{color:var(--muted)!important}}
#addr{{display:grid;grid-template-columns:1fr auto auto;gap:6px}}#addr input{{min-width:0;background:var(--card);border:1px solid var(--line);border-radius:8px;color:var(--fg);padding:10px 12px;font:15px Inter,sans-serif}}#addr input:focus{{outline:2px solid #8ec5ff;outline-offset:-1px}}
#addr button{{background:#c62a2f;color:#fff;border:0;border-radius:8px;padding:0 14px;font:600 14px Inter,sans-serif;cursor:pointer}}#addr #geo{{background:var(--card);color:var(--fg);border:1px solid var(--line)}}
.res{{margin-top:10px;padding:12px 14px;border-radius:10px;font-size:14px;border:1px solid var(--line);background:var(--card)}}.res b{{display:block;font-family:"Inter Tight",sans-serif;font-size:18px;margin-bottom:2px}}
.res.order{{background:#3a1215;border-color:#8a2a30}}.res.order b{{color:#ff8a8f}}.res.warn{{background:#3a2d08;border-color:#8a6a12}}.res.warn b{{color:#ffd45c}}.res.ok{{background:#1a2233;border-color:#2c3e5a}}.res.ok b{{color:#bcd3f5}}
.zones span.warn{{background:#2a2208;border-color:#5a4a12;color:#ffd45c}}
#windnow{{display:grid;grid-template-columns:repeat(2,1fr);gap:8px}}.w{{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:10px}}.w b{{display:block;font-family:"Inter Tight",sans-serif;font-size:22px;font-weight:600;font-variant-numeric:tabular-nums}}.w b small{{font-size:12px;color:var(--muted);font-weight:500}}.w span{{font-size:12.5px;color:var(--muted);display:block;line-height:1.35}}
.hourly{{display:flex;gap:6px;overflow-x:auto;padding:10px 0 2px;scrollbar-width:none}}.hourly span{{flex:none;background:var(--card);border:1px solid var(--line);border-radius:8px;padding:6px 9px;font-size:12px;white-space:nowrap}}.hourly em{{display:block;font-style:normal;color:var(--muted);font-size:11px}}
.mention{{list-style:none;margin:0;padding:0}}.mention li{{display:flex;padding:5px 0 5px 20px;font-size:14px;color:#cfd6de}}.mention li small{{margin-left:auto;color:var(--muted);font-size:12px}}
.windarrow{{background:rgba(11,13,16,.85);color:#fff;border-radius:8px;padding:8px 10px;font:600 12px Inter,sans-serif;display:flex;align-items:center;gap:8px}}.windarrow svg{{width:28px;height:28px}}
.act{{background:#141921;border:1px solid var(--line);border-radius:10px;padding:12px 14px;margin:12px 0}}.act h2{{color:#fff;text-transform:none;letter-spacing:0;font-size:15px;margin-bottom:6px}}.act h3{{font-size:13px;margin:12px 0 4px;color:#fff}}.steps{{margin:6px 0;padding-left:20px;font-size:13.5px;color:#cfd6de}}.steps li{{margin:4px 0}}#leave{{border-color:#8a2a30;background:#2a1215}}#es{{border-color:#5a4a12}}
nav.tabs{{display:none}}
@media (max-width:900px){{
 .layout{{display:block;height:auto}}
 #map{{height:calc(100svh - var(--hdr) - var(--tabs))}}
 aside{{border-left:0;display:none}}
 body.tab-info #map{{display:none}}body.tab-info aside{{display:block;min-height:calc(100svh - var(--hdr) - var(--tabs))}}
 body.tab-posts #map{{display:none}}body.tab-posts aside{{display:block}}body.tab-posts section:not(#posts){{display:none}}
 body.tab-info #posts{{display:none}}
 nav.tabs{{display:grid;grid-template-columns:1fr 1fr 1fr;position:sticky;bottom:0;height:var(--tabs);background:var(--bg);border-top:1px solid var(--line);padding-bottom:env(safe-area-inset-bottom)}}
 nav.tabs button{{background:none;border:0;color:var(--muted);font:500 13px Inter,sans-serif;display:inline-flex;align-items:center;justify-content:center;gap:6px}}nav.tabs .hi .ic{{width:16px;height:16px}}nav.tabs button.on{{color:#fff;box-shadow:inset 0 2px 0 var(--red)}}
 header h1{{font-size:15px}}header .upd{{display:none}}
}}
</style></head><body class="tab-map">
<div id="stale" hidden style="background:#3a2d08;color:#ffd45c;padding:8px 16px;font-size:13px;border-bottom:1px solid #8a6a12"></div>
<header><h1><b>Norte Fire</b> evacuation street map</h1><span class="upd">Updated {built}</span></header>
<div class="layout">
<a href="#leave" class="skip" style="position:absolute;left:-9999px">Skip map</a><div id="map" aria-label="Interactive map. The same information is listed in text in the panel."></div>
<aside class="ic-dark">
<div class="notice" style="display:flex;gap:10px;align-items:flex-start"><span class="hi" data-ic="danger" data-col="#f5b400" style="flex:none;width:18px;height:18px;margin-top:2px"></span><span>Informational page, not an official source. Check your address on <a href="https://ocpw.maps.arcgis.com/apps/instant/lookup/index.html?appid=61efa4f48aaf42638d7fe59c395b4865&amp;center=-117.6429%3B33.4887&amp;level=12" target="_blank" rel="noopener">the OC evacuation zone map</a> or <a href="https://protect.genasys.com/search" target="_blank" rel="noopener">Genasys Protect</a> and follow <a href="https://x.com/OCFireAuthority" target="_blank" rel="noopener">@OCFireAuthority</a>. If you are told to leave, leave.</span></div>
{guidance}
<section class="check">
<h2><span class="hi" data-ic="check" data-col="#1f8a4c"></span>Am I in an evacuation zone?</h2>
<form id="addr" autocomplete="off" data-1p-ignore><input id="q" type="search" name="nf-address" autocomplete="off" autocorrect="off" autocapitalize="words" spellcheck="false" data-1p-ignore data-lpignore="true" data-bwignore data-form-type="other" enterkeyhint="search" placeholder="Street address (e.g. 27000 Via De Agua)" aria-label="Street address"><button type="submit">Check</button><button type="button" id="geo" aria-label="Use my location to check my zone">Locate me</button></form>
<div id="res" class="res" role="status" aria-live="polite" hidden></div>
<p class="sub">Checks the live Orange County evacuation zone layer (OC Public Works). Zones are updated by OCFA and the Sheriff; this page just reads them.</p>
</section>
{('<section><h2><span class="hi" data-ic="shelter" data-col="#1f8a4c"></span>Evacuation shelters (OCFA)</h2><div class="links">'+''.join(f'<a href="https://maps.apple.com/?daddr={urllib.parse.quote(sh["addr"])}" target="_blank" rel="noopener">{html.escape(sh["name"])}<small>{html.escape(sh["addr"])} · directions</small></a>' for sh in facts.get('shelters',[]))+'</div><p class="sub">Opened by OCFA at 2:06 PM. Bring medicines, ID and chargers. Pets: check with the shelter before you arrive. If you need a ride, call 911.</p></section>') if facts.get('shelters') else ''}
{('<section><h2><span class="hi" data-ic="school" data-col="#2f6feb"></span>Schools</h2><p class="sub" style="margin:0">'+html.escape(facts['schools']['note'])+'</p><div class="zones" style="margin-top:8px">'+''.join(f'<span style="background:#1a2233;border-color:#2c3e5a;color:#bcd3f5">{html.escape(x)}</span>' for x in facts['schools']['list'])+'</div></section>') if facts.get('schools') else ''}
<section>
<h2><span class="hi" data-ic="danger" data-col="#e5484d"></span>Status</h2>
<div class="stats"><div class="stat"><b>{html.escape(str(facts['acres']))}</b><span>acres (OCFA est.)</span></div><div class="stat"><b>{html.escape(str(facts['containment']))}</b><span>containment</span></div><div class="stat"><b>{html.escape(str(facts['started']))}</b><span>started, Oct 16</span></div></div>
{('<p class="sub"><b>Damage:</b> '+html.escape(facts['damage'])+'</p>') if facts.get('damage') else ''}
<p class="sub">Evacuation <b>orders</b> (leave now):</p>
<div class="zones" id="zones">{''.join(f'<span>{html.escape(z)}</span>' for z in zones)}</div><p class="sub" id="zonesnote">Loading live zone status from the county layer…</p>
{('<p class="sub"><b>Road and facility closures:</b> '+' · '.join(html.escape(c) for c in facts.get('closures',[]))+'</p>') if facts.get('closures') else ''}
{('<p class="sub"><b>Fire perimeter:</b> the solid red area on the map is the FIRIS aircraft-mapped perimeter from '+html.escape(datetime.datetime.fromisoformat(facts['front_time']).strftime('%-I:%M %p'))+' PT, mirrored from Watch Duty. Preliminary; it does not show which homes are damaged.</p>') if perim else ''}
<p class="sub">Per radio traffic at 1:02 PM: all streets off Camino Las Ramblas down to I-5 and around to the San Juan dump. The red and yellow zones on the map are the live county evacuation areas.</p>
</section>
<section>
<h2><span class="hi" data-ic="wind" data-col="#8b5cf6"></span>Wind now</h2>
<div id="windnow">{''.join(f'<div class="w"><b>{o["mph"]:.0f}<small> mph</small></b><span>{"gusts "+str(round(o["gust"]))+" mph · " if o.get("gust") else ""}from {o["dir"]:.0f}°</span><span>{html.escape(o["name"])} · {_pt(o["time"])}</span></div>' for o in wind['obs'][:4])}</div>
<p class="sub">Purple arrows on the map sit at each NWS station and point the way the wind is blowing. Size scales with speed and the purple darkens as gusts pass 25 and 35 mph. Tap one for the raw observation.</p>
<p class="sub" id="windnote">{('Observed '+wind['obs'][0]['time'][11:16]+' UTC at '+wind['obs'][0]['name']+'. Wind is pushing the fire '+('west/southwest toward I-5 and the coast' if wind['obs'] and 45<=(wind['obs'][0]['dir'] or 90)<=135 else 'downwind')+'.') if wind['obs'] else 'Wind data loading…'}</p>
<div class="hourly">{''.join(f'<span><em>{h["t"]}</em>{h["dir"]} {h["spd"]}</span>' for h in wind['hourly'][:8])}</div>
<div id="aq" class="sub" style="margin-top:10px">Air quality: loading…</div>
<p class="sub">Forecast: NWS San Diego hourly grid. Observations: NWS stations. Temperatures {wind['obs'][0]['tempF'] if wind['obs'] and wind['obs'][0].get('tempF') else '--'}°F, humidity {wind['obs'][0]['rh'] if wind['obs'] and wind['obs'][0].get('rh') else '--'}%.</p>
</section>
{guidance2}
<section>
<h2><span class="hi" data-ic="origin" data-col="#f76b15"></span>Wind-driven spread guide (not a forecast) <small style="text-transform:none;letter-spacing:0;font-weight:500">· <a href="methodology.html">how it is computed, with the math</a></small></h2>
<div class="stats" id="spreadstats"><div class="stat"><b>--</b><span>rough head speed, mph</span></div><div class="stat"><b>--</b><span>rough 1 hr run, miles</span></div><div class="stat"><b>--</b><span>rough flame length, ft</span></div></div>
<p class="sub" id="spreadnote">Computing from live wind…</p>
<p class="sub">The gray outlines on the map show only which way today's wind would push the fire and roughly how fast, if nothing stopped it. <b>They are not a forecast and not an evacuation map.</b> Embers can start new fires a mile or more ahead of the flames, so areas outside the outlines are not safe. The starting points were set by hand from reports at {html.escape(datetime.datetime.fromisoformat(facts.get("front_time","2026-10-16T13:02:00-07:00")).strftime("%-I:%M %p"))} and may be out of date. Evacuation decisions come only from OCFA and the Sheriff. Rothermel surface fire model, Scott and Burgan SH5 shrub fuel, Anderson ellipse, slope 25%, containment treated as 0%, clipped at the coastline. No spotting, no suppression, no wind shifts. <a href="methodology.html">Full equations, inputs and sources.</a> Front assumed: {html.escape(facts.get('front_note',''))}.</p>
<p class="sub" style="color:#f3d9a4">These shapes are a rough estimate of where the fire could go if nothing stops it, not an official map. Follow OCFA, CAL FIRE and the Sheriff.</p>
</section>
<section class="leg"><h2><span class="hi" data-ic="locate" data-col="#8ec5ff"></span>Streets in the updates</h2><div id="legend"></div><p class="sub">Tap a street to zoom to it.</p>
{('<h3 style="margin-top:14px">Mentioned in posts, last 90 min</h3><ul class="mention">'+''.join(f'<li>{html.escape(n)}<small>{c}×'+('' if any(n.lower()==v[0].lower() for v in STREETS.values()) else ' · not on map yet')+'</small></li>' for n,c in mentions)+'</ul>') if mentions else ''}
</section>
<section><h2><span class="hi" data-ic="timeline" data-col="#7c8a99"></span>Timeline (PT, newest first)</h2><p class="sub" style="margin:0 0 8px">Sources rechecked every 5 minutes; last check {now.strftime("%-I:%M %p")} PT. Newest Watch Duty report {html.escape(wd_reports[0][0]) if wd_reports else "none"}. Includes OCFA and agency posts, Watch Duty reports, and automatic entries when acreage, containment, zones or the perimeter change.</p><ul class="tl">{timeline}</ul></section>
<section><h2><span class="hi" data-ic="live" data-col="#e5484d"></span>Watch Duty incident reports <small style="text-transform:none;letter-spacing:0">· <a href="https://app.watchduty.org/i/124958" target="_blank" rel="noopener">open Watch Duty</a></small></h2>
<ul class="tl">{''.join(f'<li><time>{t}</time><span>{html.escape(m)}</span></li>' for t,m in wd_reports) or '<li><span class="sub">No reports captured yet.</span></li>'}</ul>
<p class="sub">Verified reports from Watch Duty's reporters, mirrored as of {html.escape(datetime.datetime.fromisoformat(wd['fetched']).strftime('%-I:%M %p') if wd.get('fetched') else '')} PT{(' · incident address: '+html.escape(wd['event'].get('address') or '')) if wd.get('event',{}).get('address') else ''}.</p></section>

<section><h2><span class="hi" data-ic="external" data-col="#7c8a99"></span>Official sources</h2><div class="links">
<a href="https://protect.genasys.com/search" target="_blank" rel="noopener">Genasys Protect <small>zones by address</small></a>
<a href="https://ocpw.maps.arcgis.com/apps/instant/lookup/index.html?appid=61efa4f48aaf42638d7fe59c395b4865&amp;center=-117.6429%3B33.4887&amp;level=12" target="_blank" rel="noopener">OC Public Works zone lookup <small>county evacuation map</small></a>
<a href="https://app.watchduty.org/i/124958" target="_blank" rel="noopener">Watch Duty <small>incident 124958</small></a>
<a href="https://www.ocfa.org/" target="_blank" rel="noopener">Orange County Fire Authority <small>ocfa.org</small></a>
<a href="https://www.alertoc.gov/" target="_blank" rel="noopener">AlertOC <small>emergency alerts</small></a>
<a href="https://app.nationalwildfiretrackingteam.org/?incident=87ebb8be-5f37-4e03-b01a-7350c6fb597d" target="_blank" rel="noopener">Sentinel fire tracker <small>perimeter and aircraft</small></a>
<a href="https://quickmap.dot.ca.gov/" target="_blank" rel="noopener">Caltrans QuickMap <small>I-5 closures</small></a>
<a href="https://www.sanjuancapistrano.org/" target="_blank" rel="noopener">City of San Juan Capistrano</a>
<a href="https://www.san-clemente.org/" target="_blank" rel="noopener">City of San Clemente</a>
</div></section>
<section id="posts"><h2><span class="hi" data-ic="post" data-col="#f76b15"></span>Latest posts <small style="text-transform:none;letter-spacing:0">· {n_posts} via LunarCrush, newest first</small></h2>{('<article class="post video"><div class="meta"><span>Live</span><span>'+html.escape(facts["live_video"]["label"])+'</span></div><iframe loading="lazy" src="https://www.youtube.com/embed/'+re.sub(r"[^\w-]","",facts["live_video"]["id"])+'" title="Live coverage" allowfullscreen></iframe></article>') if facts.get("live_video") else ''}
<p class="sub" style="margin:0 0 8px">These are public posts collected automatically. Most are <b>not verified</b> and some are people's readings of scanner traffic. Do not make evacuation decisions from them. Follow <a href="https://x.com/OCFireAuthority" target="_blank" rel="noopener">@OCFireAuthority</a> and <a href="https://www.alertoc.gov/" target="_blank" rel="noopener">AlertOC</a>.</p>
<div id="feed">{''.join(cards)}</div></section>
<p class="sub">Map data © OpenStreetMap contributors. Imagery © Esri. Page rebuilt every 5 minutes while the incident is active.</p>
</aside></div>
<nav class="tabs" role="tablist"><button class="on" data-t="map"><span class="hi" data-ic="locate" data-col="currentColor"></span>Map</button><button data-t="info"><span class="hi" data-ic="danger" data-col="currentColor"></span>Streets &amp; status</button><button data-t="posts"><span class="hi" data-ic="post" data-col="currentColor"></span>Posts</button></nav>
<script>
if(window.ICONS_CSS)document.head.insertAdjacentHTML('beforeend','<style>'+ICONS_CSS+'</style>');const PAL=(window.ICONS&&ICONS.palette)||{{}};const mk=(k,c,sz)=>window.iconMarkerHTML?iconMarkerHTML(k,c,sz):'';const ic=(k,c)=>window.iconSVG?iconSVG(k,c):'';
const GJ={jss(gj)};
const map=L.map('map',{{zoomControl:true,tapHold:false,bounceAtZoomLimits:false,touchZoom:true,dragging:true}}).setView([33.474,-117.650],13);
const street=L.tileLayer('https://tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png',{{maxZoom:19,attribution:'© OpenStreetMap contributors'}});
const sat=L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{{z}}/{{y}}/{{x}}',{{maxZoom:19,attribution:'© Esri'}}).addTo(map);
const labels=L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Transportation/MapServer/tile/{{z}}/{{y}}/{{x}}',{{maxZoom:19,pane:'shadowPane'}}).addTo(map);
let SAT=true;map.on('baselayerchange',e=>{{ SAT=(e.name==='Satellite'); if(SAT) labels.addTo(map); else map.removeLayer(labels); zoneLayer.setStyle(zoneLayer.options.style); if(window.lastWind) drawSpread(window.lastWind); }});
const evac=[[33.4645,-117.667],[33.4675,-117.670],[33.472,-117.669],[33.478,-117.666],[33.483,-117.662],[33.489,-117.650],[33.492,-117.632],[33.489,-117.621],[33.482,-117.620],[33.476,-117.628],[33.470,-117.640],[33.4655,-117.650],[33.462,-117.660]];
const evacL=L.polygon(evac,{{color:'#e5484d',weight:2,dashArray:'6 6',fillColor:'#e5484d',fillOpacity:.10}}).bindTooltip('Requested evacuation area, approximate sketch',{{sticky:true,className:'lbl'}}).addTo(map);
const groups={{}},byGroup={{}};
const gl=L.geoJSON(GJ,{{style:f=>({{color:f.properties.color,weight:f.geometry.type==='Polygon'?2:5,opacity:.95,fillOpacity:.2,lineCap:'round'}}),
 onEachFeature:(f,l)=>{{l.bindTooltip(f.properties.name,{{className:'lbl',sticky:true}});(groups[f.properties.name]=groups[f.properties.name]||[]).push(l);(byGroup[f.properties.group]=byGroup[f.properties.group]||new Set()).add(f.properties.name);}}}}).addTo(map);
L.control.scale({{imperial:true,metric:false}}).addTo(map);
const ORDER={jss([G_ORIGIN,G_IMPACT,G_THREAT,G_ORDER,G_REF])},COL={jss(COLORS)},MISS={jss([STREETS[m][0] for m in missing])};
const leg=document.getElementById('legend');
ORDER.forEach(g=>{{const names=[...(byGroup[g]||[])].sort();if(!names.length)return;const h=document.createElement('h3');h.innerHTML=`<i style="background:${{COL[g]}}"></i>${{g}}`;leg.appendChild(h);const ul=document.createElement('ul');
 names.forEach(n=>{{const li=document.createElement('li');li.textContent=n;li.onclick=()=>{{document.body.className='tab-map';tabs('map');map.invalidateSize();map.fitBounds(L.featureGroup(groups[n]).getBounds().pad(.5));groups[n].forEach(l=>l.openTooltip());}};ul.appendChild(li);}});leg.appendChild(ul);}});
if(MISS.length){{const ul=document.createElement('ul');MISS.forEach(n=>{{const li=document.createElement('li');li.className='miss';li.innerHTML=`${{n}}<small>not in map data yet</small>`;ul.appendChild(li);}});leg.appendChild(ul);}}
// permanent labels on the named streets
const lblLayer=L.layerGroup();['Avenida Calita','Via La Mirada','Via De Agua','Calle Esperanza','Avenida California','Camino Las Ramblas','Portico Del Norte','Avenida Placida','La Novia Avenue','Via Cerro Rebal'].forEach(n=>{{const ls=groups[n];if(!ls)return;const c=L.featureGroup(ls).getBounds().getCenter();lblLayer.addLayer(L.marker(c,{{opacity:0,interactive:false}}).bindTooltip(n,{{permanent:true,className:'lbl',direction:'top',offset:[0,-4]}}));}});const syncLbl=()=>{{if(map.getZoom()>=15){{if(!map.hasLayer(lblLayer))lblLayer.addTo(map);}}else if(map.hasLayer(lblLayer))map.removeLayer(lblLayer);}};map.on('zoomend',syncLbl);syncLbl();

// ---- live county evacuation zones (OC Public Works feature layer)
const cdir=d=>['north','northeast','east','southeast','south','southwest','west','northwest'][Math.round(((d%360)+360)%360/45)%8];const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[c]));
const ZL='https://services.arcgis.com/UXmFoWC7yDHcDN5Q/arcgis/rest/services/Know_Your_Evacuation_Areas_OC_VIew/FeatureServer/0/query';
const zoneLayer=L.geoJSON(null,{{style:f=>{{const t=effType(f.properties);const satW=(typeof SAT!=='undefined'&&SAT)?1:0;const o=/order/i.test(t),w=/warning/i.test(t);return{{color:o?'#e5484d':w?'#f5b400':(satW?'#cbd5e1':'#6b7684'),weight:(o||w?2:1)+satW,fillColor:o?'#e5484d':w?'#f5b400':'#000',fillOpacity:o?.22:w?.18:0,dashArray:o||w?null:'3 4'}};}},
 onEachFeature:(f,l)=>{{const p=f.properties;l.bindTooltip(`<b>${{esc(p.Evac_Area)}}</b><br>${{esc(effType(p))}}`,{{className:'lbl',sticky:true}});}}}}).addTo(map);
let zoneStatus={{}};const spreadLayer=L.layerGroup().addTo(map);const photoLayer=L.layerGroup().addTo(map);const stnLayer=L.layerGroup().addTo(map);const shelterLayer=L.layerGroup().addTo(map);const postLayer=L.layerGroup().addTo(map);const closureLayer=L.layerGroup().addTo(map);const perimLayer=L.layerGroup().addTo(map);
const OVR_ORDER={jss(facts.get('order_zones',{}))},OVR_WARN={jss(facts.get('warning_zones',{}))};
const norm=z=>String(z||'').replace(/\\s+/g,'').toUpperCase();
function effType(p){{const z=norm(p.Evac_Area),t=p.Evac_Type||'';if(/order/i.test(t))return t;const o=Object.keys(OVR_ORDER).find(k=>norm(k)===z);if(o)return 'Evacuation Order (per '+OVR_ORDER[o]+')';if(/warning/i.test(t))return t;const w=Object.keys(OVR_WARN).find(k=>norm(k)===z);if(w)return 'Evacuation Warning (per '+OVR_WARN[w]+')';return t;}}
L.control.layers({{'Satellite':sat,'Street map':street}},{{'Fire perimeter (FIRIS)':perimLayer,'County evacuation zones (live)':zoneLayer,'Wind spread guide (not a forecast)':spreadLayer,'Photos (Watch Duty users)':photoLayer,'Wind stations (NWS)':stnLayer,'Shelters':shelterLayer,'Posts by street':postLayer,'Road closures':closureLayer,'Streets':gl,'Radio-traffic sketch':evacL}},{{collapsed:true,position:'topright'}}).addTo(map);

async function loadZones(){{try{{
 const u=ZL+'?where=1%3D1&geometry=-117.75,33.40,-117.55,33.55&geometryType=esriGeometryEnvelope&inSR=4326&spatialRel=esriSpatialRelIntersects&outFields=Evac_Area,Evac_Type,City,Area_Desc&returnGeometry=true&outSR=4326&f=geojson&_='+Date.now();
 const r=await fetch(u);const g=await r.json();if(!g.features)throw 0;
 zoneLayer.clearLayers();zoneLayer.addData(g);zoneLayer.bringToBack();evacL.remove();
 const act=g.features.map(f=>({{...f.properties,Evac_Type:effType(f.properties)}})).filter(p=>/order|warning/i.test(p.Evac_Type));
 zoneStatus={{}};act.forEach(p=>zoneStatus[p.Evac_Area]=p.Evac_Type);
 const z=document.getElementById('zones');if(act.length){{z.innerHTML=act.sort((a,b)=>a.Evac_Area.localeCompare(b.Evac_Area)).map(p=>`<span class="${{/warning/i.test(p.Evac_Type)?'warn':''}}">${{esc(p.Evac_Area)}} · ${{/order/i.test(p.Evac_Type)?'ORDER':/warning/i.test(p.Evac_Type)?'WARNING':esc(p.Evac_Type)}}</span>`).join('');}}
 document.getElementById('zonesnote').textContent='County zone layer plus OCFA announcements, checked '+new Date().toLocaleTimeString([],{{hour:'numeric',minute:'2-digit'}})+'. Red = order (leave now), yellow = warning (be ready).';
}}catch(e){{document.getElementById('zonesnote').textContent='Could not reach the county zone layer; showing last known zones. Use the OC zone map link below.';}}}}
loadZones();setInterval(loadZones,120000);
// ---- wind arrow (direction the wind is blowing TOWARD) + live NWS refresh
const WIND={jss(wind['obs'][:1])};
const WindCtl=L.Control.extend({{onAdd(){{const d=L.DomUtil.create('div','windarrow');d.id='windarrow';return d;}}}});new WindCtl({{position:'bottomleft'}}).addTo(map);
function drawWind(o){{if(!o)return;const to=((o.dir||0)+180)%360;document.getElementById('windarrow').innerHTML=mk('wind','#6d28d9',30).replace('class="ic-glyph"','class="ic-glyph" style="transform:rotate('+to+'deg)"')+`<span>Wind ${{Math.round(o.mph)}} mph${{o.gust?', gusts '+Math.round(o.gust):''}}<br><small style="color:#9aa4b2;font-weight:500">from ${{Math.round(o.dir)}}° · ${{esc(o.name)}}</small></span>`;}}
drawWind(WIND[0]);
async function liveWind(){{try{{const r=await fetch('https://api.weather.gov/stations/F1327/observations/latest',{{headers:{{'Accept':'application/geo+json'}}}});const p=(await r.json()).properties;const v=k=>(p[k]||{{}}).value;if(v('windSpeed')==null)return;const o={{dir:v('windDirection'),mph:v('windSpeed')*0.621371,gust:(v('windGust')||0)*0.621371,name:'San Clemente Pier',time:p.timestamp}};drawWind(o);o.rh=WIND[0]&&WIND[0].rh;o.tempF=WIND[0]&&WIND[0].tempF;drawSpread(o);
 const w=document.querySelector('#windnow .w');if(w)w.innerHTML=`<b>${{Math.round(o.mph)}}<small> mph</small></b><span>${{o.gust?'gusts '+Math.round(o.gust)+' mph · ':''}}from ${{Math.round(o.dir)}}° · San Clemente Pier</span>`;
 document.getElementById('windnote').textContent='Observed '+new Date(o.time).toLocaleTimeString([],{{hour:'numeric',minute:'2-digit'}})+' at San Clemente Pier. Wind is pushing the fire '+(o.dir>=45&&o.dir<=135?'west/southwest toward I-5 and the coast':'downwind')+'.';}}catch(e){{}}}}
liveWind();setInterval(liveWind,300000);
// ---- posts pinned to the streets they mention
const SP={J(street_posts)};
Object.entries(SP).forEach(([name,list])=>{{const ls=groups[name];if(!ls||!list.length)return;const b=L.featureGroup(ls).getBounds();const c=b.getCenter();const vids=list.filter(p=>p.kind==='video').length;
 const html=`<div style="font:13px Inter,sans-serif;color:#222;max-width:280px"><b>${{esc(name)}}</b> · ${{list.length}} recent post${{list.length>1?'s':''}} naming this street<ul style="margin:6px 0 0;padding-left:16px">${{list.map(p=>`<li style="margin:3px 0"><a href="${{esc(p.link)}}" target="_blank" rel="noopener">${{esc(p.who)}}</a> <span style="color:#666">${{esc(p.t)}}${{p.kind==='video'?' · video':''}}</span><br><span style="color:#333">${{esc(p.text)}}</span></li>`).join('')}}</ul><div style="color:#666;margin-top:6px;font-size:11px">Placed at the street named in the post, not at the poster's GPS.</div></div>`;
 postLayer.addLayer(L.marker([b.getSouth()+(b.getNorth()-b.getSouth())*0.35,c.lng],{{icon:L.divIcon({{className:'',iconSize:[26,26],iconAnchor:[13,13],html:mk(vids?'video':'post:'+list.length,vids?'#2f6feb':'#f76b15',26)}}),zIndexOffset:400}}).bindTooltip('Posts naming '+esc(name),{{className:'lbl',direction:'top',offset:[0,-10]}}).bindPopup(html,{{maxWidth:320}}));}});
// ---- road closures
const CLOS={J(closure_lines)};
CLOS.forEach(c=>{{const all=c.lines.flat();if(all.length){{const m=all[Math.floor(all.length/2)];closureLayer.addLayer(L.marker([m[1],m[0]],{{icon:L.divIcon({{className:'',html:mk('closure','#0b0d10',26),iconSize:[26,26],iconAnchor:[13,13]}}),zIndexOffset:450}}).bindTooltip('Road closed: '+esc(c.name),{{className:'lbl',direction:'top',offset:[0,-12]}}));}}}});
CLOS.forEach(c=>c.lines.forEach(seg=>{{const ll=seg.map(([x,y])=>[y,x]);closureLayer.addLayer(L.polyline(ll,{{color:'#fff',weight:9,opacity:.9,lineCap:'butt'}}));closureLayer.addLayer(L.polyline(ll,{{color:'#111',weight:5,dashArray:'10 8',opacity:.95,lineCap:'butt'}}).bindTooltip('Road closed: '+esc(c.name),{{className:'lbl',sticky:true}}));}}));
// ---- shelters
const SHELTERS={J([{'name':sh['name'][:80],'addr':sh['addr'][:120],'lat':_num(sh['lat']),'lng':_num(sh['lng'])} for sh in facts.get('shelters',[]) if _num(sh.get('lat')) is not None])};
SHELTERS.forEach(sh=>shelterLayer.addLayer(L.marker([sh.lat,sh.lng],{{icon:L.divIcon({{className:'',iconSize:[32,32],iconAnchor:[16,16],html:mk('shelter','#1f8a4c',32)}}),zIndexOffset:600}}).bindTooltip('Shelter: '+esc(sh.name),{{className:'lbl',direction:'top',offset:[0,-14]}}).bindPopup(`<div style="font:13px Inter,sans-serif;color:#222"><b>Evacuation shelter</b><br>${{esc(sh.name)}}<br>${{esc(sh.addr)}}<br><a href="https://maps.apple.com/?daddr=${{encodeURIComponent(sh.addr)}}" target="_blank" rel="noopener">Directions</a></div>`)));
// ---- NWS wind stations on the map
const STN={{F1327:{{n:'San Clemente Pier',ll:[33.41917,-117.621]}},CAPC1:{{n:'Bell Canyon RAWS',ll:[33.55183,-117.57294]}},ORTSD:{{n:'Ortega RAWS',ll:[33.56957,-117.51384]}},E3225:{{n:'Laguna Hills',ll:[33.61567,-117.74033]}}}};
const stnMk={{}};
function stnIcon(o){{const to=((o.dir||0)+180)%360,sz=26+Math.min(30,(o.mph||0)*1.2),col=(o.gust||o.mph)>=35?'#4c1d95':(o.gust||o.mph)>=25?'#6d28d9':'#8b5cf6';
 const badge=mk('wind',col,sz).replace('class="ic-glyph"','class="ic-glyph" style="transform:rotate('+to+'deg)"');return L.divIcon({{className:'',iconSize:[sz+70,sz],iconAnchor:[sz/2,sz/2],html:`<div style="display:flex;align-items:center;gap:4px">${{badge}}<span style="font:600 12px Inter,sans-serif;color:#fff;background:rgba(11,13,16,.85);padding:2px 6px;border-radius:4px;white-space:nowrap;border:1px solid ${{col}}">${{Math.round(o.mph)}}<span style="font-weight:500;color:#9aa4b2"> mph</span>${{o.gust?` <span style="color:#c4b5fd">g${{Math.round(o.gust)}}</span>`:''}}</span></div>`}});}}
function stnPopup(id,o){{const st=STN[id];return `<div style="font:13px Inter,sans-serif;color:#222;min-width:200px"><b>${{esc(st.n)}}</b> <span style="color:#666">(${{id}})</span><br>Wind from <b>${{Math.round(o.dir)}}°</b> at <b>${{Math.round(o.mph)}} mph</b>${{o.gust?`, gusts <b>${{Math.round(o.gust)}}</b>`:''}}<br>${{o.tempF!=null?Math.round(o.tempF)+' °F':''}}${{o.rh!=null?' · '+Math.round(o.rh)+'% RH':''}}<br><span style="color:#666">Observed ${{o.time?new Date(o.time).toLocaleTimeString([],{{hour:'numeric',minute:'2-digit'}}):''}} · NWS</span><br><a href="https://forecast.weather.gov/data/obhistory/${{id}}.html" target="_blank" rel="noopener">Station history</a></div>`;}}
function setStn(id,o){{const st=STN[id];if(!st||o.mph==null)return;if(stnMk[id]){{stnMk[id].setIcon(stnIcon(o));stnMk[id].setPopupContent(stnPopup(id,o));}}else{{stnMk[id]=L.marker(st.ll,{{icon:stnIcon(o),zIndexOffset:500}}).bindPopup(stnPopup(id,o)).bindTooltip(esc(st.n),{{className:'lbl',direction:'bottom',offset:[0,14]}}).addTo(stnLayer);}}}}
Object.entries({J({o['id']:o for o in wind['obs']})}).forEach(([id,o])=>setStn(id,o));
async function liveStations(){{for(const id of Object.keys(STN)){{try{{const r=await fetch(`https://api.weather.gov/stations/${{id}}/observations/latest`,{{headers:{{'Accept':'application/geo+json'}}}});const p=(await r.json()).properties;const v=k=>(p[k]||{{}}).value;if(v('windSpeed')==null)continue;setStn(id,{{dir:v('windDirection'),mph:v('windSpeed')*0.621371,gust:(v('windGust')||0)*0.621371||null,tempF:v('temperature')!=null?v('temperature')*9/5+32:null,rh:v('relativeHumidity'),time:p.timestamp}});}}catch(e){{}}}}}}
liveStations();setInterval(liveStations,300000);
async function liveAQ(){{try{{const r=await fetch('https://air-quality-api.open-meteo.com/v1/air-quality?latitude=33.477&longitude=-117.661&current=pm2_5,us_aqi&timezone=America%2FLos_Angeles');const c=(await r.json()).current;const aqi=Math.round(c.us_aqi),cat=aqi<=50?'good':aqi<=100?'moderate':aqi<=150?'unhealthy for sensitive groups':aqi<=200?'unhealthy':aqi<=300?'very unhealthy':'hazardous';
 document.getElementById('aq').innerHTML=`<b>Air quality (regional model):</b> US AQI ${{aqi}}, ${{cat}}; PM2.5 ${{c.pm2_5}} µg/m³. This is a regional model estimate, not a smoke sensor. Downwind of the fire it is far worse: stay inside, close windows, set HVAC to recirculate, wear an N95 outdoors. <a href="https://fire.airnow.gov/" target="_blank" rel="noopener">AirNow fire and smoke map</a>`;}}catch(e){{document.getElementById('aq').innerHTML='<b>Air quality:</b> see the <a href="https://fire.airnow.gov/" target="_blank" rel="noopener">AirNow fire and smoke map</a>. Downwind of the fire: stay inside, recirculate HVAC, N95 outdoors.';}}}}
liveAQ();setInterval(liveAQ,900000);
// ---- FIRIS fire perimeter (via Watch Duty tiles)
const PERIM={jss(perim) if perim else 'null'};
if(PERIM){{const pl=L.geoJSON(PERIM,{{style:{{color:'#b91c1c',weight:2.5,fillColor:'#ef4444',fillOpacity:.28}}}}).addTo(perimLayer);pl.bindTooltip('Fire perimeter, '+esc(PERIM.features[0].properties.source)+' mapped '+esc(new Date(PERIM.features[0].properties.date.replace(' ','T')).toLocaleTimeString([],{{hour:'numeric',minute:'2-digit'}}))+' PT. Preliminary; a home inside is not necessarily damaged.',{{className:'lbl',sticky:true}});}}
// ---- Watch Duty origin + user photos
const WDE={jss({'lat':float(wd['event']['lat']) if isinstance(wd.get('event',{}).get('lat'),(int,float)) else None,'lng':float(wd['event']['lng']) if isinstance(wd.get('event',{}).get('lng'),(int,float)) else None,'address':str(wd.get('event',{}).get('address') or '')[:120]})},WDP={jss([{'lat':float(p['lat']),'lng':float(p['lng']),'t':_pt(p['t']),'u':p['media'][0]} for p in wd_photos][:30])};
if(WDE.lat){{L.marker([WDE.lat,WDE.lng],{{icon:L.divIcon({{className:'',html:mk('origin','#b91c1c',30),iconSize:[30,30],iconAnchor:[15,15]}})}}).addTo(map).bindTooltip('Reported origin: '+esc(WDE.address||''),{{className:'lbl'}});}}
WDP.forEach(p=>photoLayer.addLayer(L.marker([p.lat,p.lng],{{icon:L.divIcon({{className:'',html:mk('photo','#2f6feb',22),iconSize:[22,22],iconAnchor:[11,11]}})}}).bindPopup(`<a href="${{esc(p.u)}}" target="_blank" rel="noopener"><img src="${{esc(p.u)}}" alt="User photo" style="width:240px;max-width:70vw;border-radius:6px;display:block"></a><div style="font:12px Inter,sans-serif;margin-top:4px;color:#333">User photo via Watch Duty · ${{esc(p.t)}}</div>`)));
// ---- predicted spread isochrones
const FRONT={jss(facts.get('front',[]))};
function drawSpread(o){{try{{if(!window.spreadModel||!FRONT.length||!o)return;window.lastWind=o;const SPc=SAT?'#fde68a':'#4b5563',SPf=SAT?'#fbbf24':'#6b7280',SPg=SAT?'#fff7ed':'#374151';const base={{windFromDeg:o.dir??95,rhPct:o.rh??20,tempF:o.tempF??92}};
 const m=spreadModel({{...base,windMph:Math.max(5,o.mph||15)}}),g=spreadModel({{...base,windMph:Math.max(o.gust||0,o.mph||15)}});
 spreadLayer.clearLayers();
 const COAST=[[33.462,-117.705],[33.449,-117.672],[33.430,-117.640],[33.416,-117.618],[33.395,-117.590]];const clip=poly=>{{let out=poly;for(let i=0;i<COAST.length-1;i++){{const a=COAST[i],b=COAST[i+1];const side=p=>(b[1]-a[1])*(p[0]-a[0])-(b[0]-a[0])*(p[1]-a[1]);const res=[];for(let k=0;k<out.length;k++){{const P=out[k],Q=out[(k+1)%out.length],sp=side(P),sq=side(Q);if(sp>=0)res.push(P);if((sp>=0)!==(sq>=0)){{const t=sp/(sp-sq);res.push([P[0]+t*(Q[0]-P[0]),P[1]+t*(Q[1]-P[1])]);}}}}out=res;if(!out.length)break;}}return out;}};
 const iso=isochrones(FRONT,m,[3,2,1]).map(i=>({{...i,polygon:clip(i.polygon)}}));iso.forEach(i=>L.polygon(i.polygon,{{color:SPc,weight:SAT?2.5:1.5,dashArray:'4 4',fillColor:SPf,fillOpacity:SAT?(i.hour===1?.22:i.hour===2?.13:.07):(i.hour===1?.14:i.hour===2?.08:.04),interactive:true}}).bindTooltip(`Rough wind guide only, not where the fire will go. +${{i.hour}} h at ${{Math.round(o.mph)}} mph if nothing stopped it (${{i.headRunMiles.toFixed(1)}} mi)`,{{className:'lbl',sticky:true}}).addTo(spreadLayer));
 if(o.gust&&o.gust>o.mph){{const gi=isochrones(FRONT,g,[1])[0];gi.polygon=clip(gi.polygon);L.polygon(gi.polygon,{{color:SPg,weight:SAT?3:2,dashArray:'2 6',fill:false}}).bindTooltip(`Rough wind guide only. +1 h if gusts of ${{Math.round(o.gust)}} mph held (${{gi.headRunMiles.toFixed(1)}} mi)`,{{className:'lbl',sticky:true}}).addTo(spreadLayer);}}
 FRONT.forEach(p=>L.marker(p,{{icon:L.divIcon({{className:'',html:mk('front','#e5484d',18),iconSize:[18,18],iconAnchor:[9,9]}}),interactive:false}}).addTo(spreadLayer));
 const st=document.querySelectorAll('#spreadstats b');st[0].textContent=m.headRosMph.toFixed(1);st[1].textContent=iso.find(i=>i.hour===1).headRunMiles.toFixed(1);st[2].textContent=Math.round(m.flameLengthFt);
 document.getElementById('spreadnote').textContent=`Wind from the ${{cdir(base.windFromDeg)}} (${{Math.round(base.windFromDeg)}}°) at ${{Math.round(o.mph)}} mph${{o.gust?', gusts '+Math.round(o.gust):''}}, pushing the fire ${{cdir(base.windFromDeg+180)}}. ${{m.note}}. Gust case head speed ${{g.headRosMph.toFixed(1)}} mph.`;
}}catch(e){{document.getElementById('spreadnote').textContent='Spread model unavailable.';}}}}
drawSpread(WIND[0]||{{dir:95,mph:17,gust:30,rh:20,tempF:93}});
// ---- address check
const res=document.getElementById('res');let pin;
function show(cls,title,body){{res.hidden=false;res.className='res '+cls;res.innerHTML=`<b>${{title}}</b>${{body}}`;if(cls)res.scrollIntoView({{block:'nearest',behavior:'smooth'}});}}
async function checkPoint(lat,lon,label){{
 label=esc(label);show('', 'Checking…', label);
 const u=ZL+`?geometry=${{lon}},${{lat}}&geometryType=esriGeometryPoint&inSR=4326&spatialRel=esriSpatialRelIntersects&outFields=Evac_Area,Evac_Type,City&returnGeometry=false&f=json&_=${{Date.now()}}`;
 const r=await fetch(u);const j=await r.json();
 if(!r.ok||j.error||!Array.isArray(j.features)){{show('','Lookup failed','The county zone service returned an error. Do not assume you are clear. Use the OC zone map link below.');return;}}
 const f=j.features[0];
 if(pin)pin.remove();pin=L.circleMarker([lat,lon],{{radius:8,color:'#fff',weight:2,fillColor:'#8ec5ff',fillOpacity:1}}).addTo(map);map.setView([lat,lon],15);
 if(!f){{show('ok','No evacuation zone found for this address','<span>We matched: <b>'+(label||'')+'</b></span><br>This does <b>not</b> mean you are safe. The county map can be behind what crews are ordering, and the address match can be wrong. If you see flames or heavy smoke, or a deputy tells you to go, leave. Confirm on the <a href="https://ocpw.maps.arcgis.com/apps/instant/lookup/index.html?appid=61efa4f48aaf42638d7fe59c395b4865" target="_blank" rel="noopener">OC zone map</a>. Sign up at <a href="https://www.alertoc.gov/" target="_blank" rel="noopener">AlertOC</a>.');return;}}
 const p=f.attributes,t=esc(effType(p));p.Evac_Area=esc(p.Evac_Area);
 if(/order/i.test(t))show('order','EVACUATION ORDER: zone '+p.Evac_Area,`<span>We matched: <b>${{label||''}}</b></span><br>Leave now. ${{t}}. Confirm on the <a href="https://ocpw.maps.arcgis.com/apps/instant/lookup/index.html?appid=61efa4f48aaf42638d7fe59c395b4865" target="_blank" rel="noopener">county zone map</a>.`);
 else if(/warning/i.test(t))show('warn','EVACUATION WARNING: zone '+p.Evac_Area,`<span>${{label||''}}</span><br>Be ready to leave. ${{t}}.`);
 else show('ok','Zone '+p.Evac_Area+': no order or warning right now',`<span>We matched: <b>${{label||''}}</b></span><br>This fire is moving fast and zones can change within minutes. Get ready to leave anyway, and check again.`);
}}
document.getElementById('addr').addEventListener('submit',async e=>{{e.preventDefault();e.stopPropagation();const q=document.getElementById('q').value.trim();if(!q){{show('','Type a street address','Example: 27000 Via De Agua');return;}}document.getElementById('q').blur();show('','Finding address…',esc(q));
 try{{const g=await fetch('https://geocode.arcgis.com/arcgis/rest/services/World/GeocodeServer/findAddressCandidates?f=json&maxLocations=1&outFields=Match_addr&countryCode=USA&location=-117.65,33.48&singleLine='+encodeURIComponent(q+(/ca\b|california/i.test(q)?'':', CA')));
  const c=((await g.json()).candidates||[])[0];if(!c||c.score<60){{show('','Address not found','Include street number, street and city, e.g. "27000 Via De Agua, San Juan Capistrano".');return;}}
  await checkPoint(+c.location.y,+c.location.x,c.address);}}catch(err){{show('','Lookup failed','Could not reach the geocoder or county layer. Use the OC zone map link below.');}}}});
document.getElementById('geo').onclick=()=>{{if(!navigator.geolocation)return show('','Location unavailable','');show('','Getting your location…','');navigator.geolocation.getCurrentPosition(p=>checkPoint(p.coords.latitude,p.coords.longitude,'Your current location'),()=>show('','Location permission denied','Type your address instead.'),{{enableHighAccuracy:true,timeout:10000}});}};
document.querySelectorAll('h2 .hi, nav.tabs .hi, .notice .hi').forEach(e=>e.innerHTML=ic(e.dataset.ic,e.dataset.col));
const BUILT_TS={int(now.timestamp())};function staleCheck(){{const m=Math.round((Date.now()/1000-BUILT_TS)/60);const el=document.getElementById('stale');if(m>45){{el.hidden=false;el.innerHTML=`This page has not been updated in over ${{m}} minutes. Check <a style="color:#ffd45c" href="https://www.ocfa.org/" target="_blank" rel="noopener">OCFA</a> and <a style="color:#ffd45c" href="https://protect.genasys.com/search" target="_blank" rel="noopener">Genasys Protect</a> for current orders.`;}}else el.hidden=true;}}staleCheck();setInterval(staleCheck,60000);
function tabs(t){{document.querySelectorAll('nav.tabs button').forEach(b=>b.classList.toggle('on',b.dataset.t===t));}}
document.querySelectorAll('nav.tabs button').forEach(b=>b.onclick=()=>{{document.body.className='tab-'+b.dataset.t;tabs(b.dataset.t);document.getElementById('vp').setAttribute('content',b.dataset.t==='map'?'width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no,viewport-fit=cover':'width=device-width,initial-scale=1,viewport-fit=cover');if(b.dataset.t==='map')setTimeout(()=>map.invalidateSize(),50);if(window.twttr&&twttr.widgets)twttr.widgets.load();}});
</script>
<script async src="https://platform.twitter.com/widgets.js" charset="utf-8"></script>
</body></html>'''
open('index.html','w').write(page)
open('robots.txt','w').write(f'User-agent: *\nAllow: /\nSitemap: {SITE}sitemap.xml\n')
open('sitemap.xml','w').write(f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>{SITE}</loc><lastmod>{now.date()}</lastmod><changefreq>hourly</changefreq></url><url><loc>{SITE}methodology.html</loc><lastmod>{now.date()}</lastmod></url></urlset>')
print('features', len(feats), 'missing', missing, 'posts', n_posts)

# ---- og.png: dark basemap tiles + street lines + title
try:
    from PIL import Image, ImageDraw, ImageFont
    W,H,Z = 1200,630,14
    lat0,lon0 = 33.474,-117.650
    def t2p(lat,lon):
        n=2**Z; x=(lon+180)/360*n; y=(1-math.log(math.tan(math.radians(lat))+1/math.cos(math.radians(lat)))/math.pi)/2*n; return x,y
    cx,cy=t2p(lat0,lon0); ox,oy=cx*256-W/2, cy*256-H/2
    img=Image.new('RGB',(W,H),(11,13,16))
    for tx in range(int(ox//256), int((ox+W)//256)+1):
        for ty in range(int(oy//256), int((oy+H)//256)+1):
            try:
                req=urllib.request.Request(f'https://tile.openstreetmap.org/{Z}/{tx}/{ty}.png',headers={'User-Agent':'norte-fire-map og builder'})
                tile=Image.open(io.BytesIO(urllib.request.urlopen(req,timeout=10).read())).convert('RGB')
                img.paste(tile,(int(tx*256-ox),int(ty*256-oy)))
            except Exception as ex: pass
    img=Image.blend(img, Image.new('RGB',(W,H),(11,13,16)), 0.55)
    d=ImageDraw.Draw(img,'RGBA')
    def px(lon,lat): x,y=t2p(lat,lon); return (x*256-ox, y*256-oy)
    pts=[px(lon,lat) for lat,lon in [[33.4645,-117.667],[33.4675,-117.670],[33.472,-117.669],[33.478,-117.666],[33.483,-117.662],[33.489,-117.650],[33.492,-117.632],[33.489,-117.621],[33.482,-117.620],[33.476,-117.628],[33.470,-117.640],[33.4655,-117.650],[33.462,-117.660]]]
    d.polygon(pts,fill=(229,72,77,28),outline=(229,72,77,200))
    def hexrgb(h): return tuple(int(h[i:i+2],16) for i in (1,3,5))
    if perim:
        for poly in perim['features'][0]['geometry']['coordinates']:
            for ring in poly[:1]:
                d.polygon([px(*xy) for xy in ring],fill=(239,68,68,90),outline=(185,28,28,255))
    for f in sorted(feats,key=lambda f:[G_REF,G_ORDER,G_THREAT,G_IMPACT,G_ORIGIN].index(f['properties']['group'])):
        c=hexrgb(f['properties']['color']); g=f['geometry']
        line=[px(*xy) for xy in (g['coordinates'][0] if g['type']=='Polygon' else g['coordinates'])]
        d.line(line,fill=c+(255,),width=4 if f['properties']['group']!=G_REF else 2,joint='curve')
    def font(sz,bold=False):
        for p in (['/System/Library/Fonts/SFCompact.ttf','/System/Library/Fonts/Helvetica.ttc']):
            try: return ImageFont.truetype(p,sz,index=1 if bold and p.endswith('ttc') else 0)
            except Exception: pass
        return ImageFont.load_default()
    d.rectangle([0,H-130,W,H],fill=(11,13,16,230))
    d.text((40,H-112),'Norte Fire',font=font(50,True),fill=(229,72,77))
    d.text((40+d.textlength('Norte Fire',font=font(50,True))+16,H-104),'evacuation street map',font=font(38),fill=(232,235,239))
    d.text((40,H-46),f"San Juan Capistrano and San Clemente  |  {facts['acres']} acres  |  {facts['containment']} contained  |  updated {now.strftime('%-I:%M %p')} PT",font=font(21),fill=(139,149,163))
    # legend chip top-right
    rows=[G_ORIGIN,G_IMPACT,G_THREAT,G_ORDER]; bw=270; bh=26*len(rows)+20
    d.rounded_rectangle([W-40-bw,28,W-40,28+bh],radius=10,fill=(11,13,16,215))
    for i,g in enumerate(rows):
        y=28+12+i*26; d.rectangle([W-40-bw+14,y+4,W-40-bw+30,y+18],fill=hexrgb(COLORS[g])); d.text((W-40-bw+40,y),g,font=font(19),fill=(232,235,239))
    img.save('og.png',optimize=True); print('og.png written')
except Exception as ex: print('og failed', ex)
