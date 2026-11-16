from app.domain.errors import ValidationError


class Review:
    def __init__(self, reviewID, rating, comment, userID=None, bookID=None, userName=None):
        self.reviewID = reviewID
        self.rating = rating
        self.comment = comment
        self.userID = userID
        self.bookID = bookID
        self.userName = userName

    @staticmethod
    def validate(rating, comment) -> None:
        if type(rating) is not int or not 1 <= rating <= 5:
            raise ValidationError("rating must be an integer from 1 to 5")
        if not isinstance(comment, str):
            raise ValidationError("comment must be a string")

    def editReview(self, rating=None, comment=None) -> None:
        if rating is None and comment is None:
            raise ValidationError("Nothing to update")
        if rating is not None:
            Review.validate(rating, self.comment if comment is None else comment)
            self.rating = rating
        if comment is not None:
            if not isinstance(comment, str):
                raise ValidationError("comment must be a string")
            self.comment = comment
