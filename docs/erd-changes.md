# ERD changes for BookNest

Update `docs/final project erd.drawio`. Keep every table and column that is already on the diagram. Add only the columns and tables below.

The database is the existing ERD, plus the fields the UML stores that the diagram does not. `book_id` stays the primary key of `BOOKS`. ISBN is also the book's identity in the UML, so both columns exist.

Generated files (do not draw these, and do not commit them):

- `data/seed/books.csv` is written by `backend/app/seed/transform_books.py`.
- `data/bookstore.db` is written by `backend/app/seed/seed_database.py`.

`data/raw-books/BooksDatasetClean.csv` stays in the repo. The seed scripts read it, reshape it, and load SQLite.

## Keep these tables as they are

- `USERS`: `user_id` PK, `email` UK, `password_hash`, `role`
- `BOOKS`: `book_id` PK, `title`, `author`, `price`
- `ORDERS`: `order_id` PK, `user_id` FK, `status`, `created_at`
- `CARTS`: `cart_id` PK, `user_id` FK UK
- `CART_ITEMS`: `cart_id` PK FK, `book_id` PK FK, `quantity`
- `ORDER_ITEMS`: `order_id` PK FK, `book_id` PK FK, `quantity`, `unit_price`
- `PAYMENTS`: `payment_id` PK, `order_id` FK, `method`, `status`, `amount`, `created_at`

Keep the existing relationships: user places orders, user owns one cart, cart contains cart items, order contains order items, book appears in cart items and order items, order has payment attempts.

## Columns to add

### USERS

- `name` : string, required
- `shipping_address` : string, nullable. Buyers only. Leave it null for staff.
- `job_title` : string, nullable. Staff only. Leave it null for buyers.

`role` stays. One `USERS` row maps to the UML subclasses: `role` is `buyer` or `staff`. Do not split Buyer and Staff into two tables.

### BOOKS

- `isbn` : string, unique, required. This is the UML identity. `book_id` stays the primary key.
- `stock` : int, required. `available` in the API is `stock > 0`. It is not a column.

### ORDERS

- `total_amount` : decimal, required

`status` stays a string. The values to show on the diagram are `pending`, `shipped`, and `delivered`. `created_at` is the UML `orderDate`. Do not add a separate `order_date` column, and do not add a table per state.

## Tables to add

### ACCOUNTS

UML `Account`, one per user.

- `account_id` : int, PK
- `user_id` : int, FK to `USERS.user_id`, unique
- `status` : string (`inactive` or `active`)

Relationship: `USERS` 1 — 1 `ACCOUNTS`.

A new account starts `inactive`. `activate()` sets `active`. The demo buyer and demo staff are stored as `active`.

### REVIEWS

UML `Review`.

- `review_id` : int, PK
- `user_id` : int, FK to `USERS.user_id`
- `book_id` : int, FK to `BOOKS.book_id`
- `rating` : int (1 through 5)
- `comment` : string

Relationships: `USERS` 1 — 0..* `REVIEWS`, `BOOKS` 1 — 0..* `REVIEWS`.

## Do not add these as tables

These UML pieces are behavior. They are classes in the code, not rows.

- `BuyerNotification` and `OrderObserver`. Checkout and advancing an order return a short message. There is no notifications table.
- `PaymentStrategy`, `CreditCardPayment`, `PayPalPayment`, and `PaymentProcessor`. `PAYMENTS` already stores the attempt. `method` is `credit_card` or `paypal`. A successful checkout stores `status` `paid`. No card number, expiry, or PayPal login is stored.
- `PendingState`, `ShippedState`, and `DeliveredState`. The current state is the `ORDERS.status` string. Loading an order builds the matching state class from that string.

Registration also inserts the one `CARTS` row (`user_id` is already unique). That table is already on the diagram.

## Kaggle columns that are not stored

`data/raw-books/BooksDatasetClean.csv` has columns the ERD and the UML do not use. Do not add them to `BOOKS`:

- `Description`
- `Category`
- `Publisher`
- `Publish Date (Month)`
- `Publish Date (Year)`

The CSV has no ISBN and no stock. The transform script generates both:

- `isbn` is synthetic and unique: `978` plus a zero-padded sequence, in the order rows are kept. The same input always produces the same ISBN.
- `stock` is `5 + (kept row index % 20)`, so it runs from 5 through 24. It is not random.

Rows with no title or no price are skipped and are not loaded. Author text `By Last, First` is stored as `First Last`. If that pattern does not match, a leading `By ` is removed and the rest is stored.
