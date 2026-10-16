#!/bin/zsh
# Pull new LunarCrush posts, merge into posts_store.json, rebuild, push. Run by LaunchAgent com.joe.norte-fire-refresh every 10 min.
cd ~/norte-fire-map || exit 1
export PATH=/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin
K=$(security find-generic-password -a lunarcrush -s lunarcrush-api-key -w) || exit 1
for t in "norte%20fire" "nortefire" "san%20juan%20capistrano%20fire" "san%20clemente%20fire" "camino%20las%20ramblas" "ocfa%20evacuation" "orange%20county%20fire%20evacuation" "san%20juan%20capistrano%20evacuation" "san%20clemente%20evacuation"; do
  curl -s -m 30 -A "Mozilla/5.0 curl" "https://lunarcrush.com/api4/public/searches/search?term=$t" -H "Authorization: Bearer $K" -o "lc_raw_$t.json"
done
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
        t=((p.get('post_title') or '')+' '+(p.get('text') or '')).lower()
        if not any(k in t for k in kw) or any(b in t for b in bad): continue
        if 'fire' not in t and 'evacu' not in t and 'smoke' not in t: continue
        if p.get('post_link') and p['post_link'] not in store: store[p['post_link']]=p; new+=1
json.dump(list(store.values()),open('posts_store.json','w'))
print('new posts',new,'total',len(store))
PY
# preflight: never ship if a dependency is down or keyed
for u in "https://tile.openstreetmap.org/14/2838/6617.png" "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/14/6617/2838" "https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"; do
  c=$(curl -s -m 15 -o /dev/null -A "Mozilla/5.0" -w "%{http_code}" "$u"); [ "$c" = "200" ] || { echo "$(date '+%F %T') PREFLIGHT FAIL $c $u" >> ~/.norte-fire-refresh.log; exit 1; }
done
python3 build.py || exit 1
grep -q "tile.openstreetmap.org" index.html && [ $(stat -f%z og.png) -gt 100000 ] || { echo "$(date '+%F %T') BUILD SANITY FAIL" >> ~/.norte-fire-refresh.log; exit 1; }
git add -A >/dev/null && git commit -qm "refresh $(date '+%m/%d %H:%M')" 2>/dev/null && git push -q && echo "$(date '+%F %T') pushed" >> ~/.norte-fire-refresh.log
