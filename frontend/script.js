const API_BASE = "http://127.0.0.1:8000";
const TOKEN_KEY = "booknestToken";
const PAGE_SIZE = 20;

let currentUser = null;
let bookQuery = "";
let bookPage = 1;
let bookTotal = 0;
let bookPageSize = PAGE_SIZE;
let selectedBookId = null;
let checkoutBusy = false;
let sessionPending = false;
let activeView = "books";
const advancingOrders = {};

function getToken() {
    return localStorage.getItem(TOKEN_KEY) || "";
}

function setToken(token) {
    if (token) {
        localStorage.setItem(TOKEN_KEY, token);
    } else {
        localStorage.removeItem(TOKEN_KEY);
    }
}

function isLoggedIn() {
    return Boolean(getToken() && currentUser);
}

function money(amount) {
    const value = Number(amount);
    const safe = Number.isFinite(value) ? value : 0;
    return "$" + safe.toFixed(2);
}

function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) {
        node.className = className;
    }
    if (text != null) {
        node.textContent = text;
    }
    return node;
}


/*
 * Stores cover results so repeated books do not
 * trigger another Open Library search.
 */
const bookCoverCache = new Map();

/*
 * Finds a cover using the book's title and author.
 * Returns an image URL or null if no match exists.
 */
async function findBookCover(book) {
    const title = String(book.title || "").trim();
    const author = String(book.author || "").trim();

    if (!title) return null;

    const key = (title + "|" + author).toLowerCase();

    // Reuse an existing search, including one in progress.
    if (bookCoverCache.has(key)) {
        return bookCoverCache.get(key);
    }

    const searchPromise = (async function () {
        try {
            const params = new URLSearchParams({
                title: title,
                limit: "5",
                fields: "title,author_name,cover_i"
            });

            if (author) {
                params.set("author", author);
            }

            const response = await fetch(
                "https://openlibrary.org/search.json?" + params
            );

            if (!response.ok) return null;

            const data = await response.json();

            // Choose the first result that has a cover.
            const match = (data.docs || []).find(function (item) {
                return item.cover_i != null;
            });

            if (!match) return null;

            return (
                "https://covers.openlibrary.org/b/id/" +
                match.cover_i +
                "-M.jpg"
            );
        } catch (error) {
            console.warn("Cover lookup failed:", title, error);
            return null;
        }
    })();

    bookCoverCache.set(key, searchPromise);
    return searchPromise;
}

const localBookCovers = {
    1: "covers/1.jpg"
};
function createBookCover(book) {
    const cover = el("div", "book-cover", book.title || "Book");

    findBookCover(book).then(function (imageUrl) {
        if (!imageUrl) return;

        const image = document.createElement("img");
        image.className = "book-cover-image";
        image.alt = "Cover of " + (book.title || "book");
        image.decoding = "async";

        image.onload = function () {
            // Only display the image if it loaded successfully.
            if (image.naturalWidth > 1) {
                cover.textContent = "";
                cover.append(image);
                cover.classList.add("has-image");
            }
        };

        image.onerror = function () {
            // Leave the original title placeholder visible.
        };

        // Start loading immediately.
        image.src = imageUrl;
    });

    return cover;

    // Check whether this book has a locally saved cover.
    const localCover = localBookCovers[book.bookId];

    if (localCover) {
        const image = document.createElement("img");
        image.className = "book-cover-image";
        image.alt = "Cover of " + (book.title || "book");

        // Replace the placeholder only when the image loads.
        image.onload = function () {
            cover.textContent = "";
            cover.append(image);
            cover.classList.add("has-image");
        };

        // If the local image fails, keep the placeholder.
        image.onerror = function () {
            console.warn("Local cover unavailable:", localCover);
        };

        image.src = localCover;
        return cover;
    }

}

function showMessage(id, text, isError) {
    const node = document.getElementById(id);
    if (!node) {
        return;
    }
    node.textContent = text || "";
    node.classList.toggle("error", Boolean(isError) && Boolean(text));
    node.hidden = !text;
}

function showLoginPrompt(id, before, linkText, after) {
    const node = document.getElementById(id);
    if (!node) {
        return;
    }
    node.hidden = false;
    node.classList.remove("error");
    node.textContent = "";
    if (before) {
        node.append(before);
    }
    const link = document.createElement("a");
    link.href = "#login";
    link.textContent = linkText;
    node.append(link);
    if (after) {
        node.append(after);
    }
}

function fieldValue(id) {
    return document.getElementById(id).value.trim();
}

function setBusy(button, busy) {
    if (button) {
        button.disabled = busy;
    }
}

