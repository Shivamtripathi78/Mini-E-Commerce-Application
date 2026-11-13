from flask import (
    Flask, render_template, request,
    redirect, url_for, session, flash
)
import sqlite3
from pathlib import Path
import secrets

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)

DATABASE = Path(__file__).parent / "data" / "shop.db"


# ---------------- DATABASE ----------------

def get_db():
    DATABASE.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")

    return connection


def initialize_database():

    with get_db() as connection:

        connection.executescript("""

        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            category TEXT,
            price REAL NOT NULL,
            image TEXT
        );

        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT NOT NULL,
            email TEXT NOT NULL,
            address TEXT NOT NULL,
            total REAL NOT NULL,
            order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            product_name TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            price REAL NOT NULL,

            FOREIGN KEY (order_id)
                REFERENCES orders(id),

            FOREIGN KEY (product_id)
                REFERENCES products(id)
        );

        """)

        count = connection.execute(
            "SELECT COUNT(*) FROM products"
        ).fetchone()[0]

        if count == 0:

            products = [

                (
                    "Wireless Headphones",
                    "High-quality wireless headphones with clear sound.",
                    "Electronics",
                    1999,
                    "https://placehold.co/400x300/161b22/58a6ff?text=Headphones"
                ),

                (
                    "Smart Watch",
                    "Smartwatch with fitness tracking and notifications.",
                    "Electronics",
                    2999,
                    "https://placehold.co/400x300/161b22/58a6ff?text=Smart+Watch"
                ),

                (
                    "Mechanical Keyboard",
                    "Premium mechanical keyboard for productivity and gaming.",
                    "Accessories",
                    2499,
                    "https://placehold.co/400x300/161b22/58a6ff?text=Keyboard"
                ),

                (
                    "Wireless Mouse",
                    "Ergonomic wireless mouse with precise tracking.",
                    "Accessories",
                    899,
                    "https://placehold.co/400x300/161b22/58a6ff?text=Mouse"
                ),

                (
                    "Laptop Backpack",
                    "Durable backpack with dedicated laptop storage.",
                    "Fashion",
                    1499,
                    "https://placehold.co/400x300/161b22/58a6ff?text=Backpack"
                ),

                (
                    "Running Shoes",
                    "Comfortable lightweight shoes for everyday running.",
                    "Fashion",
                    2199,
                    "https://placehold.co/400x300/161b22/58a6ff?text=Shoes"
                ),

                (
                    "Desk Lamp",
                    "Modern LED desk lamp for your workspace.",
                    "Home",
                    799,
                    "https://placehold.co/400x300/161b22/58a6ff?text=Desk+Lamp"
                ),

                (
                    "Water Bottle",
                    "Reusable stainless steel water bottle.",
                    "Home",
                    499,
                    "https://placehold.co/400x300/161b22/58a6ff?text=Bottle"
                )

            ]

            connection.executemany("""
                INSERT INTO products
                (name, description, category, price, image)
                VALUES (?, ?, ?, ?, ?)
            """, products)


# ---------------- PRODUCT HELPERS ----------------

def get_product(product_id):

    with get_db() as connection:

        return connection.execute(
            "SELECT * FROM products WHERE id = ?",
            (product_id,)
        ).fetchone()


def get_cart_items():

    cart = session.get("cart", {})
    items = []
    total = 0

    for product_id, quantity in cart.items():

        product = get_product(int(product_id))

        if product is None:
            continue

        subtotal = product["price"] * quantity

        items.append({
            "id": product["id"],
            "name": product["name"],
            "price": product["price"],
            "image": product["image"],
            "quantity": quantity,
            "subtotal": subtotal
        })

        total += subtotal

    return items, total


# ---------------- HOME ----------------

@app.route("/")
def home():

    search = request.args.get("search", "").strip()
    category = request.args.get("category", "").strip()

    query = "SELECT * FROM products WHERE 1=1"
    parameters = []

    if search:
        query += " AND (name LIKE ? OR description LIKE ?)"
        parameters.extend([
            f"%{search}%",
            f"%{search}%"
        ])

    if category:
        query += " AND category = ?"
        parameters.append(category)

    query += " ORDER BY id"

    with get_db() as connection:

        products = connection.execute(
            query,
            parameters
        ).fetchall()

        categories = connection.execute(
            "SELECT DISTINCT category FROM products ORDER BY category"
        ).fetchall()

    cart_count = sum(session.get("cart", {}).values())

    return render_template(
        "index.html",
        products=products,
        categories=categories,
        selected_category=category,
        search=search,
        cart_count=cart_count
    )


