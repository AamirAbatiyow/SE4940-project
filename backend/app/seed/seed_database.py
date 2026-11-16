import csv
import sys
from decimal import Decimal
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[2]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from sqlalchemy import delete, insert, select

from app.domain.user.account import Account
from app.domain.user.passwords import hash_password
from app.domain.user.user_factory import UserFactory
from app.paths import DB_PATH, SEED_BOOKS
from app.persistence.database import SessionLocal, engine, init_db
from app.persistence.tables import (
    AccountRow,
    BookRow,
    CartItemRow,
    CartRow,
    OrderItemRow,
    OrderRow,
    PaymentRow,
    ReviewRow,
    UserRow,
)

BATCH = 5000

DEMOS = (
    {
        "email": "buyer@booknest.test",
        "password": "password123",
        "name": "Demo Buyer",
        "role": "buyer",
        "shipping_address": "100 Campus Drive",
        "job_title": None,
    },
    {
        "email": "staff@booknest.test",
        "password": "password123",
        "name": "Demo Staff",
        "role": "staff",
        "shipping_address": None,
        "job_title": "Catalog Manager",
    },
)


def clear_catalog(session) -> None:
    session.execute(delete(PaymentRow))
    session.execute(delete(OrderItemRow))
    session.execute(delete(ReviewRow))
    session.execute(delete(CartItemRow))
    session.execute(delete(OrderRow))
    session.execute(delete(BookRow))


def load_books(session) -> int:
    count = 0
    batch = []
    with SEED_BOOKS.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            batch.append(
                {
                    "title": row["title"],
                    "author": row["author"],
                    "price": Decimal(row["price"]),
                    "isbn": row["isbn"],
                    "stock": int(row["stock"]),
                }
            )
            if len(batch) >= BATCH:
                session.execute(insert(BookRow), batch)
                session.commit()
                count += len(batch)
                batch = []
                print(f"Inserted {count} books")
        if batch:
            session.execute(insert(BookRow), batch)
            session.commit()
            count += len(batch)
    return count


def upsert_demos(session) -> None:
    factory = UserFactory()
    for demo in DEMOS:
        user = factory.createUser(
            demo["role"],
            name=demo["name"],
            email=demo["email"],
            passwordHash=hash_password(demo["password"]),
            shippingAddress=demo["shipping_address"],
            jobTitle=demo["job_title"],
        )
        row = session.scalar(select(UserRow).where(UserRow.email == user.email))
        if row is None:
            row = UserRow(
                email=user.email,
                password_hash=user.passwordHash,
                role=user.role,
                name=user.name,
                shipping_address=user.shippingAddress,
                job_title=user.jobTitle,
            )
            session.add(row)
            session.flush()
        else:
            row.email = user.email
            row.password_hash = user.passwordHash
            row.role = user.role
            row.name = user.name
            row.shipping_address = user.shippingAddress
            row.job_title = user.jobTitle

        account = Account(accountID=None, status="inactive", userID=row.user_id)
        account.activate()
        account_row = session.scalar(select(AccountRow).where(AccountRow.user_id == row.user_id))
        if account_row is None:
            session.add(AccountRow(user_id=row.user_id, status=account.status))
        else:
            account_row.status = account.status

        cart = session.scalar(select(CartRow).where(CartRow.user_id == row.user_id))
        if cart is None:
            session.add(CartRow(user_id=row.user_id))


def main() -> None:
    if not SEED_BOOKS.is_file():
        raise SystemExit("Missing data/seed/books.csv. Run transform_books.py first.")
    init_db()
    session = SessionLocal()
    try:
        clear_catalog(session)
        session.commit()
        count = load_books(session)
        upsert_demos(session)
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
        engine.dispose()
    print(f"Loaded {count} books into {DB_PATH}")
    print("Demo buyer: buyer@booknest.test / password123")
    print("Demo staff: staff@booknest.test / password123")


if __name__ == "__main__":
    main()
