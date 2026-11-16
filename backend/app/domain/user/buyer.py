from app.domain.catalog.book_database import BookDatabase
from app.domain.review.review import Review
from app.domain.user.user import User


# Buyer is the subclass used when USERS.role is "buyer". The shipping
# address from registration lives here, and the job title stays empty.
# Browsing, checkout, and writing a review belong to the buyer.
class Buyer(User):
    def __init__(self, userID, name, email, passwordHash, shippingAddress):
        super().__init__(userID, name, email, passwordHash, "buyer")
        self.shippingAddress = shippingAddress

    def browseBooks(self, query: str = "", page: int = 1, pageSize: int = 12):
        books, _total = BookDatabase.getInstance().listBooks(query, page, pageSize)
        return books

    def checkout(self, cart, paymentMethod: str):
        return cart.checkout(paymentMethod)

    def writeReview(self, book, rating: int, comment: str) -> Review:
        Review.validate(rating, comment)
        return Review(
            reviewID=None,
            rating=rating,
            comment=comment,
            userID=self.userID,
            bookID=book.bookID,
            userName=self.name,
        )
