# Database and cache FastAPI checkpoint

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export SECRET_KEY="replace-with-a-long-random-value"
uvicorn app.main:app --reload
```

The API documentation is available at http://127.0.0.1:8000/docs.

Run the security test with:

```bash
pytest
```

The service persists to `app.db` by default. Set `DATABASE_URL` to use another
SQLAlchemy database URL.
