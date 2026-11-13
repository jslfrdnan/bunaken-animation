# run-agent-terminal.ps1 — jalankan agent di jendela PowerShell terpisah
#
# Pemakaian:
#   powershell -File scripts/run-agent-terminal.ps1 -Agent technical -Prompt "TUGAS: ..."
#   powershell -File scripts/run-agent-terminal.ps1 -Agent modeling  -Prompt "..." -Thinking
#
# Jendela baru akan terbuka, agent bekerja di sana, dan outputnya terlihat
# langsung. Catatan:
# - Ini sesi OpenCode BARU, bukan subagent dari sesi Director. Laporan akhirnya
#   tidak otomatis kembali ke Director; lihat jendelanya atau log agent.
# - Hanya satu instance Blender MCP: jangan jalankan saat Director sedang
#   memakai Blender.
# - Agent tetap memakai model & aturan dari .opencode/agents/<agent>.md.

param(
    [Parameter(Mandatory = $true)][string]$Agent,
    [Parameter(Mandatory = $true)][string]$Prompt,
    [switch]$Thinking
)

$root = Split-Path -Parent $PSScriptRoot
$promptFile = Join-Path $env:TEMP "oc-prompt-$Agent.txt"
$runnerFile = Join-Path $env:TEMP "oc-run-$Agent.ps1"

Set-Content -Path $promptFile -Value $Prompt -Encoding utf8

$thinkingFlag = ""
if ($Thinking) { $thinkingFlag = "--thinking" }

$runner = @"
Set-Location '$root'
`$prompt = Get-Content '$promptFile' -Raw
Write-Host '=== agent: $Agent ===' -ForegroundColor Cyan
opencode run --agent $Agent $thinkingFlag `$prompt
Write-Host ''
Write-Host '=== selesai. Jendela tetap terbuka. ===' -ForegroundColor DarkGray
"@

Set-Content -Path $runnerFile -Value $runner -Encoding utf8

Write-Host "Membuka jendela PowerShell untuk agent '$Agent'..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList @(
    '-NoExit',
    '-ExecutionPolicy', 'Bypass',
    '-File', $runnerFile
)
