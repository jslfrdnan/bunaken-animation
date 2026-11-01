# Prompt Gemini — Frame Storyboard & Concept Art

Isi file: **1 prompt lembar gabungan** (2 shot per scene, sekali jadi untuk
menyusun alur storyboard) + **15 prompt satuan** untuk frame dan aset.

**Model:** Gemini 2.5 Flash Image
**Bahasa:** Inggris (hasil paling stabil)
**Rasio:** 16:9 (`--ar 16:9` untuk tool lain; di Gemini tulis "16:9 widescreen" di akhir prompt)
**Referensi:** maksimal **3 gambar per prompt**

## Dua gaya, dua keperluan

| Prompt | Gaya | Untuk apa |
|---|---|---|
| **00** (lembar 8 panel, 2 shot per scene) | **Sketsa hitam-putih** | Menyusun **alur storyboard 4 scene sekali jadi**. Ringkas, untuk rapat dan pengecekan alur — bukan acuan produksi per shot. |
| **01–09** (key art, character sheet, environment) | **Berwarna** — stylized semi-realistis | Acuan **konsep akhir**: bentuk, proporsi, warna, material. Dipakai Anggota 5 (Karakter) & 7 (Lighting). |
| **10–15** (frame storyboard) | **Sketsa hitam-putih** | Acuan **framing & komposisi** per shot. Sketsa hanya bahasa penyajian storyboard — **film final tetap berwarna** sesuai `03-gaya-visual.md`. |

> Jangan tertukar: sketsa hitam-putih **bukan** look film. Palette dan look
> akhir tetap yang berwarna, terkunci di `20-Produksi/03-gaya-visual.md`.

## Cara pakai (penting)

1. **Selalu unggah 1–3 referensi**:
   - `ref-environment-bunaken.jpg` — foto aerial Bunaken (dermaga merah-putih, Gunung Manado Tua)
   - `ref-char-nara-sheet.png` — character sheet Nara (dari prompt 02)
   - `ref-char-haris-sheet.png` — character sheet Pak Haris (dari prompt 05)
2. **Pakai seed tetap** untuk semua frame dalam satu scene: `seed: 20261102`
   Ganti seed hanya kalau ingin variasi baru.
3. Simpan hasil ke `storyboard/frames/scene-1/` dengan nama
   `scene-1_shot-010_v001.png`.
4. Kalau karakter melenceng, ulangi dengan **hanya** character sheet (tanpa
   environment reference) lalu komposit manual.
5. Pakai blok gaya yang sesuai barisnya: **STYLE BLOCK** (warna) untuk 01–09,
   **SKETCH STYLE BLOCK** (hitam-putih) untuk 00 dan 10–15.

> ⚠️ Foto referensi Bunaken hanya dipakai sebagai **acuan visual untuk prompt**.
> Jangan dimasukkan ke film atau repo kalau bukan milik sendiri.

## Blok gaya A — BERWARNA (untuk prompt 01–09)

```
STYLE BLOCK: stylized semi-realistic 3D animation still, Pixar-adjacent but
grounded and believable, tropical color palette (teal #1FA3A3, reef green
#3E8E6E, coral orange #E4713C, warm sand #E8D5B0), soft cinematic lighting,
subtle subsurface scattering on skin, clean composition, no text, 16:9
widescreen.
```

```
NEGATIVE: photorealistic skin pores, gritty darkness, horror tones, extra
limbs, deformed hands, duplicate faces, watermark, signature, text, logo,
oversaturated neon, plastic-looking water, western facial features
```

## Blok gaya B — SKETSA HITAM-PUTIH (untuk prompt 10–15)

```
SKETCH STYLE BLOCK: black-and-white storyboard sketch, graphite pencil
drawing on white paper, loose confident linework with visible construction
lines, grey marker shading for values, cross-hatching in shadow areas,
simplified forms, clear silhouette, readable composition, no color,
16:9 widescreen.
```

