"""Menambahkan bagian 'Log progres' ke setiap agent di .opencode/agents/.

Idempoten: kalau bagian sudah ada, file tidak diubah.

Jalankan: python scripts/add-agent-logging.py
"""

from pathlib import Path

AGENTS = Path(".opencode/agents")

BLOCK = """
## Log progres (wajib)

Setiap tahap, tambahkan satu baris ke `renders/logs/{name}.log` (folder
gitignored), format:

```
[HH:MM] FASE — ringkasan satu baris
```

Fase: PLAN, BRIEF, MCP, MODEL, RIG, ANIM, LOOK, VERIFY, DONE, BLOCKED.
Tulis lewat shell atau `execute_blender_code` (Python). Tujuannya supaya
Director dan lead bisa memantau tanpa menunggu laporan akhir.

Director memantau dengan:

```powershell
powershell -File scripts/watch-agent-log.ps1 {name}
```
"""

MARKER = "## Log progres (wajib)"


def main():
    changed = 0
    for path in sorted(AGENTS.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        if MARKER in text:
            print("sudah ada:", path.stem)
            continue
        path.write_text(text.rstrip() + "\n" + BLOCK.format(name=path.stem),
                        encoding="utf-8")
        changed += 1
        print("ditambahkan:", path.stem)
    print("total diubah:", changed)


if __name__ == "__main__":
    main()
