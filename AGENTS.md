# AGENTS.md

## High-Signal Facts
- Python repo, tested with Python 3.11+.
- Source code lives under `src/`; run commands from the repo root so `src.*` imports resolve.
- There is no `pyproject.toml` or repo test config; `requirements.txt` is the install source of truth.
- Runtime config comes from `.env` via `src/config.py`; `.env.example` is the template.
- Importing `src.database.session` creates the local `db/` directory if needed.

## Commands
- Install deps: `pip install -r requirements.txt`
- Run all tests: `python -m pytest tests/ -v`
- Run one test file: `python -m pytest tests/test_ds_client.py -v`
- Run one test case: `python -m pytest tests/test_ds_client.py -k test_chat -v`

## Repo Shape
- `src/preprocessor/file_loader.py` supports only `.txt`, `.md`, `.docx`, and `.epub`.
- `src/preprocessor/chapter_splitter.py` treats Chinese chapter markers, `Chapter X`, and Markdown headings as chapter boundaries; otherwise it returns the whole text as one chapter.
- `src/extractor/ds_client.py` wraps `OpenAI` and expects DeepSeek settings from `src/config.py`.
- `src/extractor/character_extractor.py` is a thin wrapper around `DeepSeekClient.extract_json()`.
- `src/database/models.py` defines six SQLite tables; `src/database/session.py` owns engine/session setup and `init_db()`.

## Testing Notes
- Several tests mock `OpenAI`; do not swap out the client interface without updating those tests.
- `tests/test_file_loader.py` creates temporary `.docx` and `.epub` files, so document-processing deps must stay installed.
- If you change file-loading or chapter-splitting behavior, update the focused tests first; the repo leans on those as the executable spec.

## Working Rules
- Prefer the smallest change that matches the existing patterns in `src/`.
- Avoid checking in generated artifacts such as `db/`, `data/uploads/`, `__pycache__/`, or `.pytest_cache/`.
