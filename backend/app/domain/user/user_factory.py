from app.domain.errors import ValidationError
from app.domain.user.buyer import Buyer
from app.domain.user.staff import Staff


class UserFactory:
    # Registration should not sprinkle `if role == "buyer"` through the API
    # and construct Buyer or Staff there. createUser is the one place that
    # choice is made. It returns a Buyer or a Staff, and rejects any other role.
    def createUser(
        self,
        type: str,
        name: str,
        email: str,
        passwordHash: str,
        userID=None,
        shippingAddress=None,
        jobTitle=None,
    ):
        kind = (type or "").strip().lower()
        if kind == "buyer":
            return Buyer(userID, name, email, passwordHash, shippingAddress)
        if kind == "staff":
            return Staff(userID, name, email, passwordHash, jobTitle)
        raise ValidationError("role must be buyer or staff")
