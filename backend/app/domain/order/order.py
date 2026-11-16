from app.domain.money import money
from app.domain.order.order_state import PendingState


class PaymentRecord:
    """One saved PAYMENTS row. The strategy classes decide whether pay() succeeds."""

    def __init__(self, paymentID, method, status, amount, createdAt):
        self.paymentID = paymentID
        self.method = method
        self.status = status
        self.amount = money(amount)
        self.createdAt = createdAt


class Order:
    def __init__(self, orderID, orderDate, totalAmount, state, items, userID=None, payment=None):
        self.orderID = orderID
        self.orderDate = orderDate
        self.totalAmount = money(totalAmount)
        self.state = state
        self.items = list(items)
        self.userID = userID
        self.payment = payment
        self.paymentProcessor = None
        self.observers = []

    def placeOrder(self) -> None:
        self.setState(PendingState())

    def setState(self, state) -> None:
        self.state = state
        self.notifyObservers()

    # setState calls this after the status changes. Each registered observer
    # gets update with the new status, which is how the buyer is told.
    # Nothing is inserted into the database.
    def notifyObservers(self) -> None:
        status = self.state.getStatus()
        for observer in list(self.observers):
            observer.update(status)

    # Checkout and staff advance register a BuyerNotification before the
    # status changes. addObserver keeps that object on the order. The list
    # is not a database table; it only exists on this in-memory order.
    def addObserver(self, observer) -> None:
        self.observers.append(observer)

    def addObservers(self, observer) -> None:
        # The class diagram spells this addObservers. addObserver is the same operation.
        self.addObserver(observer)

    def removeObserver(self, observer) -> None:
        self.observers = [item for item in self.observers if item is not observer]
