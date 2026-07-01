"""
講義類 PDF → Markdown（使用 MinerU）

用途分類：📚 講義類（教科書、備課、掃描檔、圖表/公式密集）走 MinerU。
輸入：note/input/*.pdf
輸出：note/output/{stem}.md  + 圖片集中於 note/output/images/
之後把 md + images 依 [[MinerU PDF轉換工作流]] 步驟丟進 Notes/Clippings/ 走 ingest。

⚠️ 待驗證（安裝 MinerU 後）：
  1. 確切 CLI 旗標：`mineru --help`（3.4 的 -b backend 值名、預設是否為 hybrid/VLM）。
  2. MinerU 實際輸出目錄結構（pipeline 後端多為 <out>/<stem>/auto/），
     下方 _locate_outputs() 依此假設；跑一次後對照真實結構再修。
本檔用 subprocess 呼叫 mineru CLI，不 import，避免 venv 相依問題。
"""

import os
import subprocess
import sys
import shutil
from pathlib import Path

# Windows 無 symlink 權限時，huggingface_hub 會自動改用複製；關閉其警告噪音
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

BASE = Path(__file__).resolve().parent
input_folder = BASE / "note" / "input"
output_folder = BASE / "note" / "output"
images_folder = output_folder / "images"
raw_dir = output_folder / "_mineru_raw"   # MinerU 原始輸出，處理後可刪

output_folder.mkdir(parents=True, exist_ok=True)
images_folder.mkdir(parents=True, exist_ok=True)

# CPU 用 pipeline；有 GPU 想更高保真再換 vlm-engine / hybrid-engine
# （3.4 預設為 hybrid-engine，需 GPU/VLM，CPU 必須顯式 pipeline）
BACKEND = "pipeline"
IMG_EXTS = (".png", ".jpg", ".jpeg")
# 攤平成功後是否保留 MinerU 原始輸出（含每檔 ~245MB 的 _layout/_origin/_span.pdf 除錯檔）
KEEP_RAW = False


def _find_mineru() -> str:
    """找 mineru 執行檔：先看 PATH，再看本專案 .venv-mineru\\Scripts。"""
    exe = shutil.which("mineru")
    if exe:
        return exe
    for cand in (
        BASE / ".venv-mineru" / "Scripts" / "mineru.exe",   # Windows
        BASE / ".venv-mineru" / "bin" / "mineru",           # POSIX
    ):
        if cand.exists():
            return str(cand)
    return ""


MINERU = _find_mineru()


def run_mineru(pdf: Path):
    raw_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        MINERU,
        "-p", str(pdf),
        "-o", str(raw_dir),
        "-b", BACKEND,
        "-m", "auto",   # auto 自動判斷數位/掃描；掃描檔可改 ocr
    ]
    print("執行:", " ".join(cmd))
    subprocess.run(cmd, check=True)


def _locate_outputs(stem: str):
    """在 MinerU 原始輸出中找該檔的 md 與 images 夾（結構待實跑校正）。"""
    candidates = list(raw_dir.glob(f"{stem}/**/{stem}.md")) + \
        list(raw_dir.glob(f"{stem}/**/*.md"))
    md = candidates[0] if candidates else None
    imgdirs = list(raw_dir.glob(f"{stem}/**/images"))
    imgdir = imgdirs[0] if imgdirs else None
    return md, imgdir


def flatten(stem: str):
    """把 MinerU 輸出攤平成 note/output/{stem}.md + 集中 images/。

    MinerU 的圖檔以內容 hash 命名（跨 PDF 不會撞名，撞到即同一張圖），
    md 內引用格式為 `images/{hash}.jpg`；直接複製圖片、md 原樣搬出即可，
    不需前綴、不需改寫路徑（也避免中文/括號檔名破壞 Markdown 連結）。
    """
    md, imgdir = _locate_outputs(stem)
    if not md:
        print(f"[WARN] 找不到 {stem} 的 md，請檢查 {raw_dir} 實際結構")
        return

    if imgdir and imgdir.exists():
        for img in imgdir.iterdir():
            if img.suffix.lower() in IMG_EXTS:
                shutil.copy2(img, images_folder / img.name)

    shutil.copy2(md, output_folder / f"{stem}.md")
    print(f"[OK] {stem}.md + 圖片 -> {output_folder}")

    # 攤平完成後清掉該檔的原始輸出（省下巨大的除錯 PDF）
    if not KEEP_RAW:
        doc_raw = raw_dir / stem
        if doc_raw.exists():
            shutil.rmtree(doc_raw, ignore_errors=True)


def main():
    if not MINERU:
        sys.exit("[FAIL] 找不到 mineru 執行檔。先建 .venv-mineru 並 pip install 'mineru[core]'。")

    pdfs = sorted(p for p in input_folder.iterdir() if p.suffix.lower() == ".pdf")
    if not pdfs:
        print(f"[INFO] {input_folder} 內沒有 PDF。")
        return

    for pdf in pdfs:
        print(f"處理中: {pdf.name}")
        try:
            run_mineru(pdf)
            flatten(pdf.stem)
        except subprocess.CalledProcessError as e:
            print(f"[FAIL] MinerU 轉換 {pdf.name} 失敗: {e}")

    print(f"[DONE] 原始輸出在 {raw_dir}（確認無誤後可刪）")


if __name__ == "__main__":
    main()