```
NEGATIVE: color, colored pencil, watercolor, paint wash, tinted paper, 3D
render, CGI, glossy surfaces, photorealistic skin pores, photographic
texture, neon glow, solid black ink flood fill, blurry linework, random
scribbles, messy scratchy noise, watermark, signature, text, logo, extra
limbs, deformed hands, duplicate faces
```

---

## 00 — Lembar 2 shot per scene (8 panel, sekali jadi)

Dipakai untuk **menyusun storyline storyboard** dari `10-Cerita/02-sinopsis.md`:
satu baris = satu scene, panel kiri = shot pembuka scene, panel kanan = shot
titik belok scene. Satu kali generate, satu gambar.

Output: `storyboard/frames/storyboard-2shot-per-scene_v001.jpg`
(hasil Gemini keluar sebagai JPEG; simpan apa adanya, jangan di-rename ke
`.png`)

```
A single storyboard sheet for a 4-scene short animated film set in Bunaken
National Park, Indonesia. ONE image containing EXACTLY EIGHT panels, arranged
in a grid of 2 columns and 4 rows. Each row is one scene; the left panel is
the opening shot of that scene, the right panel is the turning-point shot of
the same scene. Read left to right, top row (scene 1) down to bottom row
(scene 4). Thin hand-drawn panel borders. Under each panel write a small
handwritten label: 1A, 1B, 2A, 2B, 3A, 3B, 4A, 4B — letters and numerals
only, no other text anywhere. Same characters, same drawing style, and
consistent grey values in every panel.

Recurring characters, keep identical across panels:
Nara — 19-year-old Indonesian dive guide, short black hair, lean build,
faded rash guard, simple dive watch on the left wrist, dive mask when
underwater.
Pak Daniel — 52-year-old fisherman, father of Nara, weathered face, short
greying hair, sturdy build, woven sun hat.
Pak Haris — 45-year-old migrant fisherman, thin moustache, tired eyes, wiry
build, faded cap, worn shirt, small scar on the right forearm. He must look
under pressure, never villainous.

Panel contents in order:

1A — wide aerial view of Bunaken island in late morning: long wooden pier
with red-and-white railings over clear shallows, small fishing boats and one
white speedboat, dense green vegetation to the shoreline, Mount Manado Tua
volcano on the left horizon.

1B — underwater medium shot of Nara gliding past a healthy coral head, small
bubbles rising, a green sea turtle swimming just behind him in soft focus,
shafts of sunlight from the surface.

2A — dawn, cold and quiet: a small fishing boat far out on flat water, seen
from a distance, a splash and a cluster of rising bubbles where something was
dropped, the Bunaken shoreline a dark shape on the horizon, one small figure
at the stern with his back to camera.

2B — the emotional blow: from behind Nara on the pier, he watches Pak Daniel
step onto Pak Haris's boat, Haris at the tiller. Nara small in the foreground,
the two men readable but not detailed, morning haze.

3A — Nara underwater holding a small underwater camera, filming a damaged
patch of reef: shattered coral rubble, a snagged bottom net, silt in the
water, heavy dark shading, his mask lit by the camera.

3B — confrontation on the pier: Nara facing Pak Haris, holding an open
ledger book; Haris silent with his eyes down, Pak Daniel standing apart with
his head lowered, a few villagers watching from a distance, long late
afternoon shadows.

4A — restoration work in daylight: villagers and Nara lowering an orange
mooring buoy from a boat, a coral transplant frame with small fragments
already placed on the seabed below, Pak Haris helping with a rope, hopeful
open composition.

4B — closing image: Nara standing at the end of the red-and-white pier, seen
from behind, looking out at the sea, a green sea turtle visible as a small
shape in the clear water below, calm morning light, wide open sky.

SKETCH STYLE BLOCK: black-and-white storyboard sketch, graphite pencil
drawing on white paper, loose confident linework with visible construction
lines, grey marker shading for values, cross-hatching in shadow areas,
simplified forms, clear silhouette, readable composition, no color,
16:9 widescreen.

NEGATIVE: color, colored pencil, watercolor, paint wash, tinted paper, 3D
render, CGI, glossy surfaces, photorealistic skin pores, photographic
texture, neon glow, solid black ink flood fill, blurry linework, random
scribbles, messy scratchy noise, watermark, signature, extra text or
captions beyond the panel labels, tagline text, extra limbs, deformed hands,
duplicate faces
```

