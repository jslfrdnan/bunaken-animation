"""Cari kandidat aset karang + ikan (Scene 2/3) dari Sketchfab API & Poly Pizza.

Hanya CC0/CC-BY, low-poly. Output JSON {kategori: [kandidat...]} dengan thumbnail base64,
siap dipakai galeri_aset.py.

    python cari_aset_scene2.py <keluaran.json>
"""
import base64
import json
import re
import sys
import urllib.parse
import urllib.request

UA = {"User-Agent": "Mozilla/5.0"}
LIS_SK = {"CC Attribution", "CC0 Public Domain"}
MAKS_FACE = 40000
PER_KAT = 4

# kategori: (query list, kata wajib di nama, kata tolak)
KATEGORI = {
    "Karang meja": (["staghorn coral low poly", "table coral low poly", "branching coral low poly", "acropora coral"],
                    ["coral"], ["sword", "pixel", "flower", "grouper", "fish", "pack", "ring", "necklace"]),
    "Karang otak": (["brain coral low poly", "brain coral"], ["brain"], ["pack", "fish"]),
    "Karang kipas (gorgonian)": (["sea fan coral low poly", "gorgonian coral", "sea fan"],
                    ["fan", "gorgonian"], ["grouper", "fish", "flower", "pack", "ceiling"]),
    "Anemon laut": (["sea anemone low poly", "anemone low poly", "anemone"], ["anemone"], ["fish", "flower"]),
    "Spons tabung": (["sea sponge low poly", "tube sponge coral", "barrel sponge reef"],
                    ["sponge"], ["brush", "blender", "kitchen", "dish", "bob", "cake"]),
    "Ikan badut": (["clownfish low poly", "clown fish", "nemo fish"], ["clown", "nemo"], ["pack", "school", "skeleton"]),
    "Ikan ekor kuning/lalosi": (["tropical reef fish low poly", "yellow tang low poly", "reef fish low poly", "yellowtail fish"],
                    ["fish", "tang"], ["koi", "puffer", "clown", "nemo", "skeleton", "pixel", "tank", "shark", "whale", "angler"]),
}


def jget(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
        return json.load(r)


def bget(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
        return r.read()


def thumb(url):
    return "data:image/jpeg;base64," + base64.b64encode(bget(url)).decode()


def cari_sketchfab(query):
    q = urllib.parse.urlencode({"type": "models", "q": query, "downloadable": "true", "count": 24})
    return jget(f"https://api.sketchfab.com/v3/search?{q}")["results"]


def cand_sketchfab(m):
    g = sorted(m["thumbnails"]["images"], key=lambda t: abs(t["width"] - 360))
    return {"uid": m["uid"], "nama": m["name"], "pembuat": m["user"]["displayName"],
            "lisensi": (m.get("license") or {}).get("label", ""), "face": m["faceCount"],
            "animasi": m.get("animationCount", 0), "url": m["viewerUrl"], "sumber": "Sketchfab",
            "thumb": thumb(g[0]["url"])}


def cari_polypizza(query):
    h = bget("https://poly.pizza/search/" + urllib.parse.quote(query)).decode("utf-8", "ignore")
    return list(dict.fromkeys(re.findall(r"/m/([A-Za-z0-9_-]+)", h)))[:12]


def cand_polypizza(pid):
    h = bget("https://poly.pizza/m/" + pid).decode("utf-8", "ignore")
    m = re.search(r"__SERVER_APP_STATE__ =\s*(\{.*?\})</script>", h, re.S)
    if not m:
        return None
    d = json.loads(m.group(1))["initialData"]["model"]
    lis = d.get("Licence", "")
    if "CC0" not in lis and "CC-BY" not in lis:
        return None
    return {"uid": pid, "nama": d["Title"], "pembuat": d.get("Creator", {}).get("Username", "?"),
            "lisensi": lis, "face": d.get("Tris", 0), "animasi": 1 if d.get("Animated") else 0,
            "url": "https://poly.pizza/m/" + pid, "sumber": "Poly Pizza",
            "thumb": thumb("https://static.poly.pizza/" + d["ResourceID"] + ".webp")}


def main(keluar):
    hasil = {}
    for kat, (queries, wajib, tolak) in KATEGORI.items():
        picks, seen = [], set()
        # Sketchfab dulu
        for q in queries:
            try:
                res = cari_sketchfab(q)
            except Exception as e:
                print("  sk err", q, e); res = []
            for m in res:
                nm = m["name"].lower()
                lis = (m.get("license") or {}).get("label", "")
                if (m["uid"] in seen or lis not in LIS_SK or m["faceCount"] > MAKS_FACE
                        or not any(k in nm for k in wajib) or any(k in nm for k in tolak)):
                    continue
                seen.add(m["uid"])
                try:
                    picks.append(cand_sketchfab(m))
                except Exception as e:
                    print("  thumb err", e)
            if len(picks) >= PER_KAT:
                break
        # lengkapi dari Poly Pizza bila kurang
        if len(picks) < PER_KAT:
            for q in queries:
                for pid in cari_polypizza(q):
                    if pid in seen:
                        continue
                    seen.add(pid)
                    try:
                        c = cand_polypizza(pid)
                    except Exception:
                        c = None
                    if not c:
                        continue
                    nm = c["nama"].lower()
                    if not any(k in nm for k in wajib) or any(k in nm for k in tolak) or c["face"] > MAKS_FACE:
                        continue
                    picks.append(c)
                    if len(picks) >= PER_KAT + 2:
                        break
                if len(picks) >= PER_KAT + 2:
                    break
        # utamakan beranimasi (ikan) lalu teringan
        picks.sort(key=lambda k: (-min(k["animasi"], 1), k["face"]))
        hasil[kat] = picks[:PER_KAT]
        print(f"{kat}: {len(hasil[kat])}")
    json.dump(hasil, open(keluar, "w", encoding="utf-8"), ensure_ascii=False)


if __name__ == "__main__":
    main(sys.argv[1])
