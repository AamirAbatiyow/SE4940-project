class PaymentProcessor:
    def __init__(self):
        self.strategy = None

    # Checkout chooses credit_card or paypal and passes that strategy here.
    # processPayment then calls pay(amount) on it. The order and the route
    # never contain a card-versus-PayPal branch.
    def setStrategy(self, strategy) -> None:
        self.strategy = strategy

    def processPayment(self, amount: float) -> bool:
        if self.strategy is None:
            return False
        return self.strategy.pay(amount)