function apiError(message, status) {
    const error = new Error(message || "Request failed.");
    error.status = status;
    return error;
}

function errorDetail(data) {
    if (data && typeof data.detail === "string" && data.detail) {
        return data.detail;
    }
    if (data && Array.isArray(data.detail)) {
        const parts = data.detail.map(function (item) {
            if (typeof item === "string") {
                return item;
            }
            if (item && item.msg) {
                return item.msg;
            }
            return "";
        }).filter(Boolean);
        if (parts.length) {
            return parts.join(" ");
        }
    }
    return "Request failed.";
}

async function readJson(response) {
    const text = await response.text();
    if (!text) {
        return null;
    }
    try {
        return JSON.parse(text);
    } catch (parseError) {
        return { detail: text };
    }
}

async function api(path, options) {
    const opts = options || {};
    const headers = { Accept: "application/json" };
    if (opts.body) {
        headers["Content-Type"] = "application/json";
    }
    const token = getToken();
    if (token) {
        headers.Authorization = "Bearer " + token;
    }

    let response;
    try {
        response = await fetch(API_BASE + path, {
            method: opts.method || "GET",
            headers: headers,
            body: opts.body,
            cache: "no-store"
        });
    } catch (networkError) {
        throw apiError("Could not reach the bookstore API.", 0);
    }

    const data = await readJson(response);
    if (!response.ok) {
        throw apiError(errorDetail(data), response.status);
    }
    return data;
}

function listOf(data, key) {
    if (Array.isArray(data)) {
        return data;
    }
    if (data && Array.isArray(data[key])) {
        return data[key];
    }
    return [];
}

function statusLabel(status) {
    const text = status == null ? "" : String(status);
    if (!text) {
        return "";
    }
    return text.charAt(0).toUpperCase() + text.slice(1);
}

function paymentLabel(method) {
    if (method === "credit_card") {
        return "Credit card";
    }
    if (method === "paypal") {
        return "PayPal";
    }
    return method ? String(method) : "";
}

function formatWhen(value) {
    if (!value) {
        return "";
    }
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
        return String(value);
    }
    return date.toLocaleString();
}

function renderSession() {
    const loggedIn = isLoggedIn();
    const staff = loggedIn && currentUser.role === "staff";
    const navUser = document.getElementById("nav-user");
    document.getElementById("nav-login").hidden = loggedIn;
    document.getElementById("nav-session").hidden = !loggedIn;
    document.getElementById("auth-forms").hidden = loggedIn || (sessionPending && Boolean(getToken()));
    document.getElementById("staff-tools").hidden = !staff;
    navUser.textContent = loggedIn ? (currentUser.name || "") : "";

    const hint = document.getElementById("login-hint");
    const ordersHeading = document.getElementById("orders-heading");
    const ordersHint = document.getElementById("orders-hint");
    if (staff) {
        ordersHeading.textContent = "Orders";
        ordersHint.textContent = "Advance orders that are not delivered.";
    } else {
        ordersHeading.textContent = "Your Orders";
        ordersHint.textContent = "Status of orders you have placed.";
    }

    if (loggedIn) {
        hint.textContent = "You are signed in.";
        showMessage("checkout-message", "");
        if (activeView === "login") {
            showView("books");
        }
        return;
    }

    document.getElementById("checkout-form").hidden = true;
    if (sessionPending && getToken()) {
        hint.textContent = "Checking your session...";
        return;
    }

    hint.textContent = "Log in or create a buyer or staff account.";
}

async function refreshAccountData() {
    await loadCart();
    await loadOrders();
}

async function applyAuth(data) {
    if (!data || !data.token || !data.user) {
        throw apiError("The server did not return a session.", 0);
    }
    setToken(data.token);
    currentUser = data.user;
    document.getElementById("checkout-result").textContent = "";
    renderSession();
    await refreshAccountData();
}

async function loadMe() {
    try {
        const data = await api("/api/me");
        currentUser = data && data.user ? data.user : null;
        if (!currentUser) {
            setToken("");
            showMessage("auth-message", "Please log in again.", true);
            return;
        }
        renderSession();
        await refreshAccountData();
    } catch (error) {
        currentUser = null;
        if (error.status === 401) {
            setToken("");
            showMessage("auth-message", error.message, true);
        } else {
            showMessage("auth-message", error.message, true);
            document.getElementById("cart-items").textContent = "";
            document.getElementById("cart-count").textContent = "";
            document.getElementById("checkout-form").hidden = true;
            setCartLabel(0);
            document.getElementById("cart-intro").hidden = true;
            showMessage("cart-message", error.message, true);
            document.getElementById("orders-list").textContent = "";
            showMessage("orders-message", error.message, true);
            showMessage("checkout-message", error.message, true);
        }
    } finally {
        sessionPending = false;
        renderSession();
        if (!getToken()) {
            renderCart(null);
            await loadOrders();
        } else if (viewFromHash() === "login") {
            showView("books");
        }
    }
}

