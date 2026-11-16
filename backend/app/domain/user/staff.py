from app.domain.catalog.book_database import BookDatabase
from app.domain.user.user import User


# Staff is the subclass used when USERS.role is "staff". The job title is
# stored on this object instead of a shipping address. Adding and updating
# books in the catalog goes through staff.
class Staff(User):
    def __init__(self, userID, name, email, passwordHash, jobTitle):
        super().__init__(userID, name, email, passwordHash, "staff")
        self.jobTitle = jobTitle

    def addBook(self, book):
        return BookDatabase.getInstance().saveBook(book)

    def updateBook(self, book):
        return BookDatabase.getInstance().saveBook(book)
