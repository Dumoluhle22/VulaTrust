# Run and test (paste into your README)

## Requirements
Python 3.10 or newer.

## Set up
```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Run
```bash
uvicorn app.main:app --reload
```
Open http://127.0.0.1:8000. The SQLite database (`vulatrust.db`) is created automatically on first run and is ignored by Git.
Use `DATABASE_URL` to point somewhere else, for example `DATABASE_URL=sqlite:///./demo.db`.

## Test
```bash
pytest
```
Tests use a temporary database and never touch `vulatrust.db`.

## Project layout
```
app/
  main.py        FastAPI app and home page
  database.py    engine, session, Base
  models.py      Vendor, Application, ImportBatch (issue 5)
  templates/     Jinja2 pages
tests/           pytest tests
sample_data/     synthetic CSVs (issue 4)
docs/            research notes and write-ups
```
