# watch-agent-log.ps1 — pantau pekerjaan subagent secara langsung
#
# Pakai:
#   powershell -File scripts/watch-agent-log.ps1              # log terbaru
#   powershell -File scripts/watch-agent-log.ps1 technical    # log agent tertentu
#
# Log ditulis agent ke renders/logs/<agent>.log (gitignored), satu baris per
# tahap: [HH:MM] FASE — ringkasan.

param(
    [string]$Agent = ""
)

$root = Split-Path -Parent $PSScriptRoot
$logDir = Join-Path $root "renders\logs"

if (-not (Test-Path $logDir)) {
    Write-Host "Belum ada log. Folder: $logDir"
    Write-Host "Agent akan membuatnya saat mulai bekerja."
    exit 0
}

if ($Agent -ne "") {
    $file = Join-Path $logDir "$Agent.log"
} else {
    $latest = Get-ChildItem $logDir -Filter *.log | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if (-not $latest) {
        Write-Host "Belum ada file .log di $logDir"
        exit 0
    }
    $file = $latest.FullName
}

if (-not (Test-Path $file)) {
    Write-Host "Log tidak ditemukan: $file"
    exit 1
}

Write-Host "== memantau $file ==" -ForegroundColor Cyan
Write-Host "(Ctrl+C untuk berhenti)" -ForegroundColor DarkGray
Get-Content $file -Wait -Tail 25