Catatan:

- Referensi: 1 foto aerial Bunaken. Seed `20261102`.
- Grid 2×4 dipilih supaya tiap baris terbaca sebagai satu scene saat rapat.
- Lembar ini **ringkasan alur**, bukan pengganti frame per shot. Scene 1 yang
  detail tetap pakai prompt 10–12.
- Kalau panel keluar kurang dari 8, ulangi dengan menambahkan
  "EXACTLY EIGHT panels, count them" di awal prompt.
- Wajah Nara paling rawan berubah di panel 1B, 3A, 4A. Kalau melenceng,
  generate ulang panel itu saja dengan "match the attached character sheet
  exactly".

---

## 01 — Style anchor / key art

```
A cinematic key art frame for a short 3D animated film set in Bunaken
National Park, Indonesia. Split composition: above the waterline, a wooden
pier with red-and-white railings and small fishing boats; below the
waterline, a healthy coral reef with sun rays piercing turquoise water.
Use the attached Bunaken aerial photo as environment reference for island
shape, pier design, and boat colors. Mount Manado Tua visible in the far
background. Stylized semi-realistic 3D animation still, tropical palette,
soft cinematic lighting, 16:9 widescreen.
```
seed: 20261102 · refs: 1 (bunaken) · output: `storyboard/frames/scene-1/scene-1_keyart_v001.png`

---

## 02 — Character sheet: Nara

```
Character sheet of Nara, a 19-year-old Indonesian dive guide from Bunaken,
North Sulawesi. Short black hair, warm brown skin, lean build, friendly and
determined expression. Wearing a faded teal rash guard over dark board
shorts, simple dive watch on left wrist. Neutral A-pose, front view, three
quarter view, and side view side by side on a plain warm sand background.
Stylized semi-realistic 3D animation character design, tropical palette,
even studio lighting, 16:9 widescreen.
```
seed: 20261102 · refs: 0–1 · output: `assets/char/ref-char-nara-sheet.png`
> Simpan hasil ini — dipakai sebagai referensi di semua prompt berikutnya.

---

## 03 — Ekspresi Nara

```
Expression sheet of the same character Nara (Indonesian teenage dive guide,
teal rash guard, short black hair): six head-and-shoulders expressions in a
grid — calm, curious, worried, angry, heartbroken, hopeful smile. Consistent
facial structure and hair across all six. Stylized semi-realistic 3D
animation, tropical palette, neutral background, 16:9 widescreen.
```
seed: 20261102 · refs: 1 (nara sheet) · output: `assets/char/ref-char-nara-expressions.png`

---

## 04 — Character sheet: Pak Daniel

```
Character sheet of Pak Daniel, a 52-year-old Indonesian traditional fisherman
from Bunaken, father of Nara. Weathered dark skin, short greying hair, deep
smile lines, sturdy build. Wearing a faded blue long-sleeve shirt, rolled
trousers, and a woven sun hat. Neutral A-pose, front view, three quarter view,
side view on a plain warm sand background. Stylized semi-realistic 3D
animation character design, tropical palette, even studio lighting, 16:9
widescreen.
```
seed: 20261102 · refs: 0 · output: `assets/char/ref-char-daniel-sheet.png`

---

## 05 — Character sheet: Pak Haris