async function login(event) {
    event.preventDefault();
    const button = event.target.querySelector("button");
    setBusy(button, true);
    showMessage("auth-message", "");
    try {
        const data = await api("/api/auth/login", {
            method: "POST",
            body: JSON.stringify({
                email: fieldValue("login-email"),
                password: document.getElementById("login-password").value
            })
        });
        await applyAuth(data);
        event.target.reset();
        showMessage("auth-message", "Welcome, " + currentUser.name + ".");
    } catch (error) {
        showMessage("auth-message", error.message, true);
    } finally {
        setBusy(button, false);
    }
}

function toggleRegisterFields() {
    const role = document.getElementById("register-role").value;
    document.getElementById("shipping-field").hidden = role !== "buyer";
    document.getElementById("job-field").hidden = role !== "staff";
}

async function register(event) {
    event.preventDefault();
    const button = event.target.querySelector("button");
    setBusy(button, true);
    const role = document.getElementById("register-role").value;
    const body = {
        name: fieldValue("register-name"),
        email: fieldValue("register-email"),
        password: document.getElementById("register-password").value,
        role: role
    };
    if (role === "buyer") {
        const shippingAddress = fieldValue("register-shipping");
        if (shippingAddress) {
            body.shippingAddress = shippingAddress;
        }
    }
    if (role === "staff") {
        const jobTitle = fieldValue("register-job");
        if (jobTitle) {
            body.jobTitle = jobTitle;
        }
    }

    showMessage("auth-message", "");
    try {
        const data = await api("/api/auth/register", {
            method: "POST",
            body: JSON.stringify(body)
        });
        await applyAuth(data);
        event.target.reset();
        toggleRegisterFields();
        showMessage("auth-message", "Account created. Welcome, " + currentUser.name + ".");
    } catch (error) {
        showMessage("auth-message", error.message, true);
    } finally {
        setBusy(button, false);
    }
}

async function logout() {
    const openId = selectedBookId;
    try {
        if (getToken()) {
            await api("/api/auth/logout", { method: "POST" });
        }
    } catch (error) {
        // Drop the saved token either way so the page does not keep a dead session.
    }
    setToken("");
    currentUser = null;
    document.getElementById("checkout-result").textContent = "";
    showMessage("staff-message", "");
    renderSession();
    renderCart(null);
    await loadOrders();
    showView("books");
    if (openId != null) {
        await openBook(openId);
    }
    showMessage("auth-message", "You are logged out.");
}

function searchBooks(event) {
    event.preventDefault();
    bookQuery = fieldValue("search-input");
    bookPage = 1;
    loadBooks();
}

function showPreviousPage() {
    if (bookPage <= 1) {
        return;
    }
    bookPage -= 1;
    loadBooks();
}

function showNextPage() {
    const lastPage = Math.max(1, Math.ceil(bookTotal / bookPageSize));
    if (bookPage >= lastPage) {
        return;
    }
    bookPage += 1;
    loadBooks();
}

async function loadBooks() {
    document.getElementById("books-prev").disabled = true;
    document.getElementById("books-next").disabled = true;
    showMessage("books-message", "Loading books...");

    const params = new URLSearchParams();
    params.set("q", bookQuery);
    params.set("page", String(bookPage));
    params.set("pageSize", String(PAGE_SIZE));

    try {
        const data = await api("/api/books?" + params.toString());
        renderBooks(data);
    } catch (error) {
        document.getElementById("book-grid").textContent = "";
        document.getElementById("books-page").textContent = "";
        document.getElementById("books-prev").disabled = bookPage <= 1;
        document.getElementById("books-next").disabled = true;
        showMessage("books-message", error.message, true);
    }
}

