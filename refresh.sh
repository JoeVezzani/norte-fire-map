#!/bin/zsh
# Pull new LunarCrush posts, merge into posts_store.json, rebuild, push. Run by LaunchAgent com.joe.norte-fire-refresh every 10 min.
cd ~/norte-fire-map || exit 1
# single-run lock; kill a stale run older than 8 minutes
LOCK=~/.norte-fire-refresh.lock
if [ -d "$LOCK" ]; then
  if [ -n "$(find "$LOCK" -maxdepth 0 -mmin +8)" ]; then pkill -f "norte-fire-map/refresh.sh" 2>/dev/null; pkill -f "wd_fetch.py" 2>/dev/null; rm -rf "$LOCK"; echo "$(date '+%F %T') killed stale run" >> ~/.norte-fire-refresh.log; else exit 0; fi
fi
mkdir "$LOCK" || exit 0; trap 'rm -rf "$LOCK"' EXIT
export PATH=/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin
# Two writers: the MacBook pushes code/facts edits, the Mini is the data bot. Every run starts from origin.
git fetch -q origin && git reset -q --hard origin/main || { echo "$(date '+%F %T') fetch failed" >> ~/.norte-fire-refresh.log; exit 1; }
K=$(security find-generic-password -a lunarcrush -s lunarcrush-api-key -w) || exit 1
for t in "norte%20fire" "nortefire" "san%20juan%20capistrano%20fire" "san%20clemente%20fire" "camino%20las%20ramblas" "ocfa%20evacuation" "orange%20county%20fire%20evacuation" "san%20juan%20capistrano%20evacuation" "san%20clemente%20evacuation"; do
  curl -s -m 30 -A "Mozilla/5.0 curl" "https://lunarcrush.com/api4/public/searches/search?term=$t" -H "Authorization: Bearer $K" -o "lc_raw_$t.json"
done
curl -s -m 30 -A "Mozilla/5.0 curl" "https://lunarcrush.com/api4/public/topic/lc1szJGR3e/posts/v1" -H "Authorization: Bearer $K" -o lc_raw_topic.json
# NWS wind: observations from nearby stations + hourly forecast
UA="norte-fire-map (joevezzani@gmail.com)"
python3 -I - "$UA" <<'PY'
import json,sys,urllib.request,datetime
UA=sys.argv[1]
def get(u):
    try: return json.load(urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':UA,'Accept':'application/geo+json'}),timeout=20))
    except Exception as e: return None
out={'fetched':datetime.datetime.now().isoformat(timespec='minutes'),'obs':[],'hourly':[]}
for sid,name in [('F1327','San Clemente Pier'),('CAPC1','Bell Canyon'),('ORTSD','Ortega'),('E3225','Laguna Hills')]:
    d=get(f'https://api.weather.gov/stations/{sid}/observations/latest')
    if not d: continue
    pr=d['properties']; v=lambda k:(pr.get(k) or {}).get('value')
    if v('windSpeed') is None: continue
    out['obs'].append({'id':sid,'name':name,'time':pr['timestamp'],'dir':v('windDirection'),'mph':round(v('windSpeed')*0.621371,1),'gust':round((v('windGust') or 0)*0.621371,1) or None,'tempF':round(v('temperature')*9/5+32) if v('temperature') is not None else None,'rh':round(v('relativeHumidity')) if v('relativeHumidity') is not None else None})
h=get('https://api.weather.gov/gridpoints/SGX/44,50/forecast/hourly')
if h:
    for per in h['properties']['periods'][:12]:
        out['hourly'].append({'t':per['startTime'][11:16],'dir':per['windDirection'],'spd':per['windSpeed'],'tempF':per['temperature'],'rh':(per.get('relativeHumidity') or {}).get('value'),'sky':per['shortForecast']})
if out['obs'] or out['hourly']: json.dump(out,open('wind.json','w'))
print('wind obs',len(out['obs']),'hourly',len(out['hourly']))
PY
python3 -I - <<'PY'
import json,glob
store={p['post_link']:p for p in json.load(open('posts_store.json')) if p.get('post_link')}
kw=('norte','evacu','capistrano','clemente','ocfa','ramblas','mirada','brush fire','smoke','strike team')
bad=('tecate','concierto','pa\'l norte','the warning')
new=0
for f in glob.glob('lc_raw_*.json'):
    try: d=json.load(open(f)).get('data',[])
    except Exception: continue
    for p in d:
        if not p.get('text') and p.get('post_title'): p['text']=p['post_title']
        if not p.get('influencer_name') and p.get('creator_name'): p['influencer_name']=p['creator_name']
        t=((p.get('post_title') or '')+' '+(p.get('text') or '')).lower()
        if not any(k in t for k in kw) or any(b in t for b in bad): continue
        if 'fire' not in t and 'evacu' not in t and 'smoke' not in t: continue
        if p.get('post_link') and p['post_link'] not in store: store[p['post_link']]=p; new+=1
json.dump(list(store.values()),open('posts_store.json','w'))
print('new posts',new,'total',len(store))
PY
# Watch Duty capture (headless Chromium via Playwright); keep old wd.json on failure
/Users/joevezzani/.joe-venv/bin/python3 -I wd_fetch.py >> ~/.norte-fire-refresh.log 2>&1 || echo "$(date '+%F %T') wd_fetch failed" >> ~/.norte-fire-refresh.log
# preflight: never ship if a dependency is down or keyed
for u in "https://tile.openstreetmap.org/14/2838/6617.png" "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/14/6617/2838" "https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"; do
  c=$(curl -s -m 15 -o /dev/null -A "Mozilla/5.0" -w "%{http_code}" "$u"); [ "$c" = "200" ] || { echo "$(date '+%F %T') PREFLIGHT FAIL $c $u" >> ~/.norte-fire-refresh.log; exit 1; }
done
python3 build.py || exit 1
grep -q "tile.openstreetmap.org" index.html && [ $(stat -f%z og.png) -gt 100000 ] || { echo "$(date '+%F %T') BUILD SANITY FAIL" >> ~/.norte-fire-refresh.log; exit 1; }
git add -A >/dev/null && git commit -qm "refresh $(date '+%m/%d %H:%M')" 2>/dev/null && { git push -q && echo "$(date '+%F %T') pushed" || echo "$(date '+%F %T') push rejected (MacBook pushed first), next run rebuilds on top"; } >> ~/.norte-fire-refresh.log
