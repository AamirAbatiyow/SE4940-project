from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.exc import IntegrityError

from app.domain.errors import CheckoutError, ConflictError
from app.domain.money import money
from app.persistence.database import session_scope
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


def _like(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def _user_dict(row: UserRow) -> dict:
    return {
        "user_id": row.user_id,
        "email": row.email,
        "password_hash": row.password_hash,
        "role": row.role,
        "name": row.name,
        "shipping_address": row.shipping_address,
        "job_title": row.job_title,
    }


def _book_dict(row: BookRow) -> dict:
    return {
        "book_id": row.book_id,
        "isbn": row.isbn,
        "title": row.title,
        "author": row.author,
        "price": money(row.price),
        "stock": row.stock,
    }


def _order_dict(order: OrderRow, items, titles, payment) -> dict:
    payload = {
        "order_id": order.order_id,
        "user_id": order.user_id,
        "status": order.status,
        "total_amount": money(order.total_amount),
        "created_at": order.created_at,
        "items": [
            {
                "book_id": item.book_id,
                "title": titles.get(item.book_id, ""),
                "quantity": item.quantity,
                "unit_price": money(item.unit_price),
            }
            for item in items
        ],
        "payment": None,
    }
    if payment is not None:
        payload["payment"] = {
            "payment_id": payment.payment_id,
            "method": payment.method,
            "status": payment.status,
            "amount": money(payment.amount),
            "created_at": payment.created_at,
        }
    return payload


def _pack_orders(session, orders) -> list[dict]:
    if not orders:
        return []
    order_ids = [order.order_id for order in orders]
    item_rows = session.scalars(
        select(OrderItemRow).where(OrderItemRow.order_id.in_(order_ids))
    ).all()
    book_ids = {item.book_id for item in item_rows}
    titles = {}
    if book_ids:
        books = session.scalars(select(BookRow).where(BookRow.book_id.in_(book_ids))).all()
        titles = {book.book_id: book.title for book in books}
    payments = session.scalars(
        select(PaymentRow)
        .where(PaymentRow.order_id.in_(order_ids))
        .order_by(PaymentRow.payment_id)
    ).all()
    latest_payment = {}
    for payment in payments:
        latest_payment[payment.order_id] = payment
    items_by_order = {}
    for item in item_rows:
        items_by_order.setdefault(item.order_id, []).append(item)
    return [
        _order_dict(
            order,
            items_by_order.get(order.order_id, []),
            titles,
            latest_payment.get(order.order_id),
        )
        for order in orders
    ]


class UserRepository:
    def get_by_email(self, email: str):
        with session_scope() as session:
            row = session.scalar(select(UserRow).where(UserRow.email == email))
            return None if row is None else _user_dict(row)

    def get_by_id(self, user_id: int):
        with session_scope() as session:
            row = session.get(UserRow, user_id)
            return None if row is None else _user_dict(row)

    def register(self, fields: dict, account_status: str) -> dict:
        with session_scope() as session:
            existing = session.scalar(select(UserRow.user_id).where(UserRow.email == fields["email"]))
            if existing is not None:
                raise ConflictError("An account with that email already exists")
            user = UserRow(**fields)
            session.add(user)
            try:
                session.flush()
            except IntegrityError as exc:
                raise ConflictError("An account with that email already exists") from exc
            account = AccountRow(user_id=user.user_id, status=account_status)
            cart = CartRow(user_id=user.user_id)
            session.add(account)
            session.add(cart)
            session.flush()
            return {
                "user_id": user.user_id,
                "account_id": account.account_id,
                "cart_id": cart.cart_id,
            }


class AccountRepository:
    def get_by_user(self, user_id: int):
        with session_scope() as session:
            row = session.scalar(select(AccountRow).where(AccountRow.user_id == user_id))
            if row is None:
                return None
            return {
                "account_id": row.account_id,
                "user_id": row.user_id,
                "status": row.status,
            }


class BookRepository:
    def get(self, book_id: int):
        with session_scope() as session:
            row = session.get(BookRow, book_id)
            return None if row is None else _book_dict(row)

    def search_title(self, title: str):
        with session_scope() as session:
            row = session.scalar(
                select(BookRow)
                .where(func.lower(BookRow.title) == title.strip().lower())
                .order_by(BookRow.book_id)
                .limit(1)
            )
            return None if row is None else _book_dict(row)

    def list_books(self, query: str, page: int, page_size: int):
        with session_scope() as session:
            cleaned = (query or "").strip()
            criterion = None
            if cleaned:
                pattern = _like(cleaned.lower())
                criterion = or_(
                    func.lower(BookRow.title).like(pattern, escape="\\"),
                    func.lower(BookRow.author).like(pattern, escape="\\"),
                )
            count_stmt = select(func.count()).select_from(BookRow)
            list_stmt = select(BookRow).order_by(BookRow.book_id)
            if criterion is not None:
                count_stmt = count_stmt.where(criterion)
                list_stmt = list_stmt.where(criterion)
            total = session.scalar(count_stmt)
            rows = session.scalars(
                list_stmt.offset((page - 1) * page_size).limit(page_size)
            ).all()
            return [_book_dict(row) for row in rows], int(total or 0)

    def max_generated_isbn(self):
        with session_scope() as session:
            pattern = "978" + ("[0-9]" * 10)
            return session.scalar(
                select(func.max(BookRow.isbn)).where(BookRow.isbn.op("GLOB")(pattern))
            )

    def insert(self, fields: dict) -> dict:
        with session_scope() as session:
            row = BookRow(
                isbn=fields["isbn"],
                title=fields["title"],
                author=fields["author"],
                price=fields["price"],
                stock=fields["stock"],
            )
            session.add(row)
            try:
                session.flush()
            except IntegrityError as exc:
                raise ValueError("ISBN already exists") from exc
            return _book_dict(row)

    def update(self, book_id: int, fields: dict):
        with session_scope() as session:
            row = session.get(BookRow, book_id)
            if row is None:
                return None
            row.isbn = fields["isbn"]
            row.title = fields["title"]
            row.author = fields["author"]
            row.price = fields["price"]
            row.stock = fields["stock"]
            try:
                session.flush()
            except IntegrityError as exc:
                raise ValueError("ISBN already exists") from exc
            return _book_dict(row)


class CartRepository:
    def get_by_user(self, user_id: int):
        with session_scope() as session:
            cart = session.scalar(select(CartRow).where(CartRow.user_id == user_id))
            if cart is None:
                return None
            items = session.scalars(
                select(CartItemRow).where(CartItemRow.cart_id == cart.cart_id)
            ).all()
            book_ids = [item.book_id for item in items]
            books = {}
            if book_ids:
                for book in session.scalars(select(BookRow).where(BookRow.book_id.in_(book_ids))).all():
                    books[book.book_id] = book
            payload = []
            for item in items:
                book = books.get(item.book_id)
                if book is None:
                    continue
                payload.append(
                    {
                        "book_id": item.book_id,
                        "title": book.title,
                        "author": book.author,
                        "quantity": item.quantity,
                        "unit_price": money(book.price),
                    }
                )
            return {"cart_id": cart.cart_id, "items": payload}

    def create(self, user_id: int) -> int:
        with session_scope() as session:
            cart = CartRow(user_id=user_id)
            session.add(cart)
            session.flush()
            return cart.cart_id

    def save_line(self, cart_id: int, book_id: int, quantity: int) -> None:
        with session_scope() as session:
            line = session.get(CartItemRow, (cart_id, book_id))
            if line is None:
                session.add(CartItemRow(cart_id=cart_id, book_id=book_id, quantity=quantity))
            else:
                line.quantity = quantity

    def delete_line(self, cart_id: int, book_id: int) -> bool:
        with session_scope() as session:
            line = session.get(CartItemRow, (cart_id, book_id))
            if line is None:
                return False
            session.delete(line)
            return True


class OrderRepository:
    def place(
        self,
        user_id,
        cart_id,
        status,
        total_amount,
        created_at,
        items,
        payment_method,
        payment_status,
        payment_amount,
    ) -> dict:
        with session_scope() as session:
            for item in items:
                updated = session.execute(
                    update(BookRow)
                    .where(
                        BookRow.book_id == item["book_id"],
                        BookRow.stock >= item["quantity"],
                    )
                    .values(stock=BookRow.stock - item["quantity"])
                    .returning(BookRow.book_id)
                ).first()
                if updated is None:
                    raise CheckoutError("Not enough stock")
            order = OrderRow(
                user_id=user_id,
                status=status,
                total_amount=total_amount,
                created_at=created_at,
            )
            session.add(order)
            session.flush()
            for item in items:
                session.add(
                    OrderItemRow(
                        order_id=order.order_id,
                        book_id=item["book_id"],
                        quantity=item["quantity"],
                        unit_price=item["unit_price"],
                    )
                )
            session.add(
                PaymentRow(
                    order_id=order.order_id,
                    method=payment_method,
                    status=payment_status,
                    amount=payment_amount,
                    created_at=created_at,
                )
            )
            session.flush()
            session.execute(delete(CartItemRow).where(CartItemRow.cart_id == cart_id))
            packed = _pack_orders(session, [order])
            return packed[0]

    def get(self, order_id: int):
        with session_scope() as session:
            order = session.get(OrderRow, order_id)
            if order is None:
                return None
            return _pack_orders(session, [order])[0]

    def list_for_user(self, user_id: int):
        with session_scope() as session:
            orders = session.scalars(
                select(OrderRow)
                .where(OrderRow.user_id == user_id)
                .order_by(OrderRow.order_id.desc())
            ).all()
            return _pack_orders(session, orders)

    def list_all(self):
        with session_scope() as session:
            orders = session.scalars(select(OrderRow).order_by(OrderRow.order_id.desc())).all()
            return _pack_orders(session, orders)

    def update_status(self, order_id: int, status: str) -> None:
        with session_scope() as session:
            order = session.get(OrderRow, order_id)
            if order is None:
                return
            order.status = status


class ReviewRepository:
    def list_for_book(self, book_id: int):
        with session_scope() as session:
            rows = session.execute(
                select(ReviewRow, UserRow.name)
                .join(UserRow, UserRow.user_id == ReviewRow.user_id)
                .where(ReviewRow.book_id == book_id)
                .order_by(ReviewRow.review_id)
            ).all()
            return [_review_dict(review, name) for review, name in rows]

    def get(self, review_id: int):
        with session_scope() as session:
            row = session.get(ReviewRow, review_id)
            if row is None:
                return None
            name = session.scalar(select(UserRow.name).where(UserRow.user_id == row.user_id))
            return _review_dict(row, name)

    def insert(self, user_id: int, book_id: int, rating: int, comment: str) -> dict:
        with session_scope() as session:
            row = ReviewRow(user_id=user_id, book_id=book_id, rating=rating, comment=comment)
            session.add(row)
            session.flush()
            name = session.scalar(select(UserRow.name).where(UserRow.user_id == user_id))
            return _review_dict(row, name)

    def update(self, review_id: int, rating: int, comment: str) -> None:
        with session_scope() as session:
            row = session.get(ReviewRow, review_id)
            if row is None:
                return
            row.rating = rating
            row.comment = comment


def _review_dict(review: ReviewRow, user_name) -> dict:
    return {
        "review_id": review.review_id,
        "user_id": review.user_id,
        "book_id": review.book_id,
        "rating": review.rating,
        "comment": review.comment,
        "user_name": user_name,
    }
