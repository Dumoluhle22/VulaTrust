# Setup

VulaTrust needs **Python 3.10 or newer**. Check with `python --version`.

## Windows (PowerShell)

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pytest
python -m app.seed
python -m uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000.

If PowerShell refuses to run the activate script, run `Set-ExecutionPolicy -Scope Process Bypass` first. It lasts only for that window.

## macOS and Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pytest
python -m app.seed
python -m uvicorn app.main:app --reload
```

## What each command does

| Command | Purpose |
|---|---|
| `python -m pytest` | Runs all tests. They use a temporary database and never touch your real one. |
| `python -m app.seed` | Loads the 8 synthetic sample vendors. Safe to run twice. |
| `python -m uvicorn app.main:app --reload` | Starts the app. `--reload` restarts it when you change code. |

The database is a file called `vulatrust.db` in the folder you start the app from. It is created automatically and is ignored by Git. To use a different file, set `DATABASE_URL`, for example `DATABASE_URL=sqlite:///./demo.db`.

## Start again from nothing

Stop the server (Ctrl+C), delete `vulatrust.db`, then start the app again. On Windows a running server keeps the file locked, so stop it first. If it is still locked, run `Get-Process python* | Stop-Process`.

## Coverage (optional)

```
python -m pip install -r requirements-dev.txt
python -m pytest --cov=app --cov-report=term-missing
```

## Safe use

The app has no login. **Run it on your own computer only**, which is what the commands above do (it listens on 127.0.0.1). Do not start it with `--host 0.0.0.0` or put it on the internet. See `docs/security-notes.md`.

## Troubleshooting

| Problem | Fix |
|---|---|
| `No module named ...` | The virtual environment is not active, or packages are not installed. Activate it and run `python -m pip install -r requirements.txt`. |
| `pytest` is not recognised | Use `python -m pytest`. |
| `Remove-Item` says the database is in use | Stop the server first (see above). |
| Pages show old data after code changes | Make sure the server was restarted, or started with `--reload`. |
| A form says it "could not be verified" | Reload the page and submit again. The security token comes from the page and cookie. |
