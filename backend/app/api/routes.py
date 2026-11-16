from fastapi import APIRouter, Depends, Header, HTTPException, Request

from app.api.present import book_json, cart_json, order_json, review_json, user_json
from app.api.schemas import (
    BookCreate,
    BookUpdate,
    CartAdd,
    CheckoutRequest,
    LoginRequest,
    RegisterRequest,
    ReviewCreate,
    ReviewUpdate,
)
from app.api.tokens import create_token, read_token
from app.domain.errors import (
    AuthError,
    CheckoutError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
    OrderAlreadyDelivered,
    ValidationError,
)

router = APIRouter(prefix="/api")


def call(action):
    try:
        return action()
    except AuthError as exc:
        raise HTTPException(status_code=401, detail=exc.message) from exc
    except ForbiddenError as exc:
        raise HTTPException(status_code=403, detail=exc.message) from exc
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=exc.message) from exc
    except ConflictError as exc:
        raise HTTPException(status_code=409, detail=exc.message) from exc
    except (ValidationError, CheckoutError, OrderAlreadyDelivered) as exc:
        raise HTTPException(status_code=400, detail=exc.message) from exc


def require_user(request: Request, authorization: str | None = Header(default=None)):
    if authorization is None or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        user_id = read_token(token)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="Not authenticated") from exc
    user = request.app.state.store.getUser(user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


@router.post("/auth/register", status_code=201)
def register(body: RegisterRequest, request: Request):
    user, account = call(
        lambda: request.app.state.store.registerUser(
            body.name,
            body.email,
            body.password,
            body.role,
            body.shippingAddress,
            body.jobTitle,
        )
    )
    return {"token": create_token(user.userID), **user_json(user, account)}


@router.post("/auth/login")
def login(body: LoginRequest, request: Request):
    user, account = call(lambda: request.app.state.store.login(body.email, body.password))
    return {"token": create_token(user.userID), **user_json(user, account)}


@router.post("/auth/logout")
def logout(request: Request, user=Depends(require_user)):
    call(lambda: request.app.state.store.logout(user))
    return {"ok": True}


@router.get("/me")
def me(request: Request, user=Depends(require_user)):
    account = call(lambda: request.app.state.store.getAccount(user))
    return user_json(user, account)


@router.get("/books")
def list_books(request: Request, q: str = "", page: int = 1, pageSize: int = 12):
    books, total = call(lambda: request.app.state.store.browseBooks(q, page, pageSize))
    return {
        "books": [book_json(book) for book in books],
        "page": page,
        "pageSize": pageSize,
        "total": total,
    }


@router.get("/books/{bookId}")
def get_book(bookId: int, request: Request):
    book, reviews = call(lambda: request.app.state.store.getBook(bookId))
    return {**book_json(book), "reviews": [review_json(review) for review in reviews]}


@router.post("/books", status_code=201)
def add_book(body: BookCreate, request: Request, user=Depends(require_user)):
    book = call(
        lambda: request.app.state.store.addBook(
            user,
            body.title,
            body.author,
            body.price,
            body.stock,
            body.isbn,
        )
    )
    return book_json(book)


@router.put("/books/{bookId}")
def update_book(bookId: int, body: BookUpdate, request: Request, user=Depends(require_user)):
    fields = body.model_dump(exclude_unset=True)
    book = call(lambda: request.app.state.store.updateBook(user, bookId, fields))
    return book_json(book)


@router.get("/cart")
def get_cart(request: Request, user=Depends(require_user)):
    cart = call(lambda: request.app.state.store.getCart(user))
    return cart_json(cart)


@router.post("/cart/items")
def add_cart_item(body: CartAdd, request: Request, user=Depends(require_user)):
    cart = call(lambda: request.app.state.store.addToCart(user, body.bookId, body.quantity))
    return cart_json(cart)


@router.delete("/cart/items/{bookId}")
def remove_cart_item(bookId: int, request: Request, user=Depends(require_user)):
    cart = call(lambda: request.app.state.store.removeFromCart(user, bookId))
    return cart_json(cart)


@router.post("/checkout")
def checkout(body: CheckoutRequest, request: Request, user=Depends(require_user)):
    order, notification = call(
        lambda: request.app.state.store.checkout(user, body.paymentMethod)
    )
    return {"order": order_json(order), "notification": {"message": notification.message}}


@router.get("/orders")
def list_orders(request: Request, user=Depends(require_user)):
    orders = call(lambda: request.app.state.store.listOrders(user))
    return [order_json(order) for order in orders]


@router.get("/orders/{orderId}")
def get_order(orderId: int, request: Request, user=Depends(require_user)):
    order = call(lambda: request.app.state.store.getOrder(user, orderId))
    return order_json(order)


@router.get("/staff/orders")
def list_staff_orders(request: Request, user=Depends(require_user)):
    orders = call(lambda: request.app.state.store.listAllOrders(user))
    return [order_json(order) for order in orders]


@router.post("/orders/{orderId}/advance")
def advance_order(orderId: int, request: Request, user=Depends(require_user)):
    order, notification = call(lambda: request.app.state.store.advanceOrder(user, orderId))
    return {"order": order_json(order), "notification": {"message": notification.message}}


@router.post("/reviews", status_code=201)
def write_review(body: ReviewCreate, request: Request, user=Depends(require_user)):
    review = call(
        lambda: request.app.state.store.writeReview(user, body.bookId, body.rating, body.comment)
    )
    return review_json(review)


@router.put("/reviews/{reviewId}")
def edit_review(reviewId: int, body: ReviewUpdate, request: Request, user=Depends(require_user)):
    fields = body.model_dump(exclude_unset=True)
    review = call(
        lambda: request.app.state.store.editReview(
            user,
            reviewId,
            fields.get("rating"),
            fields.get("comment") if "comment" in fields else None,
        )
    )
    return review_json(review)
