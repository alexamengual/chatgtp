"""Build review/canouan-edition-longlist.html from the research data.

Usage: python3 -I review/build.py   (run from edicio-canouan-festive/)
"""
import json, re, unicodedata

AZ = json.load(open("data/az-artists.json"))
EXTRA = json.load(open("review/extra.json"))

def slug(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")[:60]

def country_key(c):
    if not c: return ""
    c = re.split(r"[/(;,]", c)[0].strip()
    return {"Curacao": "Curaçao", "UK (Scotland)": "UK"}.get(c, c)

def life(r):
    b, d = r.get("born"), r.get("died")
    if b and d: return f"{b}–{d}"
    if b: return f"b. {b}"
    if d: return f"d. {d}"
    return ""

def living(v):
    return "living" if v is True else "deceased" if v is False else "unknown"

def clean(v):
    return "" if v in (None, "unknown", "Unknown") else str(v)

def strip_boiler(note):
    note = clean(note)
    note = re.sub(r"\s*\[[^\]]*\]", "", note)
    note = re.sub(r"\s*\([^)]*(knowledge|verified|search budget|unverified)[^)]*\)", "", note, flags=re.I)
    note = re.sub(r"(?i)\bNOT[ -](web-|search-)?verified[^.;]*[.;]?\s*", "", note)
    note = re.sub(r"(?i)from (my own |general |background )?knowledge[^.;]*[.;]?\s*", "", note)
    note = re.sub(r"\s{2,}", " ", note).strip(" ;.-")
    if len(note) > 200:
        cut = note[:200]
        end = max(cut.rfind(". "), cut.rfind("; "))
        note = cut[:end + 1] if end > 80 else cut[:cut.rfind(" ")] + "…"
    return note

artists = []
for r in AZ:
    a = {
        "id": "a-" + slug(r["name"]), "name": r["name"], "pools": ["az"],
        "country": clean(r.get("country")), "based": clean(r.get("based")),
        "life": life(r), "living": living(r.get("living")), "medium": clean(r.get("medium")),
        "gallery": clean(r.get("gallery")), "editions": clean(r.get("editions")),
        "site": r.get("website") or "", "ig": r.get("instagram") or "",
        "note": strip_boiler(r.get("note3") or r.get("note")), "verified": bool(r.get("researched")), "tags": [],
        "born": r.get("born"), "died": r.get("died"), "origin": clean(r.get("origin_country")),
        "residence": clean(r.get("residence")) or clean(r.get("based")), "works": r.get("works") or [],
    }
    a["pools"] += EXTRA["poolAdd"].get(r["name"], [])
    a["note"] = EXTRA.get("noteOverride", {}).get(r["name"], a["note"])
    if r["name"] in EXTRA["tagAdd"]:
        a["tags"].append({"label": EXTRA["tagAdd"][r["name"]], "cls": "svg"})
    artists.append(a)

for e in EXTRA["artists"]:
    a = {"id": "x-" + slug(e["name"]), "life": "", "based": "", "medium": "", "gallery": "",
         "editions": "", "site": "", "ig": "", "note": "", "tags": [], "works": [], **e}
    a["origin"] = clean(e.get("origin_country")) or a.get("country", "")
    a["residence"] = clean(e.get("residence")) or a.get("based", "")
    if e.get("note3"): a["note"] = strip_boiler(e["note3"])
    a.pop("origin_country", None); a.pop("note3", None)
    if "svg" in a["pools"] and not any(t.get("cls") == "svg" for t in a["tags"]):
        a["tags"] = a["tags"] + [{"label": "St Vincent & Grenadines", "cls": "svg"}]
    artists.append(a)

CARIB = ["jamaica", "trinidad", "tobago", "barbados", "bahamas", "nassau", "haiti", "port-au-prince", "cuba", "havana",
         "dominican republic", "santo domingo", "puerto rico", "san juan", "guyana", "georgetown", "suriname", "paramaribo",
         "martinique", "guadeloupe", "curaçao", "curacao", "aruba", "sint maarten", "st. martin", "saint-martin", "st martin",
         "st vincent", "saint vincent", "kingstown", "bequia", "grenada", "saint lucia", "st lucia", "dominica", "antigua",
         "cayman", "virgin islands", "st. croix", "st croix", "bermuda", "french guiana", "guyane", "moengo", "léogâne",
         "kingston", "port of spain", "mariani", "cap-haïtien", "loíza", "montego bay", "fort-de-france", "baie-mahault", "caribbean"]
ABROAD = ["usa", "united states", "new york", "brooklyn", "miami", "los angeles", "chicago", "boston", "washington", "baltimore",
          "atlanta", "philadelphia", "colorado", "ohio", "nashville", "new jersey", "staten island", "austin", "bronx", "queens",
          " uk", "united kingdom", "london", "england", "cornwall", "scotland", "hastings", "cambridgeshire", "canada", "toronto",
          "montreal", "vancouver", "victoria", "ontario", "france", "paris", "netherlands", "amsterdam", "rotterdam", "den haag",
          "germany", "berlin", "spain", "madrid", "barcelona", "gran canaria", "las palmas", "mexico", "mérida", "vienna", "austria",
          "denmark", "copenhagen", "japan", "nagoya", "abidjan", "north carolina", "abroad"]

def lives_region(res):
    s = " " + (res or "").lower()
    if not res.strip(): return ""
    c = any(k in s for k in CARIB)
    a = any(k in s.replace("port of spain", "") for k in ABROAD)
    return "both" if c and a else "caribbean" if c else "abroad" if a else ""

THIS_YEAR = 2026
for a in artists:
    b = a.get("born")
    try: b = int(str(b)[:4]) if b else None
    except ValueError: b = None
    if b is None:
        m = re.search(r"b\. (\d{4})", a.get("life", "")); b = int(m.group(1)) if m else None
    a["born"] = b
    a["age"] = THIS_YEAR - b if b and a["living"] != "deceased" else None
    old = a["living"] == "deceased" or (a["age"] is not None and a["age"] > 75)
    a["section"] = "master" if old else "main"
    if a["living"] == "deceased" and b and a.get("died"): a["life"] = f"{b}–{a['died']}"
    a["livesRegion"] = lives_region(a.get("residence", ""))
    a["works"] = [w for w in (a.get("works") or []) if isinstance(w, dict) and w.get("title")][:3]
    if not a.get("origin"): a["origin"] = a.get("country", "")

for a in artists:
    a["countryKey"] = country_key(a["origin"] or a["country"])
    a["hay"] = " ".join(str(a.get(k, "")) for k in ("name", "country", "origin", "residence", "medium", "gallery", "note")).lower()
    a["hay"] += " " + " ".join(w["title"] for w in a["works"]).lower()
    a["hay"] += " " + " ".join(t["label"] for t in a["tags"]).lower()

# Order: SVG and Mustique first, then the rest alphabetically by surname
rank = lambda a: (0 if "svg" in a["pools"] else 1 if "mustique" in a["pools"] else 2 if set(a["pools"]) & {"lesiles", "scott"} else 3,
                  a["name"].split()[-1].lower())
artists.sort(key=rank)

advisors = [
    ("Holly Bynoe", "St Vincent & the Grenadines / The Bahamas", "Vincentian curator, artist and writer. Former Chief Curator, National Art Gallery of The Bahamas; co-founder of ARC Magazine (with Nadia Huggins) and Tilting Axis; earlier with The Hub Collective on Bequia. Already in Alex's network.", "https://hollybynoe.com", "dated"),
    ("Annalee Davis", "Barbados", "Artist; founded Fresh Milk (2011), co-founded Caribbean Linked (2012) and Tilting Axis (2015). The region's residency and network infrastructure.", "https://annaleedavis.com", "checked"),
    ("Veerle Poupeye", "Jamaica / Cayman Islands", "Author of Caribbean Art (Thames & Hudson, 2022 edition). Ex-Executive Director, National Gallery of Jamaica; Director, Cayman Islands National Museum since Nov 2024.", "https://veerlepoupeye.com", "checked"),
    ("Marina Reyes Franco", "Puerto Rico", "Independent curator and writer; ex-Curator, MAC Puerto Rico. Curated Tropical Is Political (2022), the art-and-tourism critique the project must answer.", "", "checked"),
    ("Marsha Pearce", "Trinidad and Tobago", "Lecturer and Deputy Dean, UWI St Augustine; British Academy Global Professor with the Fitzwilliam Museum; on the 2024 Mustique longlist jury.", "https://fitzmuseum.cam.ac.uk/about-us/our-staff/profile/marsha-pearce", "checked"),
    ("Natalie Urquhart", "Cayman Islands", "Director, National Gallery of the Cayman Islands (since 2009); founder of Cayman Art Week.", "https://www.nationalgallery.org.ky/about/staff/natalie-urquhart/", "checked"),
    ("Nicole Smythe-Johnson", "Jamaica", "Assistant Professor, Boston University; ex-Senior Curator, National Gallery of Jamaica; Kingston Biennial 2022 team.", "https://www.bu.edu/haa/profile/nicole-smythe-johnson/", "checked"),
    ("Annie Paul", "Jamaica", "Writer and critic, UWI Mona; founding editor of Small Axe; editor of PREE; National Gallery of Jamaica board.", "", "dated"),
    ("Melanie Archer", "Trinidad and Tobago", "Co-editor of the A to Z; co-founder of Robert & Christopher Publishers. A publishing peer.", "https://robertandchristopher.com", "to check"),
    ("Mariel Brown", "Trinidad and Tobago", "Co-editor of the A to Z; co-founder of Robert & Christopher; filmmaker.", "https://robertandchristopher.com", "to check"),
    ("Dominique Brebion", "Martinique", "Art critic; arts adviser to Martinique's regional cultural affairs office; co-founder of AICA Southern Caribbean.", "", "dated"),
    ("Gerald Alexis", "Haiti", "Haitian art critic and historian.", "", "dated"),
    ("Tirzo Martha", "Curaçao", "Artist; co-founder of Instituto Buena Bista, Curaçao's art school.", "", "to check"),
    ("Susanne Fredricks", "Jamaica", "Art consultant and organiser.", "", "to check"),
    ("Pat Ganase", "Trinidad and Tobago", "Writer and editor.", "", "to check"),
    ("Judy Raymond", "Trinidad and Tobago", "Writer and editor.", "", "to check"),
    ("Indra Khanna", "Guyana", "Curator and writer.", "", "to check"),
    ("José Manuel Noceda", "Cuba", "Curator and writer.", "", "to check"),
    ("Lilliana Ramos Collado", "Puerto Rico", "Writer and critic.", "", "to check"),
    ("Anjeni Ramtahal", "Trinidad / Amsterdam", "Curator of the Mustique show; founder of LES ÎLES (Prinsengracht 72hs, Amsterdam; team@lesiles.com). Alex knows her personally.", "https://www.lesiles.com", "checked"),
    ("Tiqui Atencio Demirdjian", "Mustique", "Founder and sponsor of the Mustique Caribbean Contemporary Art Show; collector. Alex knows her personally.", "https://mustiqueart.com", "checked"),
]
adv = []
for name, region, role, site, status in advisors:
    adv.append({"id": "v-" + slug(name), "name": name, "region": region, "role": role, "site": site,
                "ig": "", "status": status, "hay": f"{name} {region} {role}".lower()})

data = json.dumps({"artists": artists, "advisors": adv}, ensure_ascii=False, separators=(",", ":"))
data = data.replace("</", "<\\/")
page = open("review/template.html").read().replace("/*DATA*/", data)
open("review/canouan-edition-longlist.html", "w").write(page)
print(len(artists), "artists;", len(adv), "advisors;", len(page) // 1024, "KB")
