#Requires -Version 5.1
<#
.SYNOPSIS
    pdftomd 打包腳本
.DESCRIPTION
    將 pdftomd 核心程式、安裝腳本與空資料夾結構打包成 pdftomd_dist.zip
    排除 venv 虛擬環境與個人轉換暫存檔，供其他使用者一鍵安裝使用。
#>

$BASE = Split-Path -Parent $MyInvocation.MyCommand.Path
$OUT  = Join-Path $BASE "pdftomd_dist.zip"

# 清理舊的輸出壓縮檔
if (Test-Path $OUT) { 
    Remove-Item $OUT -Force 
}

# 定義需要打包的核心檔案清單
$include = @(
    "install.ps1",
    "install.bat",
    "convert_mineru.py",
    "convert_docling.py",
    "使用說明.txt"
)

# 建立暫存目錄以組裝打包內容
$tmp = Join-Path $env:TEMP "pdftomd_pack"
if (Test-Path $tmp) { 
    Remove-Item $tmp -Recurse -Force 
}
New-Item -ItemType Directory $tmp | Out-Null

# 複製主要執行檔與安裝腳本
foreach ($f in $include) {
    $src = Join-Path $BASE $f
    if (Test-Path $src) {
        Copy-Item $src $tmp
    } else {
        Write-Warning "找不到檔案: $src"
    }
}

# 建立空的資料夾結構，讓解壓後能直接放入 input/output
$dirs = @(
    "note\input",
    "note\output\images",
    "dev\input",
    "dev\output\images"
)

foreach ($dir in $dirs) {
    $d = Join-Path $tmp $dir
    New-Item -ItemType Directory -Force $d | Out-Null
    "" | Set-Content -Path (Join-Path $d ".gitkeep") -Encoding utf8
}

# 壓縮為 ZIP 封裝檔
Compress-Archive -Path "$tmp\*" -DestinationPath $OUT -Force
Remove-Item $tmp -Recurse -Force

Write-Host "[OK] 已建立打包檔: $OUT" -ForegroundColor Green
Write-Host "     將 pdftomd_dist.zip 提供給他人，解壓縮後雙擊 install.bat 即可。" -ForegroundColor Cyan
