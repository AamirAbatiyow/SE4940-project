import csv
import re
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[2]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.paths import RAW_BOOKS, SEED_BOOKS

_BY_LAST_FIRST = re.compile(r"^By\s+([^,]+),\s+(.+)$", re.IGNORECASE)
_LEADING_BY = re.compile(r"^By\s+", re.IGNORECASE)


def normalize_author(raw: str) -> str:
    text = (raw or "").strip()
    match = _BY_LAST_FIRST.match(text)
    if match:
        last_name = match.group(1).strip()
        first_name = match.group(2).strip()
        return f"{first_name} {last_name}".strip()
    return _LEADING_BY.sub("", text, count=1).strip()


def parse_price(raw):
    text = (raw or "").strip().replace("$", "").replace(",", "")
    if not text:
        return None
    try:
        return Decimal(text).quantize(Decimal("0.01"))
    except InvalidOperation:
        return None


def make_isbn(sequence: int) -> str:
    return f"978{sequence:010d}"


def make_stock(index: int) -> int:
    return 5 + (index % 20)


def _field_limit() -> None:
    limit = sys.maxsize
    while limit > 0:
        try:
            csv.field_size_limit(limit)
            return
        except OverflowError:
            limit //= 10


def transform(source=RAW_BOOKS, destination=SEED_BOOKS) -> tuple[int, int]:
    _field_limit()
    destination.parent.mkdir(parents=True, exist_ok=True)
    kept = 0
    skipped = 0
    with source.open(newline="", encoding="utf-8-sig") as incoming, destination.open(
        "w", newline="", encoding="utf-8"
    ) as outgoing:
        reader = csv.DictReader(incoming)
        headers = set(reader.fieldnames or [])
        required = {"Title", "Authors", "Price Starting With ($)"}
        if not required.issubset(headers):
            raise SystemExit(f"Unexpected CSV headers: {reader.fieldnames}")
        writer = csv.writer(outgoing, lineterminator="\n")
        writer.writerow(["title", "author", "price", "isbn", "stock"])
        for row in reader:
            title = (row.get("Title") or "").strip()
            price = parse_price(row.get("Price Starting With ($)"))
            if not title or price is None:
                skipped += 1
                continue
            writer.writerow(
                [
                    title,
                    normalize_author(row.get("Authors") or ""),
                    format(price, "f"),
                    make_isbn(kept + 1),
                    make_stock(kept),
                ]
            )
            kept += 1
            if kept % 20000 == 0:
                print(f"Transformed {kept} books")
    return kept, skipped


def main() -> None:
    if not RAW_BOOKS.is_file():
        raise SystemExit(f"Missing source CSV: {RAW_BOOKS}")
    kept, skipped = transform()
    print(f"Wrote {kept} books to {SEED_BOOKS}")
    print(f"Skipped {skipped} rows missing a title or a price")


if __name__ == "__main__":
    main()
