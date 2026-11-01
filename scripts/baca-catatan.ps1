# Kumpulkan seluruh dokumen proyek dalam satu output.
#
# Dipakai untuk menyuplai konteks ke AI di luar OpenCode (yang tidak otomatis
# membaca AGENTS.md). Output ditulis ke file teks di folder temp.
#
# Sumber utama: PROJECT.md di akar repo. Kalau folder vault Obsidian masih ada
# di laptop (mis. milik lead), catatannya ikut dibaca sebagai lampiran.

$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot
$out = Join-Path $env:TEMP 'warisan-bunaken-catatan.txt'

$docs = @(
    'PROJECT.md',
    'CONTRIBUTING.md',
    'AGENTS.md',
    'README.md',
    'docs/renders.md',
    'docs/credits.md',
    'docs/prompts-imagegen.md'
)

$sb = New-Object System.Text.StringBuilder

foreach ($rel in $docs) {
    $path = Join-Path $root $rel
    if (-not (Test-Path $path)) { continue }
    [void]$sb.AppendLine("`n===== $rel =====")
    [void]$sb.AppendLine((Get-Content $path -Raw))
}

# Lampiran opsional: vault Obsidian lokal (tidak ada di repo).
$vault = Join-Path $root 'Obsidian-Project-Animasi'
if (Test-Path $vault) {
    $order = '00-Proyek', '10-Cerita', '20-Produksi', '30-Aset', '40-Panduan', '50-Rapat', '90-Arsip'
    foreach ($folder in $order) {
        $dir = Join-Path $vault $folder
        if (-not (Test-Path $dir)) { continue }
        Get-ChildItem $dir -Filter '*.md' -File | Sort-Object Name | ForEach-Object {
            [void]$sb.AppendLine("`n===== vault/$folder/$($_.Name) =====")
            [void]$sb.AppendLine((Get-Content $_.FullName -Raw))
        }
    }
}

if ($sb.Length -eq 0) {
    Write-Error "Tidak ada dokumen yang terbaca di: $root"
    exit 1
}

$text = $sb.ToString()
Set-Content -Path $out -Value $text -Encoding utf8

Write-Host "Catatan terbaca: $($text.Length) karakter"
Write-Host "Disimpan ke    : $out"
