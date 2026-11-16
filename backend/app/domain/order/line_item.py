from app.domain.money import line_total, money


class LineItem:
    def __init__(self, quantity, unitPrice, bookID=None, title=None):
        self.quantity = quantity
        self.unitPrice = money(unitPrice)
        self.bookID = bookID
        self.title = title

    def calculateSubtotal(self) -> float:
        return line_total(self.quantity, self.unitPrice)
