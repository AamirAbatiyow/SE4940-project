from abc import ABC


class OrderObserver(ABC):
    def update(self, status: str) -> None:
        raise NotImplementedError
