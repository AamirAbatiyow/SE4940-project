from app.domain.money import money


class Book:
    def __init__(self, isbn, title, author, price, stock, bookID=None):
        self.bookID = bookID
        self.isbn = isbn
        self.title = title
        self.author = author
        self.price = money(price)
        self.stock = int(stock)

    def isAvailable(self) -> bool:
        return self.stock > 0
