from app.domain.payment.payment_strategy import PaymentStrategy


# Used when the buyer checks out with credit_card. pay(amount) accepts a
# total greater than zero. The route does not look at a card number; it
# only passes the method name on to checkout.
class CreditCardPayment(PaymentStrategy):
    def pay(self, amount: float) -> bool:
        return amount > 0
