from app.domain.bookstore import BookStoreManagementSystem
from app.domain.catalog.book_database import BookDatabase
from app.persistence.database import init_db
from app.persistence.repositories import (
    AccountRepository,
    BookRepository,
    CartRepository,
    OrderRepository,
    ReviewRepository,
    UserRepository,
)


def build_store() -> BookStoreManagementSystem:
    init_db()
    BookDatabase.getInstance(BookRepository())
    return BookStoreManagementSystem(
        users=UserRepository(),
        accounts=AccountRepository(),
        carts=CartRepository(),
        orders=OrderRepository(),
        reviews=ReviewRepository(),
    )
