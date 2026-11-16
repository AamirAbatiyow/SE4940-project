from abc import ABC


# Checkout charges the order total through a strategy. The order and the
# API route do not branch on credit card versus PayPal. They only need
# pay(amount) to succeed or fail.
class PaymentStrategy(ABC):
    def pay(self, amount: float) -> bool:
        raise NotImplementedError
