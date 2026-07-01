"""
程式/技術類 PDF → Markdown（使用 Docling）

用途分類：🛠 程式類（乾淨數位文字、技術文件）走 Docling。
輸入：dev/input/*.pdf
輸出：dev/output/{stem}.md  + 圖片集中於 dev/output/images/
之後把 md + images 依 [[MinerU PDF轉換工作流]] 步驟丟進 Notes/Clippings/ 走 ingest。
"""

from pathlib import Path
from docling.document_converter import DocumentConverter, PdfFormatOption
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

# ── Pipeline 選項：啟用圖片抽取（放大 2x 提升清晰度） ──
pdf_pipeline_options = PdfPipelineOptions()
pdf_pipeline_options.images_scale = 2.0
pdf_pipeline_options.generate_picture_images = True
pdf_pipeline_options.generate_table_images = True

converter = DocumentConverter(
    format_options={
        InputFormat.PDF: PdfFormatOption(pipeline_options=pdf_pipeline_options)
    }
)

pdfs = sorted(p for p in input_folder.iterdir() if p.suffix.lower() == ".pdf")
if not pdfs:
    print(f"[INFO] {input_folder} 內沒有 PDF，把程式/技術類 PDF 放進去再執行。")

for file in pdfs:
    print(f"處理中: {file.name}")
    try:
        result = converter.convert(str(file))

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

imgs = list(images_folder.glob("*.png")) + list(images_folder.glob("*.jpg"))
print(f"[DONE] 圖片共 {len(imgs)} 張 -> {images_folder}")
