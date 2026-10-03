"""Bangun halaman galeri verifikasi aset dari keluaran cari_aset_sketchfab.py.

Pemakaian: python galeri_aset.py <kandidat.json> <galeri.html> "<judul scene>" ["<catatan atas>"]
Field opsional per kandidat: "sumber" (default "Sketchfab").
"""
import hashlib
import html
import json
import sys

CSS = """
:root{
  /* Layout: daftar kategori bertumpuk, tiap kategori satu baris kartu kandidat yang bisa dipilih */
  --laut:#0f3d6e; --toska:#1f9e9c; --pasir:#efe6cf; --kertas:#fbf8f1; --tinta:#1b2530; --redup:#5b6773;
  --garis:#ddd3bb; --kartu:#ffffff; --pilih:#1f9e9c; --tolak:#b4462f;
  --f-judul:"Bricolage Grotesque",system-ui,sans-serif; --f-isi:"Source Sans 3",system-ui,sans-serif;
  --f-data:"JetBrains Mono",ui-monospace,Consolas,monospace;
}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){
  --laut:#8cc4f2; --toska:#4fd1cf; --pasir:#1d2a36; --kertas:#0f1720; --tinta:#e6edf2; --redup:#98a6b3;
  --garis:#2c3b4a; --kartu:#16212c; --pilih:#4fd1cf; --tolak:#ef8a72; color-scheme:dark}}
:root[data-theme="dark"]{
  --laut:#8cc4f2; --toska:#4fd1cf; --pasir:#1d2a36; --kertas:#0f1720; --tinta:#e6edf2; --redup:#98a6b3;
  --garis:#2c3b4a; --kartu:#16212c; --pilih:#4fd1cf; --tolak:#ef8a72; color-scheme:dark}
body{background:var(--kertas);color:var(--tinta);font:16px/1.5 var(--f-isi);padding-inline:16px;padding-block:24px 120px}
.wrap{max-width:1120px;margin:0 auto;display:grid;gap:40px}
header{display:grid;gap:8px;border-bottom:2px solid var(--laut);padding-bottom:20px}
.eyebrow{font:600 12px/1 var(--f-data);letter-spacing:.12em;text-transform:uppercase;color:var(--toska)}
h1{font:700 clamp(28px,4vw,40px)/1.1 var(--f-judul);margin:0;color:var(--laut);text-wrap:balance}
header p{margin:0;max-width:68ch;color:var(--redup)}
section{display:grid;gap:14px}
.kepala{display:flex;flex-wrap:wrap;align-items:baseline;gap:8px 16px;justify-content:space-between}
h2{font:600 22px/1.2 var(--f-judul);margin:0}
.catatan{font-size:14px;color:var(--redup);margin:0;flex-basis:100%}
.tolak-semua{font:600 13px var(--f-isi);border:1px solid var(--garis);background:transparent;color:var(--tolak);
  padding:6px 12px;border-radius:999px;cursor:pointer}
.tolak-semua[aria-pressed="true"]{background:var(--tolak);color:var(--kertas);border-color:var(--tolak)}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:14px}
label.kartu{display:grid;grid-template-rows:auto 1fr;background:var(--kartu);border:2px solid var(--garis);border-radius:10px;
  overflow:hidden;cursor:pointer;transition:border-color .15s}
label.kartu:has(input:checked){border-color:var(--pilih);box-shadow:0 0 0 3px color-mix(in srgb,var(--pilih) 25%,transparent)}
label.kartu:has(input:focus-visible){outline:3px solid var(--laut);outline-offset:2px}
.kartu input{position:absolute;opacity:0;pointer-events:none}
.foto{position:relative;aspect-ratio:16/10;background:var(--pasir);max-width:100%}
.foto img{width:100%;height:100%;object-fit:cover;display:block}
.no{position:absolute;top:8px;left:8px;font:700 13px var(--f-data);background:var(--laut);color:var(--kertas);
  padding:3px 8px;border-radius:6px}
.centang{position:absolute;top:8px;right:8px;font:700 12px var(--f-isi);background:var(--pilih);color:var(--kertas);
  padding:3px 8px;border-radius:6px;display:none}
label.kartu:has(input:checked) .centang{display:block}
.info{padding:10px 12px 12px;display:grid;gap:6px;align-content:start;min-width:0}
.nama{font-weight:600;line-height:1.3;overflow-wrap:anywhere}
.meta{display:flex;flex-wrap:wrap;gap:6px;font:12px var(--f-data);color:var(--redup)}
.chip{border:1px solid var(--garis);border-radius:4px;padding:1px 6px;font-variant-numeric:tabular-nums}
.chip.anim{border-color:var(--toska);color:var(--toska)}
.info a{font-size:13px;color:var(--laut)}
.bar{position:fixed;left:0;right:0;bottom:0;background:var(--laut);color:var(--kertas);
  padding:12px 16px calc(12px + env(safe-area-inset-bottom,0px))}
.bar .isi{max-width:1120px;margin:0 auto;display:flex;flex-wrap:wrap;gap:10px;align-items:center;justify-content:space-between}
.bar code{font:13px var(--f-data);overflow-wrap:anywhere;min-width:0;flex:1 1 320px}
.bar button{font:600 14px var(--f-isi);background:var(--kertas);color:var(--laut);border:0;border-radius:8px;
  padding:8px 16px;cursor:pointer}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]) .bar{background:#0b2a4a;color:#e6edf2}}
:root[data-theme="dark"] .bar{background:#0b2a4a;color:#e6edf2}
@media (prefers-reduced-motion: reduce){label.kartu{transition:none}}
"""

