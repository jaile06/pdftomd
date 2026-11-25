---
name: pdftomd
description: 'Use when converting a PDF or Word file (.pdf/.docx/.doc) to Markdown for vault ingest. Routes handout/scanned/diagram-heavy documents through MinerU (note/input → note/output) and clean digital technical documents through Docling (dev/input → dev/output). Trigger phrases: "轉檔", "PDF 轉 md", "convert this PDF to markdown", "把這份講義轉成 markdown".'
---

# pdftomd

Two converters, two content types. Picking the wrong one wastes a full model run.

## 1. Route by content type

| 內容特徵 | 用哪個 | 放入 | 產出 |
|---|---|---|---|
| 講義、教科書、掃描檔、圖表/公式密集 | **MinerU** (`convert_mineru.py`) | `note/input/` | `note/output/{stem}.md` + `note/output/images/` |
| 乾淨數位文字、程式書、技術手冊 | **Docling** (`convert_docling.py`) | `dev/input/` | `dev/output/{stem}.md` + `dev/output/images/` |

Scanned or diagram-heavy content run through Docling comes out with weak table/OCR fidelity — route it to MinerU instead, even if it's technically a "technical document."

## 2. Always run through the dedicated venv

Each converter has its own venv (`.venv-mineru`, `.venv-docling`) with incompatible dependency sets. Never invoke with system Python — use the venv's python directly, or the `run_mineru.bat` / `run_docling.bat` wrappers install creates:

```
.venv-mineru\Scripts\python.exe convert_mineru.py
.venv-docling\Scripts\python.exe convert_docling.py
```

System `python convert_mineru.py` will fail with `ModuleNotFoundError` — this is the shortcut to forbid.

## 3. Known gotchas

- **Backend is auto-picked** (`_pick_backend()` in convert_mineru.py): CUDA torch → `hybrid-engine`, otherwise `pipeline`. Don't hardcode either — this repo is distributed to CPU-only machines, so the CPU route must keep working.
- **MinerU's output-location logic is unverified** (`_locate_outputs()` — see comment in convert_mineru.py). If a run reports `[WARN] 找不到 {stem} 的 md`, check `note/output/_mineru_raw/{stem}/` structure directly before assuming the conversion failed.
- **`.doc` files** convert via a Word COM call (`_convert_doc_to_docx`) — this needs MS Word installed locally. If Word isn't present it warns and passes the original `.doc` through unconverted (not a hard failure, but the downstream converter will then reject it).
- **Raw MinerU debug output is deleted after flattening** (`KEEP_RAW = False`, ~245MB/doc). Don't expect `_mineru_raw/` to persist between runs.
- **Python must be 3.10–3.12** — install.ps1 accepts `>=3.10, <3.13`; a new install defaults to 3.11. A pre-existing venv on an unsupported version gets auto-rebuilt by install.ps1, not silently used.
- **install.ps1 checks GitHub but never overwrites silently.** It lists differing files and asks (default No); old files are kept as `.bak`. Never answer Y on the user's behalf — it would replace unpushed local edits with remote code. No network or non-interactive → it warns and continues with the local copy.

## 4. Completion criterion

Conversion is done when the target `.md` file exists in `note/output/` or `dev/output/` and referenced images are present in that folder's `images/` subfolder. Console prints `[DONE]` on success, `[FAIL] 轉換 {name} 失敗` per-file on failure — a partial batch (some files OK, one FAIL) is normal; only the failed file needs re-running, not the whole batch.

## 5. After conversion

Per the header comments in both scripts, the output `.md` + `images/` is meant to go through the vault's ingest flow next (`[[MinerU PDF轉換工作流]]`) — this skill only produces the Markdown, it does not ingest it.
