from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
DB_PATH = DATA / "bookstore.db"
RAW_BOOKS = DATA / "raw-books" / "BooksDatasetClean.csv"
SEED_BOOKS = DATA / "seed" / "books.csv"
FRONTEND = ROOT / "frontend"