function renderBooks(data) {
    const payload = data || {};
    const books = Array.isArray(payload.books) ? payload.books : [];
    const size = Number(payload.pageSize);
    bookPageSize = Number.isFinite(size) && size > 0 ? size : PAGE_SIZE;
    const total = Number(payload.total);
    bookTotal = Number.isFinite(total) && total >= 0 ? total : 0;
    const responsePage = Number(payload.page);
    if (Number.isFinite(responsePage) && responsePage > 0) {
        bookPage = responsePage;
    }

    const grid = document.getElementById("book-grid");
    grid.textContent = "";
    books.forEach(renderBookCard);

    const booksMessage = document.getElementById("books-message");
    const keepPrompt = booksMessage.querySelector("a[href='#login']");
    if (!books.length && !keepPrompt) {
        showMessage("books-message", bookQuery ? "No books match your search." : "No books found.");
    } else if (books.length && !keepPrompt) {
        showMessage("books-message", "");
    }

    const lastPage = Math.max(1, Math.ceil(bookTotal / bookPageSize));
    const noun = bookTotal === 1 ? "book" : "books";
    document.getElementById("books-page").textContent =
        "Page " + bookPage + " of " + lastPage + " (" + bookTotal + " " + noun + ")";
    document.getElementById("books-prev").disabled = bookPage <= 1;
    document.getElementById("books-next").disabled = bookPage >= lastPage;
    markSelectedBook();
}

function renderBookCard(book) {
    const card = el("article", "book-card");
    card.dataset.bookId = book.bookId == null ? "" : String(book.bookId);
    card.tabIndex = 0;
    if (selectedBookId != null && String(selectedBookId) === card.dataset.bookId) {
        card.classList.add("selected");
    }

    card.append(createBookCover(book));    card.append(el("h3", "", book.title || "Untitled"));
    card.append(el("p", "", book.author || ""));
    card.append(el("p", "book-price", money(book.price)));
    card.append(el(
        "p",
        book.available ? "book-availability available" : "book-availability",
        book.available ? "Available" : "Not available"
    ));

    const button = el("button", "", "Add to Cart");
    button.type = "button";
    button.setAttribute("aria-label", "Add " + (book.title || "book") + " to cart");
    button.addEventListener("click", function (event) {
        event.stopPropagation();
        addToCart(book.bookId);
    });
    card.append(button);

    card.addEventListener("click", function () {
        toggleBook(book.bookId);
    });
    card.addEventListener("keydown", function (event) {
        if (event.key === "Enter" && event.target === card) {
            toggleBook(book.bookId);
        }
    });

    document.getElementById("book-grid").append(card);
}

function markSelectedBook() {
    const cards = document.querySelectorAll("#book-grid .book-card");
    cards.forEach(function (card) {
        const selected = selectedBookId != null && card.dataset.bookId === String(selectedBookId);
        card.classList.toggle("selected", selected);
    });
}

function hideBookDetail() {
    selectedBookId = null;
    const panel = document.getElementById("book-detail");
    panel.hidden = true;
    panel.textContent = "";
    markSelectedBook();
}

function toggleBook(bookId) {
    const panel = document.getElementById("book-detail");
    if (!panel.hidden && selectedBookId != null && String(selectedBookId) === String(bookId)) {
        hideBookDetail();
        return;
    }
    openBook(bookId);
}

async function openBook(bookId) {
    selectedBookId = bookId;
    markSelectedBook();
    const panel = document.getElementById("book-detail");
    panel.hidden = false;
    panel.textContent = "";
    panel.append(el("p", "hint", "Loading book..."));

    try {
        const data = await api("/api/books/" + encodeURIComponent(String(bookId)));
        const book = data && data.bookId != null ? data : (data && data.book ? data.book : null);
        if (!book) {
            throw apiError("Book not found.", 404);
        }
        selectedBookId = book.bookId != null ? book.bookId : bookId;
        renderBookDetail(book);
        panel.scrollIntoView({ behavior: "smooth", block: "nearest" });
    } catch (error) {
        panel.textContent = "";
        panel.append(el("p", "message error", error.message));
        panel.append(closeLink());
    }
}

function closeLink() {
    const close = el("a", "text-link", "Close");
    close.href = "#books";
    close.addEventListener("click", function (event) {
        event.preventDefault();
        hideBookDetail();
    });
    return close;
}

function renderBookDetail(book) {
    const panel = document.getElementById("book-detail");
    panel.hidden = false;
    panel.textContent = "";
    panel.append(closeLink());
    panel.append(createBookCover(book));    panel.append(el("h3", "", book.title || "Untitled"));
    panel.append(el("p", "", book.author || ""));
    panel.append(el("p", "book-price", money(book.price)));
    panel.append(el(
        "p",
        book.available ? "book-availability available" : "book-availability",
        book.available ? "Available" : "Not available"
    ));
    if (book.bookId != null) {
        panel.append(el("p", "hint", "Book ID: " + book.bookId));
    }
    if (book.isbn) {
        panel.append(el("p", "hint", "ISBN: " + book.isbn));
    }
    if (book.stock != null) {
        panel.append(el("p", "hint", "Stock: " + book.stock));
    }

    panel.append(el("h3", "", "Reviews"));
    const reviews = Array.isArray(book.reviews) ? book.reviews : [];
    if (!reviews.length) {
        panel.append(el("p", "hint", "No reviews yet."));
    } else {
        reviews.forEach(function (review) {
            panel.append(renderReview(review));
        });
    }

    if (isLoggedIn() && currentUser.role === "buyer") {
        panel.append(renderReviewForm());
    } else if (!isLoggedIn()) {
        const message = el("p", "message");
        message.id = "review-message";
        message.setAttribute("role", "status");
        panel.append(message);
        showLoginPrompt("review-message", "", "Login", " as a buyer to write a review.");
    }
    markSelectedBook();
}

