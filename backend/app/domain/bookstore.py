import re

from app.domain.cart.shopping_cart import ShoppingCartManagement
from app.domain.catalog.book import Book
from app.domain.catalog.book_database import BookDatabase
from app.domain.errors import (
    AuthError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
    ValidationError,
)
from app.domain.money import money
from app.domain.notification.buyer_notification import BuyerNotification
from app.domain.order.line_item import LineItem
from app.domain.order.order import Order, PaymentRecord
from app.domain.order.order_state import stateFromStatus
from app.domain.review.review import Review
from app.domain.user.account import Account
from app.domain.user.buyer import Buyer
from app.domain.user.passwords import hash_password
from app.domain.user.staff import Staff
from app.domain.user.user_factory import UserFactory

_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class BookStoreManagementSystem:
    def __init__(self, users, accounts, carts, orders, reviews, factory=None):
        self.database = BookDatabase.getInstance()
        self.users = users
        self.accounts = accounts
        self.carts = carts
        self.orders = orders
        self.reviews = reviews
        self.factory = factory or UserFactory()

    def registerUser(self, name, email, password, role, shippingAddress=None, jobTitle=None):
        cleaned_name = (name or "").strip()
        cleaned_email = (email or "").strip().lower()
        if not cleaned_name:
            raise ValidationError("name is required")
        if not _EMAIL.match(cleaned_email):
            raise ValidationError("Enter a valid email")
        if not password:
            raise ValidationError("password is required")
        if role not in ("buyer", "staff"):
            raise ValidationError("role must be buyer or staff")
        if self.users.get_by_email(cleaned_email) is not None:
            raise ConflictError("An account with that email already exists")

        shipping = None
        job = None
        if role == "buyer" and shippingAddress and shippingAddress.strip():
            shipping = shippingAddress.strip()
        if role == "staff" and jobTitle and jobTitle.strip():
            job = jobTitle.strip()

        user = self.factory.createUser(
            role,
            name=cleaned_name,
            email=cleaned_email,
            passwordHash=hash_password(password),
            shippingAddress=shipping,
            jobTitle=job,
        )
        account = Account(accountID=None, status="inactive", userID=None)
        account.activate()
        saved = self.users.register(
            {
                "name": user.name,
                "email": user.email,
                "password_hash": user.passwordHash,
                "role": user.role,
                "shipping_address": user.shippingAddress,
                "job_title": user.jobTitle,
            },
            account.status,
        )
        user.userID = saved["user_id"]
        account.accountID = saved["account_id"]
        account.userID = saved["user_id"]
        return user, account

    def login(self, email, password):
        found = self.users.get_by_email((email or "").strip().lower())
        if found is None:
            raise AuthError("Invalid email or password")
        user = self._to_user(found)
        if not user.login(email, password):
            raise AuthError("Invalid email or password")
        return user, self.getAccount(user)

    def logout(self, user) -> None:
        user.logout()

    def getUser(self, userID):
        row = self.users.get_by_id(userID)
        if row is None:
            return None
        return self._to_user(row)

    def getAccount(self, user):
        row = self.accounts.get_by_user(user.userID)
        if row is None:
            raise NotFoundError("Account not found")
        return Account(row["account_id"], row["status"], row["user_id"])

    def browseBooks(self, query: str = "", page: int = 1, pageSize: int = 12):
        self._check_page(page, pageSize)
        return self.database.listBooks(query or "", page, pageSize)

    def getBook(self, bookId: int):
        book = self.database.getBook(bookId)
        if book is None:
            raise NotFoundError("Book not found")
        reviews = [self._to_review(row) for row in self.reviews.list_for_book(bookId)]
        return book, reviews

    def addBook(self, user, title, author, price, stock, isbn=None):
        if not isinstance(user, Staff):
            raise ForbiddenError("Only staff can add books")
        cleaned_title = (title or "").strip()
        cleaned_author = (author or "").strip()
        if not cleaned_title:
            raise ValidationError("title is required")
        if not cleaned_author:
            raise ValidationError("author is required")
        self._check_price(price)
        self._check_stock(stock)
        book = Book(
            isbn=(isbn or "").strip(),
            title=cleaned_title,
            author=cleaned_author,
            price=price,
            stock=stock,
        )
        try:
            return user.addBook(book)
        except ValueError as exc:
            raise ConflictError(str(exc)) from exc

    def updateBook(self, user, bookId, fields: dict):
        if not isinstance(user, Staff):
            raise ForbiddenError("Only staff can update books")
        if not fields:
            raise ValidationError("Nothing to update")
        book = self.database.getBook(bookId)
        if book is None:
            raise NotFoundError("Book not found")
        if "title" in fields:
            cleaned = (fields["title"] or "").strip()
            if not cleaned:
                raise ValidationError("title is required")
            book.title = cleaned
        if "author" in fields:
            cleaned = (fields["author"] or "").strip()
            if not cleaned:
                raise ValidationError("author is required")
            book.author = cleaned
        if "price" in fields:
            self._check_price(fields["price"])
            book.price = money(fields["price"])
        if "stock" in fields:
            self._check_stock(fields["stock"])
            book.stock = fields["stock"]
        if "isbn" in fields:
            cleaned = (fields["isbn"] or "").strip()
            if not cleaned:
                raise ValidationError("isbn is required")
            book.isbn = cleaned
        try:
            saved = user.updateBook(book)
        except ValueError as exc:
            raise ConflictError(str(exc)) from exc
        if saved is None:
            raise NotFoundError("Book not found")
        return saved

    def getCart(self, user):
        return self._load_cart(user)

    def addToCart(self, user, bookId, quantity=None):
        if quantity is None:
            quantity = 1
        if type(quantity) is not int or quantity < 1:
            raise ValidationError("quantity must be a positive integer")
        book = self.database.getBook(bookId)
        if book is None:
            raise NotFoundError("Book not found")
        cart = self._load_cart(user)
        cart.addBook(book, quantity)
        self.carts.save_line(cart.cartID, book.bookID, cart.quantityOf(book.bookID))
        return self._load_cart(user)

    def removeFromCart(self, user, bookId):
        book = self.database.getBook(bookId)
        if book is None:
            raise NotFoundError("Book not found")
        cart = self._load_cart(user)
        if not cart.holds(book):
            raise NotFoundError("That book is not in the cart")
        cart.removeBook(book)
        self.carts.delete_line(cart.cartID, book.bookID)
        return self._load_cart(user)

    def checkout(self, user, paymentMethod):
        if not isinstance(user, Buyer):
            raise ForbiddenError("Only buyers can checkout")
        cart = self._load_cart(user)
        order = user.checkout(cart, paymentMethod)
        saved = self.orders.place(
            user_id=user.userID,
            cart_id=cart.cartID,
            status=order.state.getStatus(),
            total_amount=order.totalAmount,
            created_at=order.orderDate,
            items=[
                {
                    "book_id": item.bookID,
                    "quantity": item.quantity,
                    "unit_price": item.unitPrice,
                }
                for item in order.items
            ],
            payment_method=paymentMethod,
            payment_status="paid",
            payment_amount=order.totalAmount,
        )
        stored = self._hydrate_order(saved)
        notification = BuyerNotification(user)
        stored.addObserver(notification)
        stored.placeOrder()
        return stored, notification

    def listOrders(self, user):
        if not isinstance(user, Buyer):
            raise ForbiddenError("Only buyers can view their orders")
        return [self._hydrate_order(row) for row in self.orders.list_for_user(user.userID)]

    def getOrder(self, user, orderId):
        data = self.orders.get(orderId)
        if data is None:
            raise NotFoundError("Order not found")
        if isinstance(user, Staff):
            return self._hydrate_order(data)
        if not isinstance(user, Buyer) or data["user_id"] != user.userID:
            raise ForbiddenError("You can only view your own orders")
        return self._hydrate_order(data)

    def listAllOrders(self, user):
        if not isinstance(user, Staff):
            raise ForbiddenError("Only staff can view every order")
        return [self._hydrate_order(row) for row in self.orders.list_all()]

    def advanceOrder(self, user, orderId):
        if not isinstance(user, Staff):
            raise ForbiddenError("Only staff can advance orders")
        data = self.orders.get(orderId)
        if data is None:
            raise NotFoundError("Order not found")
        order = self._hydrate_order(data)
        buyer = None
        buyer_row = self.users.get_by_id(order.userID)
        if buyer_row is not None:
            loaded = self._to_user(buyer_row)
            if isinstance(loaded, Buyer):
                buyer = loaded
        notification = BuyerNotification(buyer)
        order.addObserver(notification)
        order.state.next(order)
        self.orders.update_status(order.orderID, order.state.getStatus())
        refreshed = self.orders.get(order.orderID)
        return self._hydrate_order(refreshed), notification

    def writeReview(self, user, bookId, rating, comment):
        if not isinstance(user, Buyer):
            raise ForbiddenError("Only buyers can write reviews")
        book = self.database.getBook(bookId)
        if book is None:
            raise NotFoundError("Book not found")
        review = user.writeReview(book, rating, comment)
        saved = self.reviews.insert(
            user_id=review.userID,
            book_id=review.bookID,
            rating=review.rating,
            comment=review.comment,
        )
        review.reviewID = saved["review_id"]
        return review

    def editReview(self, user, reviewId, rating=None, comment=None):
        data = self.reviews.get(reviewId)
        if data is None:
            raise NotFoundError("Review not found")
        if data["user_id"] != user.userID:
            raise ForbiddenError("You can only edit your own review")
        review = self._to_review(data)
        review.editReview(rating=rating, comment=comment)
        self.reviews.update(review.reviewID, review.rating, review.comment)
        return review

    def _load_cart(self, user):
        data = self.carts.get_by_user(user.userID)
        if data is None:
            self.carts.create(user.userID)
            data = self.carts.get_by_user(user.userID)
        return ShoppingCartManagement.load(data["cart_id"], user.userID, data["items"])

    def _to_user(self, row):
        return self.factory.createUser(
            row["role"],
            userID=row["user_id"],
            name=row["name"],
            email=row["email"],
            passwordHash=row["password_hash"],
            shippingAddress=row.get("shipping_address"),
            jobTitle=row.get("job_title"),
        )

    def _to_review(self, row):
        return Review(
            row["review_id"],
            row["rating"],
            row["comment"],
            row["user_id"],
            row["book_id"],
            row.get("user_name"),
        )

    def _hydrate_order(self, data) -> Order:
        payment = None
        if data.get("payment"):
            pay = data["payment"]
            payment = PaymentRecord(
                pay["payment_id"],
                pay["method"],
                pay["status"],
                pay["amount"],
                pay["created_at"],
            )
        return Order(
            orderID=data["order_id"],
            orderDate=data["created_at"],
            totalAmount=data["total_amount"],
            state=stateFromStatus(data["status"]),
            items=[
                LineItem(item["quantity"], item["unit_price"], item["book_id"], item.get("title"))
                for item in data["items"]
            ],
            userID=data["user_id"],
            payment=payment,
        )

    def _check_page(self, page, pageSize) -> None:
        if type(page) is not int or page < 1:
            raise ValidationError("page must be at least 1")
        if type(pageSize) is not int or pageSize < 1:
            raise ValidationError("pageSize must be at least 1")
        if pageSize > 100:
            raise ValidationError("pageSize cannot be greater than 100")

    def _check_price(self, price) -> None:
        if isinstance(price, bool) or not isinstance(price, (int, float)):
            raise ValidationError("price must be a number")
        if price != price or price in (float("inf"), float("-inf")):
            raise ValidationError("price must be a number")
        if price < 0:
            raise ValidationError("price cannot be negative")

    def _check_stock(self, stock) -> None:
        if type(stock) is not int or stock < 0:
            raise ValidationError("stock must be a whole number that is zero or greater")
