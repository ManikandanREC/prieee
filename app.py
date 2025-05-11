import os
import pandas as pd
from flask import Flask, render_template, request, redirect,url_for,flash
import mysql.connector
from flask_mail import Mail, Message
from datetime import datetime, timedelta,date
from openpyxl import load_workbook




app = Flask(__name__)



UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


app.config['MAIL_SERVER'] = 'smtp.gmail.com'  # Use your email provider's SMTP server
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'manikandan101004@gmail.com'
app.config['MAIL_PASSWORD'] = 'skry ugup ouaz cgzu'  # Use app password if using Gmail
app.config['MAIL_DEFAULT_SENDER'] = 'manikandan101004@gmail.com'
mail = Mail(app)
# Database connection
def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="host",
        password="root",
        database="stock_manager"
    )

@app.route("/", methods=["GET"])
def dashboard():
    search_query = request.args.get("search", "").strip()
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Always fetch products with days_left
    cursor.execute("SELECT *, DATEDIFF(expiry_date, CURDATE()) AS days_left FROM products")
    all_products = cursor.fetchall()

    products = []
    low_stock = []
    searched_product = []

    for p in all_products:
        p["discounted"] = p["days_left"] is not None and p["days_left"] <= 7
        products.append(p)

    if search_query:
        searched_product = [p for p in products if search_query.lower() in p["name"].lower()]
    else:
        cursor.execute("SELECT name, stock_level FROM products WHERE stock_level < threshold")
        low_stock = cursor.fetchall()

    conn.close()

    return render_template(
        "index.html",
        products=products,
        low_stock=low_stock,
        searched_product=searched_product,
        search_query=search_query,
        current_date=date.today()
    )



@app.route("/add_product", methods=["POST"])
def add_product():
    name = request.form["name"]
    stock_level = request.form["stock_level"]
    threshold = request.form["threshold"]
    price = request.form["price"]
    expiry_date = request.form["expiry_date"]  # format: yyyy-mm-dd

    # Apply discount if expiry is within 7 days
    expiry_obj = datetime.strptime(expiry_date, "%Y-%m-%d")
    today = datetime.now()
    if expiry_obj <= today + timedelta(days=7):
        price = round(float(price) * 0.7, 2)  # 30% discount

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO products (name, stock_level, threshold, price, expiry_date) VALUES (%s, %s, %s, %s, %s)",
        (name, stock_level, threshold, price, expiry_date)
    )
    conn.commit()
    conn.close()
    return redirect("/")

@app.route("/upload_excel", methods=["POST"])
def upload_excel():
    file = request.files["file"]
    file_path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(file_path)

    df = pd.read_excel(file_path)

    conn = get_db_connection()
    cursor = conn.cursor()

    for _, row in df.iterrows():
        name = row["Product Name"].strip()
        stock_level = int(row["Stock Level"])
        threshold = int(row["Threshold"]) if "Threshold" in row else 10  # Default threshold
        price = float(row["Price"]) if "Price" in row else 0.0  # Default to 0.0 if not provided
        expiry_date = row["Expiry Date"].strftime('%Y-%m-%d') if "Expiry Date" in row else None

        # Try updating existing stock along with price and expiry date
        cursor.execute(
            """
            UPDATE products 
            SET stock_level = stock_level + %s, price = %s, expiry_date = %s 
            WHERE TRIM(name) = TRIM(%s)
            """,
            (stock_level, price, expiry_date, name)
        )

        # If no row was updated, insert as a new product
        if cursor.rowcount == 0:
            cursor.execute(
                """
                INSERT INTO products (name, stock_level, threshold, price, expiry_date) 
                VALUES (%s, %s, %s, %s, %s)
                """,
                (name, stock_level, threshold, price, expiry_date)
            )
            print(f"Inserted new product: {name} -> {stock_level}, {price}, {expiry_date}")

    conn.commit()
    conn.close()

    return redirect("/")

def send_email(subject, recipient, body):
    msg = Message(subject, recipients=[recipient], body=body)
    mail.send(msg)