```
Character sheet of Pak Haris, a 45-year-old migrant fisherman who now lives
in Bunaken. Sun-darkened skin, thin moustache, tired eyes, wiry build, a
small scar on the right forearm. Wearing a worn grey t-shirt, dark shorts,
and a faded cap. Expression should read as hardened but not villainous —
a man under pressure. Neutral A-pose, front view, three quarter view, side
view on a plain warm sand background. Stylized semi-realistic 3D animation
character design, 16:9 widescreen.
```
seed: 20261102 · refs: 0 · output: `assets/char/ref-char-haris-sheet.png`

---

## 06 — Environment: aerial Bunaken

```
Aerial establishing shot of Bunaken island at late morning. Long wooden pier
with red-and-white railings extending over clear turquoise shallows, small
white speedboats and colourful fishing boats moored along it, dense green
tropical vegetation, white sand beach, Mount Manado Tua volcano in the left
background. Use the attached Bunaken aerial photo as environment reference
for island shape, pier structure, and boat layout. Stylized semi-realistic
3D animation environment, tropical palette, soft haze, 16:9 widescreen.
```
seed: 20261102 · refs: 1 (bunaken) · output: `assets/env/ref-env-aerial.png`

---

## 07 — Environment: terumbu bawah laut

```
Underwater environment of a healthy Bunaken coral reef: branching and table
corals in teal, green and coral orange, schooling fusiliers, a green sea
turtle gliding past, shafts of sunlight cutting through clear turquoise
water, sandy patches below. No diver in frame. Stylized semi-realistic 3D
animation environment, volumetric god rays, tropical palette, 16:9 widescreen.
```
seed: 20261102 · refs: 1 (bunaken) · output: `assets/env/ref-env-reef.png`

---

## 08 — Environment: dive shop keluarga

```
Exterior of a small family-run dive shop on Bunaken: weathered wooden
building, hand-painted sign, drying wetsuits and fins hanging on a rack,
tanks stacked near the door, palm trees and bougainvillea, sandy path,
afternoon golden light. No people. Stylized semi-realistic 3D animation
environment, tropical palette, 16:9 widescreen.
```
seed: 20261102 · refs: 1 (bunaken) · output: `assets/env/ref-env-diveshop.png`

---

## 09 — Environment: dermaga kampung

```
Village pier in Bunaken at golden hour: red-and-white painted railings,
children's sandals left on the planks, fishing nets drying, a small
outrigger canoe tied to a post, warm sunlight, calm turquoise water,
silhouette of Mount Manado Tua. Use the attached Bunaken aerial photo as
environment reference for pier design. No people. Stylized semi-realistic
3D animation environment, 16:9 widescreen.
```
seed: 20261102 · refs: 1 (bunaken) · output: `assets/env/ref-env-pier.png`

---

## 10 — Frame storyboard: shot 010 (aerial) — sketsa

```
Storyboard frame, scene 1 shot 010: wide aerial push-in over Bunaken island
towards the long red-and-white pier, Mount Manado Tua on the left horizon,
boats trailing thin wakes, morning light. Use the attached Bunaken aerial
photo as environment reference for island shape and pier layout.
Black-and-white pencil storyboard sketch, loose hatching for vegetation and
water, clear silhouette, 16:9 widescreen.
```
seed: 20261102 · refs: 1 (bunaken) · output: `storyboard/frames/scene-1/scene-1_shot-010_v001.png`

---

## 11 — Frame storyboard: shot 050 (Nara menyelam) — sketsa

```
Storyboard frame, scene 1 shot 050: medium underwater shot of Nara (19-year-
old Indonesian dive guide, teal rash guard, dive mask) gliding past a coral
head, small bubbles rising, a green sea turtle in soft focus behind him.
Use the attached Nara character sheet for facial structure and outfit, and
the attached Bunaken aerial photo for water layout reference.
Black-and-white pencil storyboard sketch, god rays as light grey hatching,
darker grey shading toward the bottom of frame, 16:9 widescreen.
```
seed: 20261102 · refs: 2 (nara + bunaken) · output: `storyboard/frames/scene-1/scene-1_shot-050_v001.png`

---

## 12 — Frame storyboard: shot 070 (Nara naik ke perahu) — sketsa