function renderReview(review) {
    const block = el("div", "review");
    const name = review.userName || "Reader";
    const rating = review.rating != null ? String(review.rating) + "/5" : "";
    const heading = rating ? name + " - " + rating : name;
    block.append(el("p", "review-name", heading));
    if (review.comment) {
        block.append(el("p", "review-comment", review.comment));
    }
    return block;
}

function renderReviewForm() {
    const form = document.createElement("form");
    form.id = "review-form";

    const select = document.createElement("select");
    select.id = "review-rating";
    for (let rating = 1; rating <= 5; rating += 1) {
        const option = document.createElement("option");
        option.value = String(rating);
        option.textContent = String(rating);
        if (rating === 5) {
            option.selected = true;
        }
        select.append(option);
    }
    const ratingLabel = el("label", "field", "Rating");
    ratingLabel.append(select);

    const comment = document.createElement("textarea");
    comment.id = "review-comment";
    comment.rows = 4;
    comment.required = true;
    const commentLabel = el("label", "field", "Comment");
    commentLabel.append(comment);

    const button = el("button", "", "Submit review");
    button.type = "submit";
    const message = el("p", "message");
    message.id = "review-message";
    message.hidden = true;
    message.setAttribute("role", "status");

    form.append(ratingLabel, commentLabel, button, message);
    form.addEventListener("submit", submitReview);
    return form;
}

async function submitReview(event) {
    event.preventDefault();
    const button = event.target.querySelector("button");
    if (!isLoggedIn() || currentUser.role !== "buyer") {
        showLoginPrompt("review-message", "", "Login", " as a buyer to write a review.");
        return;
    }

    const rating = Number(document.getElementById("review-rating").value);
    const comment = document.getElementById("review-comment").value.trim();
    if (!comment || !Number.isFinite(rating) || rating < 1 || rating > 5) {
        showMessage("review-message", "Choose a rating from 1 to 5 and enter a comment.", true);
        return;
    }

    setBusy(button, true);
    try {
        await api("/api/reviews", {
            method: "POST",
            body: JSON.stringify({
                bookId: selectedBookId,
                rating: rating,
                comment: comment
            })
        });
        await openBook(selectedBookId);
        if (document.getElementById("review-message")) {
            showMessage("review-message", "Review saved.");
        } else {
            showMessage("books-message", "Review saved.");
        }
    } catch (error) {
        showMessage("review-message", error.message, true);
    } finally {
        setBusy(button, false);
    }
}

function cartLineText(item) {
    const title = item.title || "Book";
    const parts = [item.author ? title + " by " + item.author : title];
    if (item.quantity != null) {
        parts.push("Qty " + item.quantity);
    }
    if (item.subtotal != null) {
        parts.push("Subtotal " + money(item.subtotal));
    }
    return parts.join(" - ");
}

async function addToCart(bookId) {
    if (!isLoggedIn()) {
        showLoginPrompt("books-message", "", "Login", " to add books to your cart.");
        return;
    }
    try {
        await api("/api/cart/items", {
            method: "POST",
            body: JSON.stringify({ bookId: bookId, quantity: 1 })
        });
        await loadCart();
        showMessage("books-message", "Added to your cart.");
    } catch (error) {
        showMessage("books-message", error.message, true);
    }
}

async function removeFromCart(bookId) {
    if (!isLoggedIn()) {
        renderCart(null);
        return;
    }
    try {
        await api("/api/cart/items/" + encodeURIComponent(String(bookId)), {
            method: "DELETE"
        });
        await loadCart();
    } catch (error) {
        showMessage("cart-message", error.message, true);
    }
}

async function loadCart() {
    if (!isLoggedIn()) {
        renderCart(null);
        return;
    }
    try {
        const cart = await api("/api/cart");
        renderCart(cart || { items: [], total: 0 });
    } catch (error) {
        document.getElementById("cart-items").textContent = "";
        document.getElementById("cart-count").textContent = "";
        document.getElementById("checkout-form").hidden = true;
        setCartLabel(0);
        document.getElementById("cart-intro").hidden = false;
        showMessage("cart-message", error.message, true);
    }
}

