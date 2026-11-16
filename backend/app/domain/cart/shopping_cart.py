from app.domain.catalog.book_database import BookDatabase
from app.domain.errors import CheckoutError
from app.domain.money import line_total, money
from app.domain.order.line_item import LineItem
from app.domain.order.order import Order
from app.domain.order.order_state import PendingState
from app.domain.payment.credit_card_payment import CreditCardPayment
from app.domain.payment.payment_processor import PaymentProcessor
from app.domain.payment.paypal_payment import PayPalPayment


def utcnow():
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).replace(microsecond=0, tzinfo=None)


class _CartLine:
    def __init__(self, bookID, title, author, quantity, unitPrice):
        self.bookID = bookID
        self.title = title
        self.author = author
        self.quantity = quantity
        self.unitPrice = money(unitPrice)

    def calculateSubtotal(self) -> float:
        return line_total(self.quantity, self.unitPrice)


class ShoppingCartManagement:
    def __init__(self, cartID, userID=None):
        self.cartID = cartID
        self.userID = userID
        self.lines = []

    @classmethod
    def load(cls, cartID, userID, items):
        cart = cls(cartID, userID=userID)
        for item in items:
            cart.lines.append(
                _CartLine(
                    item["book_id"],
                    item["title"],
                    item["author"],
                    item["quantity"],
                    item["unit_price"],
                )
            )
        return cart

    def addBook(self, book, quantity: int = 1) -> None:
        for line in self.lines:
            if line.bookID == book.bookID:
                line.quantity += quantity
                line.unitPrice = money(book.price)
                line.title = book.title
                line.author = book.author
                return
        self.lines.append(
            _CartLine(book.bookID, book.title, book.author, quantity, book.price)
        )

    def removeBook(self, book) -> None:
        self.lines = [line for line in self.lines if line.bookID != book.bookID]

    def holds(self, book) -> bool:
        return any(line.bookID == book.bookID for line in self.lines)

    def quantityOf(self, bookID) -> int:
        for line in self.lines:
            if line.bookID == bookID:
                return line.quantity
        return 0

    def calculateTotal(self) -> float:
        return money(sum(line.calculateSubtotal() for line in self.lines))

    def checkout(self, paymentMethod: str):
        if not self.lines:
            raise CheckoutError("Cart is empty")

        items = []
        catalog = BookDatabase.getInstance()
        for line in self.lines:
            book = catalog.getBook(line.bookID)
            if book is None:
                raise CheckoutError("A book in the cart is no longer available")
            if book.stock < line.quantity:
                raise CheckoutError(f"Not enough stock for {book.title}")
            items.append(LineItem(line.quantity, book.price, book.bookID, book.title))

        total = money(sum(item.calculateSubtotal() for item in items))
        order = Order(
            orderID=None,
            orderDate=utcnow(),
            totalAmount=total,
            state=PendingState(),
            items=items,
            userID=self.userID,
        )
        processor = PaymentProcessor()
        if paymentMethod == "credit_card":
            processor.setStrategy(CreditCardPayment())
        elif paymentMethod == "paypal":
            processor.setStrategy(PayPalPayment())
        else:
            raise CheckoutError("paymentMethod must be credit_card or paypal")
        order.paymentProcessor = processor
        if not order.paymentProcessor.processPayment(order.totalAmount):
            raise CheckoutError("Payment failed")
        return order
