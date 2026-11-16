from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class UserRow(Base):
    __tablename__ = "USERS"

    user_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    shipping_address: Mapped[str | None] = mapped_column(String, nullable=True)
    job_title: Mapped[str | None] = mapped_column(String, nullable=True)


class AccountRow(Base):
    __tablename__ = "ACCOUNTS"

    account_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("USERS.user_id"), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)


class BookRow(Base):
    __tablename__ = "BOOKS"
    __table_args__ = (Index("ix_books_title", "title"),)

    book_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    author: Mapped[str] = mapped_column(String, nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    isbn: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    stock: Mapped[int] = mapped_column(Integer, nullable=False)


class CartRow(Base):
    __tablename__ = "CARTS"

    cart_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("USERS.user_id"), unique=True, nullable=False)


class CartItemRow(Base):
    __tablename__ = "CART_ITEMS"

    cart_id: Mapped[int] = mapped_column(ForeignKey("CARTS.cart_id"), primary_key=True)
    book_id: Mapped[int] = mapped_column(ForeignKey("BOOKS.book_id"), primary_key=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)


class OrderRow(Base):
    __tablename__ = "ORDERS"
    __table_args__ = (Index("ix_orders_user_id", "user_id"),)

    order_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("USERS.user_id"), nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)


class OrderItemRow(Base):
    __tablename__ = "ORDER_ITEMS"

    order_id: Mapped[int] = mapped_column(ForeignKey("ORDERS.order_id"), primary_key=True)
    book_id: Mapped[int] = mapped_column(ForeignKey("BOOKS.book_id"), primary_key=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)


class PaymentRow(Base):
    __tablename__ = "PAYMENTS"

    payment_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("ORDERS.order_id"), nullable=False)
    method: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class ReviewRow(Base):
    __tablename__ = "REVIEWS"
    __table_args__ = (Index("ix_reviews_book_id", "book_id"),)

    review_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("USERS.user_id"), nullable=False)
    book_id: Mapped[int] = mapped_column(ForeignKey("BOOKS.book_id"), nullable=False)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    comment: Mapped[str] = mapped_column(Text, nullable=False)
