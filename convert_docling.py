"""
程式/技術類 PDF / Word → Markdown（使用 Docling）

用途分類：🛠 程式類（乾淨數位文字、技術文件）走 Docling。
輸入：dev/input/*.pdf  或  dev/input/*.docx
輸出：dev/output/{stem}.md  + 圖片集中於 dev/output/images/
之後把 md + images 依 [[MinerU PDF轉換工作流]] 步驟丟進 Notes/Clippings/ 走 ingest。
"""

from pathlib import Path
from docling.document_converter import DocumentConverter, PdfFormatOption, WordFormatOption
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.datamodel.base_models import InputFormat
from docling_core.types.doc import ImageRefMode

# ── 路徑：一律相對於本腳本，避免寫死絕對路徑 ──
BASE = Path(__file__).resolve().parent
input_folder = BASE / "dev" / "input"
output_folder = BASE / "dev" / "output"
images_folder = output_folder / "images"   # 圖片集中一個資料夾

output_folder.mkdir(parents=True, exist_ok=True)
images_folder.mkdir(parents=True, exist_ok=True)
input_folder.mkdir(parents=True, exist_ok=True)

# ── Pipeline 選項：啟用圖片抽取（放大 2x 提升清晰度） ──
pdf_pipeline_options = PdfPipelineOptions()
pdf_pipeline_options.images_scale = 2.0
pdf_pipeline_options.generate_picture_images = True
pdf_pipeline_options.generate_table_images = True

converter = DocumentConverter(
    format_options={
        InputFormat.PDF: PdfFormatOption(pipeline_options=pdf_pipeline_options),
        # DOCX 走 SimplePipeline，不需額外 pipeline_options
        InputFormat.DOCX: WordFormatOption(),
    }
)

import subprocess

# ── 舊版 Word (.doc) 轉換為新版 (.docx) ──
# 透過 PowerShell 呼叫本地安裝的 MS Word COM 物件進行轉檔，不需額外安裝 pywin32 等 Python 套件。
def _convert_doc_to_docx(doc_path: Path) -> Path:
    docx_path = doc_path.with_suffix(".docx")
    if docx_path.exists():
        return docx_path
    
    ps_cmd = f"""
    $word = New-Object -ComObject Word.Application
    $word.Visible = $false
    $doc = $word.Documents.Open('{doc_path.resolve()}')
    $doc.SaveAs2('{docx_path.resolve()}', 16)
    $doc.Close()
    $word.Quit()
    """
    try:
        print(f"[DOC] 正在將舊版 Word 檔轉換為 docx: {doc_path.name}")
        subprocess.run(["powershell", "-Command", ps_cmd], check=True, capture_output=True)
        return docx_path
    except Exception as e:
        print(f"[WARN] 無法自動將 {doc_path.name} 轉換為 docx，請嘗試手動轉存。錯誤: {e}")
        return doc_path

# ── 同時接受 PDF, DOCX 與舊版 DOC ──
SUPPORTED_EXTS = {".pdf", ".docx", ".doc"}
pdfs = sorted(p for p in input_folder.iterdir() if p.suffix.lower() in SUPPORTED_EXTS)
if not pdfs:
    print(f"[INFO] {input_folder} 內沒有 PDF/Word 檔案。")

for file in pdfs:
    temp_docx = None
    # 核心邏輯：如果是舊版 .doc，呼叫 PowerShell 轉為 .docx 後再交給 Docling 處理
    if file.suffix.lower() == ".doc":
        actual_file = _convert_doc_to_docx(file)
        if actual_file != file:
            temp_docx = actual_file
    else:
        actual_file = file

    if actual_file.suffix.lower() != ".docx" and actual_file.suffix.lower() != ".pdf":
        continue

    print(f"處理中: {file.name}")
    try:
        result = converter.convert(str(actual_file))

        md_path = output_folder / f"{file.stem}.md"
        # 關鍵修正：save_as_markdown 的第一參數是 md 檔路徑，圖片走 artifacts_dir。
        # REFERENCED 模式會把圖片寫進 images_folder，並在 md 內以相對路徑引用
        # （md 在 output/，圖片在 output/images/ → 自動變成 images/xxx.png），
        # 不需要再手動 replace 路徑。
        result.document.save_as_markdown(
            md_path,
            artifacts_dir=images_folder,
            image_mode=ImageRefMode.REFERENCED,
        )
        print(f"[OK] Markdown: {md_path}")

    except Exception as e:
        # 不用特殊 Unicode 符號，避免 Windows CP950 主控台編碼報錯
        print(f"[FAIL] 轉換 {file.name} 失敗，錯誤原因: {e}")
    finally:
        # 轉檔完成後，自動刪除臨時產生的 docx 檔案，保持資料夾乾淨
        if temp_docx and temp_docx.exists():
            try:
                temp_docx.unlink()
            except Exception:
                pass

imgs = list(images_folder.glob("*.png")) + list(images_folder.glob("*.jpg"))
print(f"[DONE] 圖片共 {len(imgs)} 張 -> {images_folder}")
