from abc import ABC

from app.domain.errors import OrderAlreadyDelivered


class OrderState(ABC):
    def next(self, order) -> None:
        raise NotImplementedError

    def getStatus(self) -> str:
        raise NotImplementedError


class PendingState(OrderState):
    # A new order starts pending after checkout. next() moves it to shipped
    # and nowhere else. ORDERS.status stores "pending" while the order is
    # in this state.
    def next(self, order) -> None:
        order.setState(ShippedState())

    def getStatus(self) -> str:
        return "pending"


class ShippedState(OrderState):
    # After the order has shipped, the only allowed advance is to delivered.
    # Staff call next() to make that move. ORDERS.status stores "shipped"
    # until then.
    def next(self, order) -> None:
        order.setState(DeliveredState())

    def getStatus(self) -> str:
        return "shipped"


class DeliveredState(OrderState):
    # Delivered is the last step. next() refuses another advance and raises
    # OrderAlreadyDelivered, so the order cannot leave this state.
    # ORDERS.status stays "delivered".
    def next(self, order) -> None:
        raise OrderAlreadyDelivered("Order is already delivered")

    def getStatus(self) -> str:
        return "delivered"


def stateFromStatus(status: str) -> OrderState:
    if status == "pending":
        return PendingState()
    if status == "shipped":
        return ShippedState()
    if status == "delivered":
        return DeliveredState()
    raise ValueError(f"Unknown order status: {status}")
