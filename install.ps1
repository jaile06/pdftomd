#Requires -Version 5.1
<#
.SYNOPSIS
    pdftomd 一鍵安裝腳本（適用全新 Win11，不需預先安裝任何東西）
.DESCRIPTION
    1. 偵測/安裝 Python 3.11
    2. 建立 .venv-mineru（MinerU）與 .venv-docling（Docling）虛擬環境
    3. pip 安裝依賴
    4. 下載 MinerU 模型（~2GB，首次需要網路與時間）
    5. 建立 run_mineru.bat 與 run_docling.bat 供日後雙擊使用
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$BASE = Split-Path -Parent $MyInvocation.MyCommand.Path
$PYTHON_MIN = [Version]"3.10"
$PYTHON_MAX = [Version]"3.14"   # MinerU 不支援 3.14+
$PYTHON_TARGET = "3.11"

function Write-Step($msg) { Write-Host "`n==> $msg" -ForegroundColor Cyan }
function Write-Ok($msg)   { Write-Host "    [OK] $msg" -ForegroundColor Green }
function Write-Warn($msg) { Write-Host "    [WARN] $msg" -ForegroundColor Yellow }
function Write-Fail($msg) { Write-Host "`n[FAIL] $msg" -ForegroundColor Red; exit 1 }

# ── 1. 找 Python ──────────────────────────────────────────────────────────────
Write-Step "檢查 Python 版本..."

function Find-Python {
    foreach ($cmd in @("python", "python3", "py")) {
        $exe = (Get-Command $cmd -ErrorAction SilentlyContinue)
        if (-not $exe) { continue }
        $ver = & $exe --version 2>&1
        if ($ver -match "Python (\d+\.\d+)") {
            $v = [Version]$Matches[1]
            if ($v -ge $PYTHON_MIN -and $v -lt $PYTHON_MAX) { return $exe.Source }
        }
    }
    return $null
}

$PYTHON = Find-Python

if (-not $PYTHON) {
    Write-Warn "找不到 Python $PYTHON_MIN+，嘗試用 winget 安裝 Python $PYTHON_TARGET..."
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        Write-Fail "winget 不可用。請先從 Microsoft Store 安裝『應用程式安裝程式』，或手動安裝 Python 3.11。"
    }
    winget install Python.Python.3.11 --silent --accept-package-agreements --accept-source-agreements
    if ($LASTEXITCODE -ne 0) { Write-Fail "winget 安裝 Python 失敗，請手動安裝後重試。" }
    # 重新整理 PATH
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" +
                [System.Environment]::GetEnvironmentVariable("Path","User")
    $PYTHON = Find-Python
    if (-not $PYTHON) { Write-Fail "安裝後仍找不到 Python，請重開 PowerShell 後重試。" }
}

$ver = & $PYTHON --version 2>&1
Write-Ok "使用 $ver（$PYTHON）"

# ── 2. 建立虛擬環境 ───────────────────────────────────────────────────────────
function New-Venv($name) {
    $path = Join-Path $BASE $name
    if (Test-Path $path) {
        # 確認 pip 可用；若損壞則刪掉重建
        $pyExe = Join-Path $path "Scripts\python.exe"
        & $pyExe -m pip --version 2>&1 | Out-Null
        if ($LASTEXITCODE -ne 0) {
            Write-Warn "$name 的 pip 損壞，刪除後重建..."
            Remove-Item $path -Recurse -Force
        } else {
            Write-Ok "$name 已存在，略過建立"
            return $path
        }
    }
    Write-Step "建立虛擬環境 $name ..."
    & $PYTHON -m venv $path
    if ($LASTEXITCODE -ne 0) { Write-Fail "建立 $name 失敗" }
    Write-Ok "$name 建立完成"
    return $path
}

$VENV_MINERU  = New-Venv ".venv-mineru"
$VENV_DOCLING = New-Venv ".venv-docling"

