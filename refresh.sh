#!/bin/zsh
# Pull new LunarCrush posts, merge into posts_store.json, rebuild, push. Run by LaunchAgent com.joe.norte-fire-refresh every 10 min.
cd ~/norte-fire-map || exit 1
export PATH=/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin
K=$(security find-generic-password -a lunarcrush -s lunarcrush-api-key -w) || exit 1
for t in "norte%20fire" "nortefire" "san%20juan%20capistrano%20fire" "san%20clemente%20fire"; do
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
python3 build.py || exit 1
git add -A >/dev/null && git commit -qm "refresh $(date '+%m/%d %H:%M')" 2>/dev/null && git push -q && echo "$(date '+%F %T') pushed" >> ~/.norte-fire-refresh.log
