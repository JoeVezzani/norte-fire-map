#!/bin/zsh
# Re-pull LunarCrush posts + rebuild + push. Run: ~/norte-fire-map/refresh.sh
cd ~/norte-fire-map || exit 1
K=$(security find-generic-password -a lunarcrush -s lunarcrush-api-key -w)
curl -s -A "Mozilla/5.0 curl" "https://lunarcrush.com/api4/public/searches/search?term=norte%20fire" -H "Authorization: Bearer $K" -o lc_raw.json
python3 -I - <<'PY'
import json
d=json.load(open('lc_raw.json')).get('data',[])
kw=('fire','evacu','capistrano','clemente','ocfa','ramblas','mirada','brush','smoke')
keep=[p for p in d if any(k in ((p.get('post_title') or '')+(p.get('text') or '')).lower() for k in kw) and 'tecate' not in ((p.get('post_title') or '')+(p.get('text') or '')).lower()]
json.dump(keep,open('posts_keep.json','w')); print('posts',len(keep))
PY
python3 build.py && git add -A && git commit -qm "refresh posts $(date '+%m/%d %H:%M')" && git push -q && echo pushed