$PY_MINERU  = Join-Path $VENV_MINERU  "Scripts\python.exe"
$PY_DOCLING = Join-Path $VENV_DOCLING "Scripts\python.exe"

# ── 3. pip 安裝依賴 ───────────────────────────────────────────────────────────
Write-Step "安裝 MinerU 依賴（magic-pdf + CPU backend）..."
Write-Host "    這可能需要 5~15 分鐘，請耐心等候..." -ForegroundColor DarkGray
& $PY_MINERU -m pip install --upgrade pip --quiet
& $PY_MINERU -m pip install "mineru[core]" --quiet
if ($LASTEXITCODE -ne 0) { Write-Fail "MinerU 安裝失敗" }
Write-Ok "MinerU 安裝完成"

Write-Step "安裝 Docling 依賴..."
Write-Host "    這可能需要 5~10 分鐘，請耐心等候..." -ForegroundColor DarkGray
& $PY_DOCLING -m pip install --upgrade pip --quiet
& $PY_DOCLING -m pip install docling --quiet
if ($LASTEXITCODE -ne 0) { Write-Fail "Docling 安裝失敗" }
Write-Ok "Docling 安裝完成"

# ── 4. 下載 MinerU 模型 ───────────────────────────────────────────────────────
Write-Step "下載 MinerU AI 模型（約 1~2GB，首次必須，請確保網路暢通）..."
Write-Host "    模型會快取到 ~/.cache/magic-pdf/，之後不再重複下載。" -ForegroundColor DarkGray

$MINERU_MODELS = Join-Path $VENV_MINERU "Scripts\mineru-models-download.exe"
if (Test-Path $MINERU_MODELS) {
    & $MINERU_MODELS -s huggingface -m pipeline
    if ($LASTEXITCODE -ne 0) {
        Write-Warn "模型下載失敗（可能是網路問題）。稍後可手動執行："
        Write-Warn "  $MINERU_MODELS -s huggingface"
    } else {
        Write-Ok "MinerU 模型下載完成"
    }
} else {
    Write-Warn "找不到 mineru-models-download，模型將在首次執行時自動下載。"
}

# ── 5. 建立 run.bat 捷徑 ──────────────────────────────────────────────────────
Write-Step "建立執行捷徑..."

$RUN_MINERU = Join-Path $BASE "run_mineru.bat"
$mineruBat = @(
    '@echo off',
    'chcp 65001 >nul',
    'echo [pdftomd] MinerU: note\input\ -^> note\output\',
    '"%~dp0.venv-mineru\Scripts\python.exe" "%~dp0convert_mineru.py"',
    'echo.',
    'echo [DONE] 按任意鍵關閉...',
    'pause >nul'
)
$mineruBat | Set-Content $RUN_MINERU -Encoding utf8
Write-Ok "run_mineru.bat"

$RUN_DOCLING = Join-Path $BASE "run_docling.bat"
$doclingBat = @(
    '@echo off',
    'chcp 65001 >nul',
    'echo [pdftomd] Docling: dev\input\ -^> dev\output\',
    '"%~dp0.venv-docling\Scripts\python.exe" "%~dp0convert_docling.py"',
    'echo.',
    'echo [DONE] 按任意鍵關閉...',
    'pause >nul'
)
$doclingBat | Set-Content $RUN_DOCLING -Encoding utf8
Write-Ok "run_docling.bat"

# ── 完成 ──────────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "================================================================" -ForegroundColor Green
Write-Host "  安裝完成！" -ForegroundColor Green
Write-Host "----------------------------------------------------------------" -ForegroundColor Green
Write-Host "  使用方式："
Write-Host "    講義類 PDF → 放入 note\input\  → 雙擊 run_mineru.bat"
Write-Host "    技術類 PDF → 放入 dev\input\   → 雙擊 run_docling.bat"
Write-Host "  輸出位置："
Write-Host "    Markdown 在 note\output\ 或 dev\output\"
Write-Host "    圖片在各自的 output\images\"
Write-Host "================================================================" -ForegroundColor Green
