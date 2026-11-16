class Account:
    def __init__(self, accountID, status, userID=None):
        self.accountID = accountID
        self.status = status
        self.userID = userID

    # A new account is created inactive. Registration and the seed data call
    # activate so the ACCOUNTS row is saved as active.
    def activate(self) -> None:
        self.status = "active"
