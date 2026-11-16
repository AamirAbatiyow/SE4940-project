from app.domain.catalog.book import Book


class BookDatabase:
    _instance = None
    _creating = False

    def __init__(self, book_repository):
        if not BookDatabase._creating:
            raise RuntimeError("Use BookDatabase.getInstance()")
        self._books = book_repository

    # BookNest uses one shared catalog for search, staff edits, and checkout.
    # getInstance returns that same object for the whole process. SQLite,
    # through the book repository, is only the storage behind the catalog.
    @classmethod
    def getInstance(cls, book_repository=None):
        if cls._instance is None:
            if book_repository is None:
                raise RuntimeError("BookDatabase is not initialized")
            cls._creating = True
            try:
                cls._instance = cls(book_repository)
            finally:
                cls._creating = False
        return cls._instance

    def searchBook(self, title: str):
        cleaned = (title or "").strip()
        if not cleaned:
            return None
        row = self._books.search_title(cleaned)
        if row is None:
            return None
        return self._to_book(row)

    def listBooks(self, query: str, page: int, pageSize: int):
        rows, total = self._books.list_books(query or "", page, pageSize)
        return [self._to_book(row) for row in rows], total

    def getBook(self, bookID: int):
        row = self._books.get(bookID)
        if row is None:
            return None
        return self._to_book(row)

    def saveBook(self, book: Book) -> Book:
        payload = {
            "isbn": book.isbn,
            "title": book.title,
            "author": book.author,
            "price": book.price,
            "stock": book.stock,
        }
        if book.bookID is None:
            if not payload["isbn"]:
                payload["isbn"] = self._nextIsbn()
                book.isbn = payload["isbn"]
            saved = self._books.insert(payload)
            book.bookID = saved["book_id"]
            return book
        saved = self._books.update(book.bookID, payload)
        if saved is None:
            return None
        return book

    def _nextIsbn(self) -> str:
        latest = self._books.max_generated_isbn()
        sequence = 1
        if latest and latest.startswith("978") and latest[3:].isdigit():
            sequence = int(latest[3:]) + 1
        return f"978{sequence:010d}"

    def _to_book(self, row: dict) -> Book:
        return Book(
            isbn=row["isbn"],
            title=row["title"],
            author=row["author"],
            price=row["price"],
            stock=row["stock"],
            bookID=row["book_id"],
        )