> Nomor shot dikoreksi dari `080` → `070`; isi prompt ini memang shot 070 di
> `02-shotlist-scene-1.md`. Shot 080 adalah dive shop + Pak Daniel.

```
Storyboard frame, scene 1 shot 070: low angle from water level as Nara
climbs onto a wooden boat and pulls off his dive mask, wet hair, relieved
smile, the red-and-white pier out of focus behind. Use the attached Nara
character sheet for likeness. Black-and-white pencil storyboard sketch, grey
shading for wet hair and boat shadow, background simplified with light
hatching, 16:9 widescreen.
```
seed: 20261102 · refs: 1 (nara) · output: `storyboard/frames/scene-1/scene-1_shot-070_v001.png`

---

## 13 — Scene 2: terumbu setelah bom — sketsa

```
Storyboard frame, scene 2: a damaged patch of reef after an illegal blast
fishing incident — shattered coral rubble, pale dead coral heads, a few dead
fish floating, silt in the water, somber light. No people. Black-and-white
pencil storyboard sketch, heavy hatching and dark grey wash to show silt and
damage, flat heavy values, 16:9 widescreen.
```
seed: 20261103 · refs: 1 (bunaken) · output: `storyboard/frames/scene-2/scene-2_shot-030_v001.png`

---

## 14 — Scene 2: perahu nelayan mengebom — sketsa

```
Storyboard frame, scene 2: distant silhouetted small fishing boat at dawn on
calm water, a splash and rising bubbles where an explosive was dropped, the
Bunaken shoreline dark against the horizon. Haris visible only as a small
figure at the stern, back to camera. Black-and-white pencil storyboard
sketch, near-silhouette boat against a light grey sky, strong value contrast,
16:9 widescreen.
```
seed: 20261103 · refs: 1 (haris sheet) · output: `storyboard/frames/scene-2/scene-2_shot-050_v001.png`

---

## 15 — Scene 4: restorasi & key art penutup — sketsa

```
Storyboard frame, scene 4: underwater shot of a coral restoration frame with
young coral fragments growing, Nara and Pak Haris planting a fragment
together, shafts of sunlight, schools of small fish returning. Use the
attached Nara and Haris character sheets for likeness, and the Bunaken aerial
photo for water layout reference. Hopeful mood. Black-and-white pencil
storyboard sketch, bright light greys with open white space for god rays,
16:9 widescreen.
```
seed: 20261104 · refs: 3 (nara + haris + bunaken) · output: `storyboard/frames/scene-4/scene-4_shot-120_v001.png`

---

## Catatan konsistensi

### Untuk prompt berwarna (01–09)

- **Wajah melenceng** → ulangi dengan hanya 1 character sheet, tambahkan
  "match the attached character sheet exactly, same face, same hair".
- **Warna air terlalu neon** → tambahkan "muted turquoise, natural water
  color, slight green tint".
- **Terlihat seperti foto** → tambahkan "clearly stylized, simplified forms,
  animation look, not photorealistic".
- **Warna keluar dari palette** → tambahkan hex yang benar, mis.
  "teal #1FA3A3 for the water, no other blue".

### Untuk prompt sketsa (10–15)

- **Masih ada warna / ada tint** → tambahkan "pure black-and-white graphite
  sketch, no color at all, white paper".
- **Terlihat seperti render 3D atau foto** → tambahkan "hand-drawn pencil
  sketch, visible construction lines, clearly drawn by hand, not a render".
- **Terlalu gelap / blok hitam pekat** → tambahkan "light grey shading, open
  linework, keep most of the paper white".
- **Garis terlalu rapi seperti vektor** → tambahkan "sketchy hand-drawn
  linework, slightly uneven strokes".

### Berlaku untuk keduanya

- Jangan campur dua gaya dalam satu set gambar: 01–09 berwarna, 10–15 sketsa.
- Sketsa **tidak** mengubah look film. Warna final tetap dari
  `20-Produksi/03-gaya-visual.md`.
