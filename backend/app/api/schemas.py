from pydantic import BaseModel


class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str
    role: str
    shippingAddress: str | None = None
    jobTitle: str | None = None


class LoginRequest(BaseModel):
    email: str
    password: str


class BookCreate(BaseModel):
    title: str
    author: str
    price: float
    stock: int
    isbn: str | None = None


class BookUpdate(BaseModel):
    title: str | None = None
    author: str | None = None
    price: float | None = None
    stock: int | None = None
    isbn: str | None = None


class CartAdd(BaseModel):
    bookId: int
    quantity: int | None = None


class CheckoutRequest(BaseModel):
    paymentMethod: str


class ReviewCreate(BaseModel):
    bookId: int
    rating: int
    comment: str


class ReviewUpdate(BaseModel):
    rating: int | None = None
    comment: str | None = None
