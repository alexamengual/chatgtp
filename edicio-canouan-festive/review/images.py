"""Download up to 3 work images per collaboration-list artist and write thumbnails to review/img/.

Sources, in order: Artsy works (data/artsy.json), Mustique 2026 shop (review/extra.json),
then pages found in research (data/fallback-images.json). Writes data/images.json.
Run from edicio-canouan-festive/ after review/build.py.
"""
import io, json, re, sys, urllib.request, concurrent.futures as cf
from urllib.parse import urlparse
from PIL import Image

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
SKIP = re.compile(r"headshot|profile|portrait|hero\.|avatar|logo|wikimedia|_March_|scaled\.jpe?g|thumbnail_dm", re.I)
H = 260  # thumbnail height in px

page = open("review/canouan-edition-longlist.html").read()
data = json.loads(re.search(r'type="application/json">(.*?)</script>', page, re.S).group(1).replace("<\\/", "</"))
artsy = json.load(open("data/artsy.json"))
fallback = json.load(open("data/fallback-images.json"))
extra = {a["name"]: a for a in json.load(open("review/extra.json"))["artists"]}

def candidates(a):
    out = []
    out += [dict(w, source="Artsy") for w in artsy.get(a["name"], {}).get("works", [])]
    out += [dict(w, source="Mustique show") for w in extra.get(a["name"], {}).get("mustique_works", [])]
    out += [dict(w, source=urlparse(w["url"]).netloc.replace("www.", "")) for w in fallback.get(a["name"], [])]
    seen, res = set(), []
    for w in out:
        if w["img"] in seen or SKIP.search(w["img"]): continue
        seen.add(w["img"]); res.append(w)
    return res

def fetch(job):
    aid, n, w = job
    try:
        raw = urllib.request.urlopen(urllib.request.Request(w["img"], headers={"User-Agent": UA, "Referer": w["url"]}), timeout=25).read()
        im = Image.open(io.BytesIO(raw)); im = im.convert("RGB")
        if im.width < 150 or im.height < 150: return None
        r = im.width / im.height
        if r > 4 or r < 0.25: return None          # banners and strips are not artworks
        im = im.resize((max(1, round(H * r)), H), Image.LANCZOS)
        path = f"img/{aid}-{n}.jpg"
        im.save(f"review/{path}", "JPEG", quality=74, optimize=True, progressive=True)
        return aid, {"title": w.get("title"), "year": w.get("year"), "url": w["url"], "thumb": path, "source": w["source"], "w": im.width, "h": H}
    except Exception as e:
        return None

import os; os.makedirs("review/img", exist_ok=True)
for f in os.listdir("review/img"): os.remove(f"review/img/{f}")
jobs = []
for a in data["artists"]:
    if a["section"] != "main": continue
    for n, w in enumerate(candidates(a)[:4]):     # one spare in case a download fails
        jobs.append((a["id"], n, w))
res = {}
with cf.ThreadPoolExecutor(16) as ex:
    for r in ex.map(fetch, jobs):
        if r: res.setdefault(r[0], []).append(r[1])
for k in res: res[k] = sorted(res[k], key=lambda x: x["thumb"])[:3]
keep = {x["thumb"] for v in res.values() for x in v}
for f in os.listdir("review/img"):
    if f"img/{f}" not in keep: os.remove(f"review/img/{f}")
json.dump(res, open("data/images.json", "w"), ensure_ascii=False, indent=1)
size = sum(os.path.getsize(f"review/img/{f}") for f in os.listdir("review/img"))
print("artists with images", len(res), "| images", len(keep), "| MB", round(size / 1e6, 1))