function itemCount(cart) {
    const items = cart && Array.isArray(cart.items) ? cart.items : [];
    let count = 0;
    items.forEach(function (item) {
        const qty = Number(item.quantity);
        if (Number.isFinite(qty) && qty > 0) {
            count += qty;
        }
    });
    return count;
}

function setCartLabel(count) {
    const link = document.getElementById("nav-cart");
    if (!link) {
        return;
    }
    link.textContent = count > 0 ? "Cart (" + count + ")" : "Cart";
}

function renderCart(cart) {
    const list = document.getElementById("cart-items");
    const total = document.getElementById("cart-count");
    const intro = document.getElementById("cart-intro");
    const form = document.getElementById("checkout-form");
    list.textContent = "";

    if (!isLoggedIn() || !cart) {
        intro.hidden = true;
        form.hidden = true;
        total.textContent = "";
        setCartLabel(0);
        showLoginPrompt("cart-message", "", "Login", " to see your cart.");
        return;
    }

    intro.hidden = false;
    const items = Array.isArray(cart.items) ? cart.items : [];
    setCartLabel(itemCount(cart));
    const result = document.getElementById("checkout-result");
    const hasResult = result && result.children.length > 0;
    if (!items.length) {
        showMessage("cart-message", hasResult ? "" : "Your cart is empty.");
    } else {
        showMessage("cart-message", "");
    }

    items.forEach(function (item) {
        const row = el("li", "cart-line");
        row.append(el("span", "", cartLineText(item)));
        const remove = el("button", "action-button", "Remove");
        remove.type = "button";
        remove.setAttribute("aria-label", "Remove " + (item.title || "book"));
        remove.addEventListener("click", function () {
            removeFromCart(item.bookId);
        });
        row.append(remove);
        list.append(row);
    });

    total.textContent = "Cart total: " + money(cart.total);
    form.hidden = currentUser.role !== "buyer" || items.length === 0;
}

async function checkout(event) {
    event.preventDefault();
    if (!isLoggedIn()) {
        showLoginPrompt("checkout-message", "", "Login", " to place an order.");
        return;
    }
    if (checkoutBusy) {
        return;
    }

    checkoutBusy = true;
    const button = event.target.querySelector("button");
    setBusy(button, true);
    showMessage("checkout-message", "");
    try {
        const data = await api("/api/checkout", {
            method: "POST",
            body: JSON.stringify({
                paymentMethod: document.getElementById("payment-method").value
            })
        });
        renderCheckoutResult(data);
        await loadCart();
        await loadOrders();
        await loadBooks();
        if (selectedBookId != null) {
            await openBook(selectedBookId);
        }
    } catch (error) {
        showMessage("checkout-message", error.message, true);
    } finally {
        checkoutBusy = false;
        setBusy(button, false);
    }
}

function lineText(item) {
    const record = item || {};
    const title = record.title || (record.bookId != null ? "Book " + record.bookId : "Item");
    const parts = [title];
    if (record.quantity != null) {
        parts.push("Qty " + record.quantity);
    }
    if (record.subtotal != null) {
        parts.push(money(record.subtotal));
    } else if (record.unitPrice != null) {
        parts.push(money(record.unitPrice));
    }
    return parts.join(" - ");
}

function orderBuyer(order) {
    if (!order) {
        return "";
    }
    if (order.buyerName) {
        return order.buyerName;
    }
    if (order.userName) {
        return order.userName;
    }
    if (order.user && order.user.name) {
        return order.user.name;
    }
    return "";
}

function appendOrderBody(card, order, allowAdvance) {
    card.append(el("h3", "", "Order " + (order.orderId != null ? order.orderId : "")));
    if (order.status) {
        card.append(el("p", "order-status", statusLabel(order.status)));
    }
    if (order.totalAmount != null) {
        card.append(el("p", "book-price", "Total " + money(order.totalAmount)));
    }
    const when = formatWhen(order.createdAt);
    if (when) {
        card.append(el("p", "hint", when));
    }
    if (allowAdvance) {
        const who = orderBuyer(order);
        if (who) {
            card.append(el("p", "", who));
        }
    }
    if (order.payment) {
        const bits = [];
        const method = paymentLabel(order.payment.method);
        if (method) {
            bits.push(method);
        }
        if (order.payment.status) {
            bits.push(statusLabel(order.payment.status));
        }
        if (bits.length) {
            card.append(el("p", "", bits.join(" - ")));
        }
    }
    const items = Array.isArray(order.items) ? order.items : [];
    if (items.length) {
        const list = el("ul", "order-items");
        items.forEach(function (item) {
            list.append(el("li", "", lineText(item)));
        });
        card.append(list);
    }
}

