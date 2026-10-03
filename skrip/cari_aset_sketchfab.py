"""Cari kandidat aset publik di Sketchfab (hanya CC0 / CC-BY, dapat diunduh).

Pemakaian: python cari_aset_sketchfab.py <keluaran.json>
Menulis daftar kandidat per kategori + thumbnail (base64) untuk galeri verifikasi.
"""
import base64
import json
import sys
import urllib.parse
import urllib.request

LISENSI_OK = {"CC Attribution", "CC0 Public Domain"}
MAKS_FACE = 30000
PER_KATEGORI = 4

# kategori: (daftar query, kata kunci yang wajib ada di nama model)
KATEGORI = {
    "Pohon kelapa": (["low poly palm tree", "low poly coconut tree"], ["palm", "coconut"]),
    "Bakau": (["low poly mangrove tree", "mangrove tree", "mangrove"], ["mangrove tree", "mangrove"]),
    "Rumah panggung": (["stilt house low poly", "house on stilts", "fisherman hut low poly", "nipa hut"],
                       ["stilt", "hut", "house", "rumah"]),
    "Dermaga kayu": (["low poly wooden pier", "low poly wooden dock", "low poly jetty", "wooden pier"],
                     ["pier", "dock", "jetty", "dermaga"]),
    "Papan / gapura": (["low poly wooden sign", "wooden signboard low poly", "wooden sign board"],
                       ["wooden sign", "signboard", "sign board", "wood sign"]),
    "Perahu (→ katinting)": (["outrigger canoe low poly", "outrigger boat", "low poly wooden boat",
                             "low poly fishing boat", "low poly canoe"], ["boat", "canoe", "outrigger"]),
    "Nelayan ber-rig": (["low poly fisherman rigged", "low poly man rigged", "low poly character rigged animated"],
                        ["man", "guy", "fisherman", "character", "villager", "male"]),
    "Burung": (["low poly seagull animated", "low poly seagull", "low poly bird flying animated"],
               ["seagull", "gull", "bird"]),
    "Awan": (["low poly cloud", "low poly clouds pack"], ["cloud"]),
}
KATA_TOLAK = ["minecraft", "voxel", "exit", "sci-fi", "space", "paddle", "pack", "scene", "kitchen", "cabinet"]


def ambil_json(url):
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.load(r)


def ambil_thumbnail(model):
    gambar = sorted(model["thumbnails"]["images"], key=lambda t: abs(t["width"] - 360))
    with urllib.request.urlopen(gambar[0]["url"], timeout=30) as r:
        return "data:image/jpeg;base64," + base64.b64encode(r.read()).decode()


def cari(query):
    q = urllib.parse.urlencode({"type": "models", "q": query, "downloadable": "true", "count": 24})
    return ambil_json(f"https://api.sketchfab.com/v3/search?{q}")["results"]


def main(keluaran):
    hasil = {}
    for kategori, (daftar_query, kata_wajib) in KATEGORI.items():
        terpilih, uid_dilihat = [], set()
        for query in daftar_query:
            for m in cari(query):
                lisensi = (m.get("license") or {}).get("label", "")
                nama = m["name"].lower()
                if (m["uid"] in uid_dilihat or lisensi not in LISENSI_OK or m["faceCount"] > MAKS_FACE
                        or not any(k in nama for k in kata_wajib) or any(k in nama for k in KATA_TOLAK)):
                    continue
                uid_dilihat.add(m["uid"])
                terpilih.append({
                    "uid": m["uid"],
                    "nama": m["name"],
                    "pembuat": m["user"]["displayName"],
                    "profil": m["user"]["profileUrl"],
                    "lisensi": lisensi,
                    "face": m["faceCount"],
                    "animasi": m.get("animationCount", 0),
                    "url": m["viewerUrl"],
                    "query": query,
                })
            if len(terpilih) >= PER_KATEGORI * 2:
                break
        # utamakan yang sudah beranimasi (nelayan/burung), lalu yang paling ringan
        terpilih.sort(key=lambda k: (-min(k["animasi"], 1), k["face"]))
        hasil[kategori] = terpilih[:PER_KATEGORI]
        print(f"{kategori}: {len(hasil[kategori])} kandidat")
    for daftar in hasil.values():
        for k in daftar:
            k["thumb"] = ambil_thumbnail(ambil_json(f"https://api.sketchfab.com/v3/models/{k['uid']}"))
    with open(keluaran, "w", encoding="utf-8") as f:
        json.dump(hasil, f, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main(sys.argv[1])