@app.route("/upload_sales", methods=["POST"])
def upload_sales():
    if "file" not in request.files:
        return "No file part"

    file = request.files["file"]
    if file.filename == "":
        return "No selected file"

    df = pd.read_excel(file)

    conn = mysql.connector.connect(
        host="localhost", user="host", password="root", database="stock_manager"
    )
    cursor = conn.cursor()

    for _, row in df.iterrows():
        print("Processing row:", row.to_dict())

        name = row["Product Name"].strip()
        sold_quantity = int(row["Sold Quantity"])

        cursor.execute(
            "UPDATE products SET stock_level = stock_level - %s WHERE LOWER(TRIM(name)) = LOWER(TRIM(%s))",
            (sold_quantity, name)
        )
        cursor.execute("SELECT stock_level, threshold FROM products WHERE LOWER(TRIM(name)) = LOWER(TRIM(%s))", (name,))
        result = cursor.fetchone()
        if result:
            print(f"{name}: Stock={result[0]}, Threshold={result[1]}")
        else:
            print(f"{name} not found!")

        if result and result[0] < result[1]:  # stock_level < threshold
            subject = f"⚠️ Low Stock Alert: {name}"
            body = f"Stock for {name} is low! Only {result[0]} left."

            msg = Message(subject, recipients=["220701159@rajalakshmi.edu.in"], body=body)
            mail.send(msg)

    conn.commit()
    conn.close()

    return redirect(url_for("dashboard"))

@app.route("/delete_product/<int:product_id>", methods=["POST"])
def delete_product(product_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM products WHERE id = %s", (product_id,))
    conn.commit()
    conn.close()
    return redirect("/")
@app.route("/upload_page")
def upload_page():
    return render_template("upload.html")

@app.route("/upload_new_products", methods=["POST"])
def upload_new_products():
    file = request.files["file"]
    file_path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(file_path)

    df = pd.read_excel(file_path)

    conn = get_db_connection()
    cursor = conn.cursor()

    for _, row in df.iterrows():
        name = row["Product Name"].strip()
        stock_level = int(row["Stock Level"])
        threshold = int(row["Threshold"]) if "Threshold" in row else 10
        price = float(row["Price"]) if "Price" in row else 0.0
        expiry_date = row["Expiry Date"] if "Expiry Date" in row else None

        # Apply 30% discount if expiry within 7 days
        if expiry_date:
            try:
                expiry_obj = pd.to_datetime(expiry_date)
                if expiry_obj <= datetime.now() + timedelta(days=7):
                    price = round(price * 0.7, 2)
            except:
                expiry_date = None  # fallback if invalid

        cursor.execute(
            "INSERT IGNORE INTO products (name, stock_level, threshold, price, expiry_date) VALUES (%s, %s, %s, %s, %s)",
            (name, stock_level, threshold, price, expiry_date)
        )
        print(f"Inserted: {name} -> {stock_level}, Price: {price}, Expiry: {expiry_date}")

    conn.commit()
    conn.close()

    return redirect("/")

def send_initial_low_stock_alerts():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT name, stock_level, threshold FROM products WHERE stock_level < threshold")
    low_stock_products = cursor.fetchall()
    conn.close()

    for product in low_stock_products:
        subject = f"⚠️ Low Stock Alert: {product['name']}"
        body = f"Stock for {product['name']} is low! Only {product['stock_level']} left."
        print(f"Sending alert: {body}")
        send_email(subject, "220701159@rajalakshmi.edu.in", body)

# Wrap the email sending in the app context
with app.app_context():
    send_initial_low_stock_alerts()



@app.route("/purchase/<int:product_id>", methods=["GET"])
def purchase_page(product_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Get the selected product
    cursor.execute("SELECT * FROM products WHERE id = %s", (product_id,))
    product = cursor.fetchone()
    if not product:
        conn.close()
        return "Product not found", 404

    # Products close to expiry (<= 7 days)
    cursor.execute("""
        SELECT * FROM products 
        WHERE DATEDIFF(expiry_date, CURDATE()) <= 7 AND id != %s
    """, (product_id,))
    expiring_soon = cursor.fetchall()

    # Suggestions based on starting letter (excluding the current product)
    start_letter = product["name"][0]
    cursor.execute("""
        SELECT * FROM products 
        WHERE name LIKE %s AND id != %s
    """, (f"{start_letter}%", product_id))
    suggestions = cursor.fetchall()

    conn.close()

    return render_template(
        "purchase.html",
        product=product,
        expiring_soon=expiring_soon,
        suggestions=suggestions
    )


# Handle the actual purchase
@app.route("/process_purchase/<int:product_id>", methods=["POST"])
def process_purchase(product_id):
    quantity = int(request.form["quantity"])

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE products SET stock_level = stock_level - %s WHERE id = %s AND stock_level >= %s",
                   (quantity, product_id, quantity))
    conn.commit()
    conn.close()

    return redirect("/")






if __name__ == "__main__":
    app.run(debug=True)
