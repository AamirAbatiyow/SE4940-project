
let cart = [];

function addToCart(bookTitle) {
    cart.push(bookTitle);

    displayCart();

    alert(bookTitle + " has been added to your cart!");
}

function displayCart() {
    let cartItems = document.getElementById("cart-items");
    let cartCount = document.getElementById("cart-count");

    cartItems.innerHTML = "";

    cart.forEach(function(book) {
        let listItem = document.createElement("li");

        listItem.textContent = book;

        cartItems.appendChild(listItem);
    });

    cartCount.textContent = "Total items: " + cart.length;
}
