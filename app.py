import os
import pandas as pd
from flask import Flask, render_template, request, redirect,url_for
import mysql.connector
from flask_mail import Mail, Message





app = Flask(__name__)


mail = Mail(app)
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


app.config['MAIL_SERVER'] = 'smtp.gmail.com'  # Use your email provider's SMTP server
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = '220701159@rajalakshmi.edu.in'
app.config['MAIL_PASSWORD'] = ''  # Use app password if using Gmail
app.config['MAIL_DEFAULT_SENDER'] = ''

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

    searched_product = []
    if search_query:
        cursor.execute("SELECT * FROM products WHERE LOWER(name) LIKE LOWER(%s)", (f"%{search_query}%",))
        searched_product = cursor.fetchall()

    # Fetch all products only if no search is performed
    products = []
    low_stock = []
    if not searched_product:
        cursor.execute("SELECT * FROM products")
        products = cursor.fetchall()

        cursor.execute("SELECT name, stock_level FROM products WHERE stock_level < threshold")
        low_stock = cursor.fetchall()

    conn.close()
    
    return render_template(
        "index.html",
        products=products,
        low_stock=low_stock,
        searched_product=searched_product,
        search_query=search_query
    )




@app.route("/add_product", methods=["POST"])
def add_product():
    name = request.form["name"]
    stock_level = request.form["stock_level"]
    threshold = request.form["threshold"]

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO products (name, stock_level, threshold) VALUES (%s, %s, %s)",
        (name, stock_level, threshold)
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

        # Try updating existing stock
        cursor.execute(
            "UPDATE products SET stock_level = stock_level + %s WHERE TRIM(name) = TRIM(%s)",
            (stock_level, name)
        )

        # If no row was updated, insert as a new product
        if cursor.rowcount == 0:
            cursor.execute(
                "INSERT INTO products (name, stock_level, threshold) VALUES (%s, %s, %s)",
                (name, stock_level, threshold)
            )
            print(f"Inserted new product: {name} -> {stock_level}")

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
        name = row["Product Name"].strip()
        sold_quantity = int(row["Sold Quantity"])

        cursor.execute(
            "UPDATE products SET stock_level = stock_level - %s WHERE LOWER(TRIM(name)) = LOWER(TRIM(%s))",
            (sold_quantity, name)
        )
        cursor.execute("SELECT stock_level, threshold FROM products WHERE LOWER(TRIM(name)) = LOWER(TRIM(%s))", (name,))
        result = cursor.fetchone()

        if result and result[0] < result[1]:  # stock_level < threshold
            subject = f"⚠️ Low Stock Alert: {name}"
            body = f"Stock for {name} is low! Only {result[0]} left."

            msg = Message(subject, recipients=["manikandan101004@gmail.com"], body=body)
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
        threshold = int(row["Threshold"]) if "Threshold" in row else 10  # Default threshold

        # Insert new product (ignores duplicates)
        cursor.execute(
            "INSERT IGNORE INTO products (name, stock_level, threshold) VALUES (%s, %s, %s)",
            (name, stock_level, threshold)
        )
        print(f"Inserted: {name} -> {stock_level}")

    conn.commit()
    conn.close()

    return redirect("/")




if __name__ == "__main__":
    app.run(debug=True)
