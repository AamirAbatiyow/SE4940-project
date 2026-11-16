from app.domain.notification.order_observer import OrderObserver


class BuyerNotification(OrderObserver):
    def __init__(self, buyer=None):
        self.buyer = buyer
        self.message = ""

    # The buyer on this notification is who hears about the status change.
    # update stores a short message such as "Your order is now shipped."
    # Checkout and advance return that message. It is not saved in its own table.
    def update(self, status: str) -> None:
        self.message = f"Your order is now {status}."
