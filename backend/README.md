# BookNest backend

From the repository root:

```
python -m venv .venv
.venv\Scripts\activate
pip install -r backend/requirements.txt
python backend/app/seed/transform_books.py
python backend/app/seed/seed_database.py
uvicorn app.main:app --app-dir backend --port 8000
```

On macOS or Linux, activate the environment with `source .venv/bin/activate`.

Then open http://127.0.0.1:8000/ . Re-running the seed replaces the catalog and clears orders, reviews, and cart items. The demo logins stay.

- Buyer: buyer@booknest.test / password123
- Staff: staff@booknest.test / password123