function renderCheckoutResult(data) {
    const payload = data || {};
    const order = payload.order || {};
    const result = document.getElementById("checkout-result");
    result.textContent = "";
    const card = el("article", "book-card");
    appendOrderBody(card, order, false);
    const note = payload.notification && payload.notification.message;
    if (note) {
        card.append(el("p", "message", note));
    }
    result.append(card);
    showMessage("checkout-message", "");
}

function orderCard(order, allowAdvance) {
    const card = el("article", "book-card");
    appendOrderBody(card, order, allowAdvance);
    const status = String(order.status || "").trim().toLowerCase();
    if (allowAdvance && status !== "delivered") {
        const button = el("button", "", "Advance order");
        button.type = "button";
        button.setAttribute("aria-label", "Advance order " + order.orderId);
        button.addEventListener("click", function () {
            advanceOrder(order.orderId);
        });
        card.append(button);
    }
    return card;
}

function renderOrderList(target, orders, allowAdvance) {
    target.textContent = "";
    if (!orders.length) {
        target.append(el("p", "hint", allowAdvance ? "No orders yet." : "You have no orders yet."));
        return;
    }
    orders.forEach(function (order) {
        target.append(orderCard(order, allowAdvance));
    });
}

async function loadOrders() {
    const list = document.getElementById("orders-list");
    if (!isLoggedIn()) {
        list.textContent = "";
        document.getElementById("staff-tools").hidden = true;
        showLoginPrompt("orders-message", "", "Login", " to see your orders.");
        return;
    }
    if (currentUser.role === "staff") {
        document.getElementById("staff-tools").hidden = false;
        showMessage("orders-message", "");
        await loadStaffOrders();
        return;
    }
    document.getElementById("staff-tools").hidden = true;
    try {
        const data = await api("/api/orders");
        showMessage("orders-message", "");
        renderOrderList(list, listOf(data, "orders"), false);
    } catch (error) {
        list.textContent = "";
        showMessage("orders-message", error.message, true);
    }
}

async function loadStaffOrders() {
    const list = document.getElementById("orders-list");
    if (!isLoggedIn() || currentUser.role !== "staff") {
        return;
    }
    try {
        const data = await api("/api/staff/orders");
        renderOrderList(list, listOf(data, "orders"), true);
        return true;
    } catch (error) {
        list.textContent = "";
        showMessage("orders-message", error.message, true);
        return false;
    }
}

async function advanceOrder(orderId) {
    const key = String(orderId);
    if (advancingOrders[key]) {
        return;
    }
    advancingOrders[key] = true;
    try {
        const data = await api("/api/orders/" + encodeURIComponent(key) + "/advance", {
            method: "POST"
        });
        const note = data && data.notification && data.notification.message
            ? data.notification.message
            : "Order updated.";
        const reloaded = await loadStaffOrders();
        if (reloaded) {
            showMessage("orders-message", note);
        }
    } catch (error) {
        showMessage("staff-message", error.message, true);
    } finally {
        delete advancingOrders[key];
    }
}

async function addBook(event) {
    event.preventDefault();
    const button = event.target.querySelector("button");
    const price = Number(document.getElementById("add-price").value);
    const stock = Number(document.getElementById("add-stock").value);
    if (!Number.isFinite(price) || !Number.isFinite(stock) || price < 0 || stock < 0) {
        showMessage("staff-message", "Enter a valid price and stock.", true);
        return;
    }

    const body = {
        title: fieldValue("add-title"),
        author: fieldValue("add-author"),
        price: price,
        stock: stock
    };
    const isbn = fieldValue("add-isbn");
    if (isbn) {
        body.isbn = isbn;
    }

    setBusy(button, true);
    try {
        await api("/api/books", {
            method: "POST",
            body: JSON.stringify(body)
        });
        event.target.reset();
        showMessage("staff-message", "Book added.");
        bookPage = 1;
        await loadBooks();
    } catch (error) {
        showMessage("staff-message", error.message, true);
    } finally {
        setBusy(button, false);
    }
}