JS = """
const KUNCI='galeri-aset-__ID__';
const bagian=[...document.querySelectorAll('section[data-kat]')];
function ringkas(){
  const potong=bagian.map(s=>{
    const kat=s.dataset.kat, p=s.querySelector('input:checked'), t=s.querySelector('.tolak-semua');
    return kat+': '+(t.getAttribute('aria-pressed')==='true'?'tolak semua':(p?p.value:'-'));
  });
  document.getElementById('ringkasan').textContent=potong.join('; ');
  try{localStorage.setItem(KUNCI,JSON.stringify(Object.fromEntries(bagian.map(s=>{
    const p=s.querySelector('input:checked');
    return [s.dataset.kat,{p:p?p.value:null,t:s.querySelector('.tolak-semua').getAttribute('aria-pressed')}];
  }))))}catch(e){}
}
try{const d=JSON.parse(localStorage.getItem(KUNCI)||'{}');bagian.forEach(s=>{const v=d[s.dataset.kat];if(!v)return;
  if(v.p){const i=s.querySelector('input[value="'+v.p+'"]');if(i)i.checked=true}
  s.querySelector('.tolak-semua').setAttribute('aria-pressed',v.t||'false')})}catch(e){}
bagian.forEach(s=>{
  s.addEventListener('change',()=>{s.querySelector('.tolak-semua').setAttribute('aria-pressed','false');ringkas()});
  s.querySelector('.tolak-semua').addEventListener('click',e=>{
    const b=e.currentTarget, on=b.getAttribute('aria-pressed')!=='true';
    b.setAttribute('aria-pressed',String(on)); if(on)s.querySelectorAll('input').forEach(i=>i.checked=false); ringkas();
  });
});
document.getElementById('salin').addEventListener('click',async e=>{
  const teks=document.getElementById('ringkasan').textContent, b=e.currentTarget;
  try{await navigator.clipboard.writeText(teks);b.textContent='Tersalin'}
  catch(err){const r=document.createRange();r.selectNodeContents(document.getElementById('ringkasan'));
    const s=getSelection();s.removeAllRanges();s.addRange(r);b.textContent='Teks dipilih, tekan Ctrl+C'}
  setTimeout(()=>b.textContent='Salin pilihan',2200);
});
ringkas();
"""

CATATAN = {
    "Rumah panggung": "Atap akan diganti seng dan material diseragamkan ke palet Bunaken.",
    "Perahu (→ katinting)": "Belum ada perahu bercadik berlisensi CC. Kandidat terpilih akan ditambah cadik dan mesin katinting.",
    "Papan / gapura": "Teks papan akan diganti \"Taman Nasional Bunaken\".",
    "Nelayan ber-rig": "Pakaian akan diwarnai ulang (kaos lusuh, celana pendek, topi). Animasi dibuat sendiri.",
    "Dermaga kayu": "Bila terlalu panjang atau ada bangunan, hanya bagian dermaganya yang dipakai.",
}


def kartu(kat_id, i, m):
    e = html.escape
    anim = f'<span class="chip anim">{m["animasi"]} animasi</span>' if m["animasi"] else ""
    return f"""<label class="kartu"><input type="radio" name="{kat_id}" value="K{i}">
<div class="foto"><img src="{m['thumb']}" alt="Pratinjau {e(m['nama'])}"><span class="no">K{i}</span><span class="centang">Dipilih</span></div>
<div class="info"><div class="nama">{e(m['nama'])}</div>
<div class="meta"><span class="chip">{m['face']:,} face</span><span class="chip">{e(m['lisensi'])}</span>{anim}</div>
<div class="meta">oleh {e(m['pembuat'])}</div>
<a href="{e(m['url'])}" target="_blank" rel="noopener">Lihat 3D di {e(m.get('sumber', 'Sketchfab'))} ↗</a></div></label>"""


PENGANTAR = ("Pilih satu kandidat per kategori, atau tekan \"Tolak semua\" bila tidak ada yang cocok. "
             "Semua kandidat berlisensi CC0/CC-BY dan bisa diunduh. "
             "Setelah selesai, salin ringkasan di bawah dan tempel ke chat.")


def main(masuk, keluar, judul, catatan_atas=""):
    data = json.load(open(masuk, encoding="utf-8"))
    pengantar = html.escape((catatan_atas + " " if catatan_atas else "") + PENGANTAR)
    kunci = hashlib.sha1("".join(m["uid"] for d in data.values() for m in d).encode()).hexdigest()[:10]
    bagian = []
    for n, (kat, daftar) in enumerate(data.items()):
        kat_id = f"kat{n}"
        catatan = f'<p class="catatan">{html.escape(CATATAN[kat])}</p>' if kat in CATATAN else ""
        kartu_html = "\n".join(kartu(kat_id, i + 1, m) for i, m in enumerate(daftar))
        bagian.append(f"""<section data-kat="{html.escape(kat)}"><div class="kepala"><h2>{html.escape(kat)}</h2>
<button type="button" class="tolak-semua" aria-pressed="false">Tolak semua, cari lagi</button>{catatan}</div>
<div class="grid">{kartu_html}</div></section>""")
    halaman = f"""<title>Galeri Aset {html.escape(judul)}</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,600;12..96,700&family=JetBrains+Mono:wght@400;700&family=Source+Sans+3:wght@400;600&display=swap">
<style>{CSS}</style>
<div class="wrap"><header><span class="eyebrow">Project Animasi Bunaken · verifikasi aset publik</span>
<h1>Galeri Aset {html.escape(judul)}</h1>
<p>{pengantar}</p></header>
{''.join(bagian)}</div>
<div class="bar"><div class="isi"><code id="ringkasan"></code><button type="button" id="salin">Salin pilihan</button></div></div>
<script>{JS.replace("__ID__", kunci)}</script>"""
    open(keluar, "w", encoding="utf-8").write(halaman)


if __name__ == "__main__":
    main(*sys.argv[1:5])