# ---------------- ADD TO CART ----------------

@app.route("/add-to-cart/<int:product_id>", methods=["POST"])
def add_to_cart(product_id):

    product = get_product(product_id)

    if product is None:
        flash("Product not found.", "error")
        return redirect(url_for("home"))

    cart = session.get("cart", {})

    key = str(product_id)

    cart[key] = cart.get(key, 0) + 1

    session["cart"] = cart

    flash(f"{product['name']} added to cart!", "success")

    return redirect(request.referrer or url_for("home"))


# ---------------- VIEW CART ----------------

@app.route("/cart")
def cart():

    items, total = get_cart_items()

    return render_template(
        "cart.html",
        items=items,
        total=total
    )


# ---------------- UPDATE CART ----------------

@app.route("/update-cart/<int:product_id>", methods=["POST"])
def update_cart(product_id):

    quantity = request.form.get("quantity", type=int)

    cart = session.get("cart", {})
    key = str(product_id)

    if key not in cart:
        return redirect(url_for("cart"))

    if quantity is None or quantity < 1:
        cart.pop(key, None)

    elif quantity > 99:
        flash("Maximum quantity allowed is 99.", "error")

    else:
        cart[key] = quantity

    session["cart"] = cart

    return redirect(url_for("cart"))


# ---------------- REMOVE FROM CART ----------------

@app.route("/remove-from-cart/<int:product_id>", methods=["POST"])
def remove_from_cart(product_id):

    cart = session.get("cart", {})

    cart.pop(str(product_id), None)

    session["cart"] = cart

    flash("Product removed from cart.", "success")

    return redirect(url_for("cart"))


# ---------------- CHECKOUT ----------------

@app.route("/checkout", methods=["GET", "POST"])
def checkout():

    items, total = get_cart_items()

    if not items:
        flash("Your cart is empty.", "error")
        return redirect(url_for("home"))

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        address = request.form.get("address", "").strip()

        if not name or not email or not address:
            flash("Please complete all checkout fields.", "error")

            return render_template(
                "checkout.html",
                items=items,
                total=total
            )

        if len(name) > 100 or len(email) > 254 or len(address) > 500:
            flash("Please check the length of your details.", "error")

            return render_template(
                "checkout.html",
                items=items,
                total=total
            )

        if "@" not in email or "." not in email.split("@")[-1]:
            flash("Please enter a valid email address.", "error")

            return render_template(
                "checkout.html",
                items=items,
                total=total
            )

        with get_db() as connection:

            cursor = connection.execute("""
                INSERT INTO orders
                (customer_name, email, address, total)
                VALUES (?, ?, ?, ?)
            """, (name, email, address, total))

            order_id = cursor.lastrowid

            for item in items:

                connection.execute("""
                    INSERT INTO order_items
                    (order_id, product_id, product_name, quantity, price)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    order_id,
                    item["id"],
                    item["name"],
                    item["quantity"],
                    item["price"]
                ))

        session["cart"] = {}

        return redirect(
            url_for("order_success", order_id=order_id)
        )

    return render_template(
        "checkout.html",
        items=items,
        total=total
    )


# ---------------- ORDER SUCCESS ----------------

@app.route("/order-success/<int:order_id>")
def order_success(order_id):

    with get_db() as connection:

        order = connection.execute(
            "SELECT * FROM orders WHERE id = ?",
            (order_id,)
        ).fetchone()

    if order is None:
        return redirect(url_for("home"))

    return render_template(
        "orders.html",
        success_order=order,
        history=None
    )


# ---------------- ORDER HISTORY ----------------

@app.route("/orders")
def order_history():

    with get_db() as connection:

        orders = connection.execute("""
            SELECT * FROM orders
            ORDER BY order_date DESC
        """).fetchall()

    return render_template(
        "orders.html",
        success_order=None,
        history=orders
    )


# ---------------- RUN APPLICATION ----------------

if __name__ == "__main__":

    initialize_database()

    app.run(debug=True, port=5000)