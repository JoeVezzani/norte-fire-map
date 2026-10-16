#!/usr/bin/env python3
"""Capture Watch Duty incident 124958 data by loading their app in headless Chromium and recording the API responses it makes. Writes wd.json."""
import json, time, sys, os
from playwright.sync_api import sync_playwright
os.chdir(os.path.dirname(os.path.abspath(__file__)))
caught = {}
with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    ctx = b.new_context(user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36')
    pg = ctx.new_page()
    def on_resp(r):
        u = r.url
        if 'api.watchduty.org' not in u: return
        if not ('124958' in u or 'perimeter' in u.lower() or 'progression' in u.lower()): return
        try: body = r.json()
        except Exception: return
        key = u if 'perimeter' in u.lower() else u.split('?')[0] + ('?limit' if 'limit=' in u else '?latlng' if 'has_lat_lng' in u else '')
        caught[key] = body
    pg.on('response', on_resp)
    try:
        pg.goto('https://app.watchduty.org/i/124958', wait_until='load', timeout=60000); pg.wait_for_timeout(12000)
    except Exception as e: print('goto', str(e)[:120])
    b.close()
ev = next((v for k, v in caught.items() if k.endswith('geo_events/124958')), None)
reps = next((v for k, v in caught.items() if 'reports' in k and k.endswith('?limit')), None)
photos = next((v for k, v in caught.items() if 'reports' in k and k.endswith('?latlng')), None)
if not ev: sys.exit('no event captured')
items = reps.get('results', reps) if isinstance(reps, dict) else (reps or [])
ph = photos.get('results', photos) if isinstance(photos, dict) else (photos or [])
out = {'fetched': time.strftime('%Y-%m-%dT%H:%M'), 'event': {k: ev.get(k) for k in ('id','name','lat','lng','address','is_active','date_created','date_modified')},
       'data': {k: ev.get('data', {}).get(k) for k in ('acreage','containment','evacuation_orders','evacuation_warnings','evacuation_advisories','evacuation_notes')},
       'reports': [{'t': r.get('date_created'), 'msg': r.get('message'), 'lat': r.get('lat'), 'lng': r.get('lng'), 'media': [m.get('url') for m in (r.get('media') or []) if isinstance(m, dict) and m.get('url')]} for r in items if r.get('message')],
       'photos': [{'t': r.get('date_created'), 'lat': r.get('lat'), 'lng': r.get('lng'), 'media': [m.get('url') for m in (r.get('media') or []) if isinstance(m, dict) and m.get('url')]} for r in ph if r.get('lat') is not None]}
perims={k:v for k,v in caught.items() if 'perimeter' in k.lower()}
if perims: json.dump(perims, open('wd_perim.json','w'))
json.dump(out, open('wd.json', 'w'))
print('wd ok', out['data']['acreage'], out['data']['containment'], len(out['reports']), 'reports', len(out['photos']), 'photos')
