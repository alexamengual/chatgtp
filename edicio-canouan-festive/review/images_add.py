"""Add images from data/pass4-r*.json for artists that have none yet; updates data/images.json and review/img/.

Run from edicio-canouan-festive/ after review/build.py. Leaves existing images untouched.
"""
import glob, io, json, re, urllib.request, concurrent.futures as cf
from urllib.parse import urlparse
from PIL import Image

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
H = 260
page = open("review/canouan-edition-longlist.html").read()
data = json.loads(re.search(r'type="application/json">(.*?)</script>', page, re.S).group(1).replace("<\\/", "</"))
ids = {a["name"]: a["id"] for a in data["artists"]}
images = json.load(open("data/images.json"))

def fetch(job):
    aid, n, w = job
    try:
        raw = urllib.request.urlopen(urllib.request.Request(w["img"], headers={"User-Agent": UA, "Referer": w.get("page") or ""}), timeout=25).read()
        im = Image.open(io.BytesIO(raw)).convert("RGB")
        if im.width < 150 or im.height < 150: return None
        r = im.width / im.height
        if r > 4 or r < 0.25: return None
        im = im.resize((max(1, round(H * r)), H), Image.LANCZOS)
        path = f"img/{aid}-p{n}.jpg"
        im.save(f"review/{path}", "JPEG", quality=74, optimize=True, progressive=True)
        page_url = w.get("page") or w["img"]
        return aid, {"title": w.get("title"), "year": w.get("year"), "url": page_url, "thumb": path,
                     "source": urlparse(page_url).netloc.replace("www.", ""), "w": im.width, "h": H}
    except Exception:
        return None

jobs = []
for f in sorted(glob.glob("data/pass4-r*.json")):
    for r in json.load(open(f)):
        aid = ids.get(r["name"])
        if not aid or images.get(aid) or not r.get("found"): continue
        for n, w in enumerate(r.get("images", [])[:4]):
            if w.get("img"): jobs.append((aid, n, w))
added = {}
with cf.ThreadPoolExecutor(12) as ex:
    for res in ex.map(fetch, jobs):
        if res: added.setdefault(res[0], []).append(res[1])
for k, v in added.items():
    images[k] = sorted(v, key=lambda x: x["thumb"])[:3]
json.dump(images, open("data/images.json", "w"), ensure_ascii=False, indent=1)
print("artists added", len(added), "| images added", sum(len(v[:3]) for v in added.values()))
