#Requires -Version 5.1
# 打包 pdftomd 供新機器安裝使用（不含 venv、不含已轉換的輸出）
$BASE = Split-Path -Parent $MyInvocation.MyCommand.Path
$OUT  = Join-Path $BASE "pdftomd_dist.zip"

if (Test-Path $OUT) { Remove-Item $OUT -Force }

$include = @(
    "install.ps1",
    "convert_mineru.py",
    "convert_docling.py"
)

# 建暫存目錄
$tmp = Join-Path $env:TEMP "pdftomd_pack"
if (Test-Path $tmp) { Remove-Item $tmp -Recurse -Force }
New-Item -ItemType Directory $tmp | Out-Null

foreach ($f in $include) {
    Copy-Item (Join-Path $BASE $f) $tmp
}

# 建空的輸入/輸出資料夾結構（放 .gitkeep 讓資料夾存在）
foreach ($dir in @("note\input","note\output\images","dev\input","dev\output\images")) {
    $d = Join-Path $tmp $dir
    New-Item -ItemType Directory -Force $d | Out-Null
    "" | Set-Content (Join-Path $d ".gitkeep")
}

Compress-Archive -Path "$tmp\*" -DestinationPath $OUT
Remove-Item $tmp -Recurse -Force

Write-Host "[OK] 已建立：$OUT" -ForegroundColor Green
Write-Host "     新機器解壓後，右鍵 install.ps1 > 以 PowerShell 執行 即可。" -ForegroundColor Cyan
