def iso(value):
    if value is None:
        return None
    if isinstance(value, str):
        return value
    text = value.isoformat()
    if value.tzinfo is None:
        return text + "Z"
    return text


def user_json(user, account) -> dict:
    return {
        "user": {
            "userId": user.userID,
            "name": user.name,
            "email": user.email,
            "role": user.role,
            "shippingAddress": user.shippingAddress,
            "jobTitle": user.jobTitle,
        },
        "account": {
            "accountId": account.accountID,
            "status": account.status,
        },
    }


def book_json(book) -> dict:
    return {
        "bookId": book.bookID,
        "isbn": book.isbn,
        "title": book.title,
        "author": book.author,
        "price": book.price,
        "stock": book.stock,
        "available": book.isAvailable(),
    }


def review_json(review) -> dict:
    return {
        "reviewId": review.reviewID,
        "userId": review.userID,
        "userName": review.userName,
        "rating": review.rating,
        "comment": review.comment,
    }


def cart_json(cart) -> dict:
    return {
        "cartId": cart.cartID,
        "items": [
            {
                "bookId": line.bookID,
                "title": line.title,
                "author": line.author,
                "quantity": line.quantity,
                "unitPrice": line.unitPrice,
                "subtotal": line.calculateSubtotal(),
            }
            for line in cart.lines
        ],
        "total": cart.calculateTotal(),
    }


def order_json(order) -> dict:
    payment = None
    if order.payment is not None:
        payment = {
            "paymentId": order.payment.paymentID,
            "method": order.payment.method,
            "status": order.payment.status,
            "amount": order.payment.amount,
            "createdAt": iso(order.payment.createdAt),
        }
    return {
        "orderId": order.orderID,
        "status": order.state.getStatus(),
        "totalAmount": order.totalAmount,
        "createdAt": iso(order.orderDate),
        "items": [
            {
                "bookId": item.bookID,
                "title": item.title,
                "quantity": item.quantity,
                "unitPrice": item.unitPrice,
                "subtotal": item.calculateSubtotal(),
            }
            for item in order.items
        ],
        "payment": payment,
    }
