from app.domain.payment.payment_strategy import PaymentStrategy


# Used when the buyer checks out with paypal. pay(amount) accepts a positive
# total, the same contract as the card strategy. The processor calls pay
# without a special case for PayPal.
class PayPalPayment(PaymentStrategy):
    def pay(self, amount: float) -> bool:
        return amount > 0
