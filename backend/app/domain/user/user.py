from abc import ABC

from app.domain.user.passwords import verify_password


# Buyers and staff are stored as one USERS row. The role column decides
# which subclass is built when that row is loaded. A buyer keeps a shipping
# address; a staff member keeps a job title. Login is shared by both.
class User(ABC):
    def __init__(self, userID, name, email, passwordHash, role):
        if type(self) is User:
            raise TypeError("User is abstract")
        self.userID = userID
        self.name = name
        self.email = email
        self.passwordHash = passwordHash
        self.role = role
        self.shippingAddress = None
        self.jobTitle = None

    def login(self, email: str, password: str) -> bool:
        supplied = (email or "").strip().lower()
        if supplied != (self.email or "").lower():
            return False
        return verify_password(password or "", self.passwordHash)

    def logout(self) -> None:
        return None