async function updateBook(event) {
    event.preventDefault();
    const button = event.target.querySelector("button");
    const bookId = fieldValue("update-id");
    if (!bookId) {
        showMessage("staff-message", "Enter a book id.", true);
        return;
    }

    const body = {};
    const title = fieldValue("update-title");
    const author = fieldValue("update-author");
    const isbn = fieldValue("update-isbn");
    const priceRaw = document.getElementById("update-price").value.trim();
    const stockRaw = document.getElementById("update-stock").value.trim();
    if (title) {
        body.title = title;
    }
    if (author) {
        body.author = author;
    }
    if (isbn) {
        body.isbn = isbn;
    }
    if (priceRaw !== "") {
        const price = Number(priceRaw);
        if (!Number.isFinite(price) || price < 0) {
            showMessage("staff-message", "Enter a valid price.", true);
            return;
        }
        body.price = price;
    }
    if (stockRaw !== "") {
        const stock = Number(stockRaw);
        if (!Number.isFinite(stock) || stock < 0) {
            showMessage("staff-message", "Enter a valid stock.", true);
            return;
        }
        body.stock = stock;
    }
    if (!Object.keys(body).length) {
        showMessage("staff-message", "Enter at least one field to update.", true);
        return;
    }

    setBusy(button, true);
    try {
        await api("/api/books/" + encodeURIComponent(bookId), {
            method: "PUT",
            body: JSON.stringify(body)
        });
        showMessage("staff-message", "Book updated.");
        await loadBooks();
        if (selectedBookId != null && String(selectedBookId) === String(bookId)) {
            await openBook(bookId);
        }
    } catch (error) {
        showMessage("staff-message", error.message, true);
    } finally {
        setBusy(button, false);
    }
}

function viewFromHash() {
    const hash = (location.hash || "").replace(/^#/, "");
    if (hash === "checkout") {
        return "cart";
    }
    if (hash === "staff") {
        return "orders";
    }
    if (hash === "books" || hash === "cart" || hash === "login" || hash === "orders") {
        return hash;
    }
    return "books";
}

function showView(name, updateHash) {
    let view = name;
    if (view === "checkout") {
        view = "cart";
    }
    if (view === "staff") {
        view = "orders";
    }
    const known = { books: true, cart: true, login: true, orders: true };
    if (!known[view]) {
        view = "books";
    }
    if (view === "login" && isLoggedIn()) {
        view = "books";
    }

    document.querySelectorAll("main [data-view]").forEach(function (section) {
        section.hidden = section.getAttribute("data-view") !== view;
    });
    document.querySelectorAll("[data-nav]").forEach(function (link) {
        const on = link.getAttribute("data-nav") === view;
        link.classList.toggle("active", on);
        if (on) {
            link.setAttribute("aria-current", "page");
        } else {
            link.removeAttribute("aria-current");
        }
    });

    activeView = view;
    if (updateHash !== false) {
        const next = "#" + view;
        if (location.hash !== next) {
            history.replaceState(null, "", next);
        }
    }
    window.scrollTo(0, 0);
}

function onNavClick(event) {
    if (event.defaultPrevented) {
        return;
    }
    const target = event.target;
    const link = target && target.closest ? target.closest("a") : null;
    if (!link) {
        return;
    }
    const href = link.getAttribute("href") || "";
    if (href.charAt(0) !== "#") {
        return;
    }
    const id = href.slice(1);
    if (id !== "books" && id !== "cart" && id !== "login" && id !== "orders" && id !== "checkout" && id !== "staff") {
        return;
    }
    event.preventDefault();
    showView(id);
}

function bindEvents() {
    document.getElementById("search-form").addEventListener("submit", searchBooks);
    document.getElementById("books-prev").addEventListener("click", showPreviousPage);
    document.getElementById("books-next").addEventListener("click", showNextPage);
    document.getElementById("login-form").addEventListener("submit", login);
    document.getElementById("register-form").addEventListener("submit", register);
    document.getElementById("register-role").addEventListener("change", toggleRegisterFields);
    document.getElementById("logout-button").addEventListener("click", logout);
    document.getElementById("checkout-form").addEventListener("submit", checkout);
    document.getElementById("add-book-form").addEventListener("submit", addBook);
    document.getElementById("update-book-form").addEventListener("submit", updateBook);
    document.addEventListener("click", onNavClick);
    window.addEventListener("hashchange", function () {
        showView(viewFromHash(), false);
    });
}

async function start() {
    const booksPromise = loadBooks();
    if (getToken()) {
        await loadMe();
    }
    await booksPromise;
}

function init() {
    bindEvents();
    toggleRegisterFields();
    const opening = viewFromHash();
    if (getToken() && opening === "login") {
        showView("books", false);
    } else {
        showView(opening);
    }
    if (getToken()) {
        sessionPending = true;
        showMessage("cart-message", "Loading your cart...");
        showMessage("orders-message", "Loading your orders...");
    } else {
        renderCart(null);
        loadOrders();
    }
    renderSession();
    start();
}

init();
