from flask import Flask, render_template, request, redirect, session
import sqlite3
import random
from datetime import datetime
import os
import uuid
import hashlib
from flask import jsonify
import time
import json
import razorpay
from razorpay.errors import SignatureVerificationError
from flask import Response
import sqlite3
import csv
from io import StringIO

app = Flask(__name__)
app.secret_key = "secret123"



BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database.db")



def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn



# ---------------- AUTH PAGE ----------------
@app.route("/")
def home():
    return render_template("auth.html")


# ---------------- REGISTER ----------------
@app.route("/register", methods=["POST"])
def register():
    name = request.form["name"]
    email = request.form["email"]
    password = request.form["password"]
    phone = request.form["phone"]
    address = request.form["address"]
    aadhaar = request.form["aadhaar"]

    conn = get_db_connection()

    existing = conn.execute(
        "SELECT * FROM users WHERE email=?",
        (email,)
    ).fetchone()

    if existing:
        conn.close()
        return render_template("auth.html", register_error="Email already registered")

    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    role = "admin" if email.endswith("@ngo.com") else "user"

    conn.execute("""
INSERT INTO users 
(name, email, password, role, created_at, phone, address, aadhaar)
VALUES (?, ?, ?, ?, ?, ?, ?, ?)
""", (
    name,
    email,
    password,
    role,
    created_at,
    phone,
    address,
    aadhaar
))



    conn.commit()
    conn.close()

    return render_template("register_success.html")

# ---------------- LOGIN ----------------
@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "GET":
        return render_template("login.html")

    email = request.form["email"]
    password = request.form["password"]

    conn = get_db_connection()
    user = conn.execute(
        "SELECT * FROM users WHERE email=? AND password=?",
        (email, password)
    ).fetchone()
    conn.close()

    if user:
        session["user_id"] = user["id"]
        session["role"] = user["role"]

        # log login
        conn = get_db_connection()
        conn.execute(
            "INSERT INTO login_logs (user_id) VALUES (?)",
            (user["id"],)
        )
        conn.commit()
        conn.close()

        if user["role"] == "admin":
            return redirect("/admin")
        else:
            return redirect("/dashboard")

    return render_template("login.html", error="Invalid email or password")

@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form["email"]

        conn = get_db_connection()
        user = conn.execute(
            "SELECT * FROM users WHERE email=?",
            (email,)
        ).fetchone()
        conn.close()

        if not user:
            return render_template(
                "forgot_password.html",
                error="Email not registered"
            )

        # Generate OTP (mock)
        otp = random.randint(100000, 999999)

        session["reset_otp"] = otp
        session["reset_email"] = email

        return render_template(
            "verify_otp.html",
            otp=otp   # MOCK OTP shown
        )

    return render_template("forgot_password.html")

@app.route("/verify-otp", methods=["POST"])
def verify_otp():
    entered_otp = request.form["otp"]

    if "reset_otp" not in session:
        return redirect("/forgot-password")

    if entered_otp == str(session["reset_otp"]):
        return redirect("/reset-password")

    return render_template(
        "verify_otp.html",
        error="Invalid OTP",
        otp=session["reset_otp"]
    )

@app.route("/reset-password", methods=["GET", "POST"])
def reset_password():
    if "reset_email" not in session:
        return redirect("/")

    if request.method == "POST":
        new_password = request.form["password"]

        conn = get_db_connection()
        conn.execute(
            "UPDATE users SET password=? WHERE email=?",
            (new_password, session["reset_email"])
        )
        conn.commit()
        conn.close()

        # Clear OTP session
        session.pop("reset_otp", None)
        session.pop("reset_email", None)

        return redirect("/")

    return render_template("reset_password.html")


# ---------------- USER DASHBOARD ----------------
@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect("/")

    conn = get_db_connection()
    user = conn.execute(
        "SELECT * FROM users WHERE id=?",
        (session["user_id"],)
    ).fetchone()
    conn.close()

    return render_template("dashboard.html", user=user)
#######################################################################################################

RAZORPAY_KEY_ID = "rzp_test_S4S7C7ryb9WlU6"
RAZORPAY_KEY_SECRET = "uopveSGkMmvNF7Q6CF8JyWqO"

razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))


@app.route("/create_order")
def create_order():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    amount = request.args.get("amount")
    if not amount:
        return jsonify({"error": "Amount required"}), 400

    # Fetch user details
    conn = get_db_connection()
    user = conn.execute(
        "SELECT * FROM users WHERE id=?",
        (session["user_id"],)
    ).fetchone()
    conn.close()

    try:
        # Convert amount to paise (Razorpay uses smallest currency unit)
        # For INR: ₹100 = 10000 paise
        amount_in_paise = int(float(amount) * 100)

        # Create Razorpay order
        razorpay_order = razorpay_client.order.create({
            "amount": amount_in_paise,
            "currency": "INR",
            "receipt": f"receipt_{int(time.time())}",
            "notes": {
                "user_id": session["user_id"],
                "user_email": user["email"]
            }
        })

        print("="*50)
        print("RAZORPAY ORDER CREATION")
        print("="*50)
        print(f"Order ID: {razorpay_order['id']}")
        print(f"Amount: {amount_in_paise} paise (₹{amount})")
        print(f"Currency: INR")
        print(f"Status: {razorpay_order['status']}")
        print("="*50)

        response_data = {
            "key_id": RAZORPAY_KEY_ID,
            "order_id": razorpay_order["id"],
            "amount": amount_in_paise,
            "currency": "INR",
            "name": user["name"] or "Guest User",
            "email": user["email"],
            "phone": user["phone"] or "",
            "address": user["address"] or ""
        }

        print("Response JSON:")
        print(json.dumps(response_data, indent=2))
        print("="*50)

        return jsonify(response_data)

    except Exception as e:
        print(f"Error creating Razorpay order: {str(e)}")
        return jsonify({"error": "Failed to create order"}), 500


@app.route("/payment_success", methods=["POST"])
def payment_success():
    if "user_id" not in session:
        return jsonify({"success": False, "error": "Unauthorized"}), 401

    try:
        data = request.get_json()
        
        razorpay_payment_id = data.get("razorpay_payment_id")
        razorpay_order_id = data.get("razorpay_order_id")
        razorpay_signature = data.get("razorpay_signature")
        amount = data.get("amount")

        print("="*50)
        print("RAZORPAY PAYMENT VERIFICATION")
        print("="*50)
        print(f"Payment ID: {razorpay_payment_id}")
        print(f"Order ID: {razorpay_order_id}")
        print("="*50)

        # Verify payment signature
        params_dict = {
            'razorpay_order_id': razorpay_order_id,
            'razorpay_payment_id': razorpay_payment_id,
            'razorpay_signature': razorpay_signature
        }

        try:
            razorpay_client.utility.verify_payment_signature(params_dict)
            print("✅ Payment signature verified successfully")

            # Convert amount back from paise to rupees
            amount_in_rupees = float(amount) / 100

            # Save donation as SUCCESS
            conn = get_db_connection()
            conn.execute("""
                INSERT INTO donations (user_id, amount, status)
                VALUES (?, ?, ?)
            """, (session["user_id"], amount_in_rupees, "success"))
            conn.commit()
            conn.close()

            return jsonify({"success": True})

        except SignatureVerificationError as e:
            print(f" Signature verification failed: {str(e)}")
            
            # Save donation as FAILED
            conn = get_db_connection()
            conn.execute("""
                INSERT INTO donations (user_id, amount, status)
                VALUES (?, ?, ?)
            """, (session["user_id"], float(amount) / 100, "failed"))
            conn.commit()
            conn.close()

            return jsonify({"success": False, "error": "Invalid signature"}), 400

    except Exception as e:
        print(f"Error processing payment: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/payment_failed", methods=["POST"])
def payment_failed():
    if "user_id" not in session:
        return jsonify({"success": False, "error": "Unauthorized"}), 401

    try:
        data = request.get_json()
        amount = data.get("amount")

        # Convert amount back from paise to rupees
        amount_in_rupees = float(amount) / 100

        print("="*50)
        print("PAYMENT FAILED/CANCELLED")
        print("="*50)
        print(f"Amount: ₹{amount_in_rupees}")
        print("="*50)

        # Save donation as FAILED
        conn = get_db_connection()
        conn.execute("""
            INSERT INTO donations (user_id, amount, status)
            VALUES (?, ?, ?)
        """, (session["user_id"], amount_in_rupees, "failed"))
        conn.commit()
        conn.close()

        return jsonify({"success": True})

    except Exception as e:
        print(f"Error recording failed payment: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/payment_cancel")
def payment_cancel():
    return redirect("/dashboard")


# Optional: Razorpay webhook for server-side notifications
@app.route("/payment_webhook", methods=["POST"])
def payment_webhook():
    webhook_secret = "your_webhook_secret"  # Set in Razorpay Dashboard
    webhook_signature = request.headers.get("X-Razorpay-Signature")
    webhook_body = request.get_data()

    try:
        razorpay_client.utility.verify_webhook_signature(
            webhook_body.decode('utf-8'),
            webhook_signature,
            webhook_secret
        )

        data = request.get_json()
        event = data.get("event")

        print("="*50)
        print("RAZORPAY WEBHOOK RECEIVED")
        print("="*50)
        print(f"Event: {event}")
        print(json.dumps(data, indent=2))
        print("="*50)

        # Handle different events
        if event == "payment.captured":
            payment = data.get("payload", {}).get("payment", {}).get("entity", {})
            # Process successful payment
            print("✅ Payment captured successfully")
        elif event == "payment.failed":
            payment = data.get("payload", {}).get("payment", {}).get("entity", {})
            # Process failed payment
            print(" Payment failed")

        return jsonify({"status": "ok"}), 200

    except SignatureVerificationError:
        print(" Webhook signature verification failed")
        return jsonify({"status": "invalid signature"}), 400

# ---------------- DONATE ----------------
@app.route("/donate", methods=["POST"])
def donate():
    if "user_id" not in session:
        return redirect("/")

    amount = request.form["amount"]
    status = random.choice(["success", "pending", "failed"])

    conn = get_db_connection()
    conn.execute("""
        INSERT INTO donations (user_id, amount, status)
        VALUES (?, ?, ?)
    """, (session["user_id"], amount, status))
    conn.commit()
    conn.close()

    return redirect("/history")


# ---------------- DONATION HISTORY ----------------
@app.route("/history")
def history():
    if "user_id" not in session:
        return redirect("/")

    conn = get_db_connection()
    donations = conn.execute("""
        SELECT * FROM donations
        WHERE user_id=?
        ORDER BY created_at DESC
    """, (session["user_id"],)).fetchall()
    conn.close()

    return render_template("history.html", donations=donations)

# ---------------- ADMIN DASHBOARD ----------------
@app.route("/admin")
def admin():
    if "role" not in session or session["role"] != "admin":
        return redirect("/")

    conn = get_db_connection()

    total_users = conn.execute(
        "SELECT COUNT(*) FROM users"
    ).fetchone()[0]

    today_users = conn.execute(
        "SELECT COUNT(*) FROM users WHERE DATE(created_at)=DATE('now')"
    ).fetchone()[0]

    users = conn.execute(
        "SELECT * FROM users ORDER BY created_at DESC"
    ).fetchall()

    conn.close()

    return render_template(
        "admin.html",
        total_users=total_users,
        today_users=today_users,
        users=users
    )

@app.route("/admin/users")
def admin_users():
    if "role" not in session or session["role"] != "admin":
        return redirect("/")

    search = request.args.get("search", "")

    conn = get_db_connection()

    # ✅ Total registrations (ONLY users)
    total_users = conn.execute(
        "SELECT COUNT(*) FROM users WHERE role = 'user'"
    ).fetchone()[0]

    # ✅ Today's registrations (ONLY users)
    today_users = conn.execute(
        """
        SELECT COUNT(*) FROM users
        WHERE role = 'user'
        AND DATE(created_at) = DATE('now')
        """
    ).fetchone()[0]

    #  User list with search (EXCLUDE admin)
    users = conn.execute("""
        SELECT id, name, email, phone, address, aadhaar, DATE(created_at) as date
        FROM users
        WHERE role = 'user'
        AND (
            name LIKE ?
            OR email LIKE ?
            OR phone LIKE ?
        )
        ORDER BY created_at DESC
    """, (
        f"%{search}%",
        f"%{search}%",
        f"%{search}%"
    )).fetchall()

    conn.close()

    return render_template(
        "admin_users.html",
        total_users=total_users,
        today_users=today_users,
        users=users,
        search=search
    )


@app.route("/admin/donations")
def admin_donations():
    if "role" not in session or session["role"] != "admin":
        return redirect("/")

    search = request.args.get("search", "")

    conn = get_db_connection()

    # Total donations
    total_donations = conn.execute(
        "SELECT COUNT(*) FROM donations"
    ).fetchone()[0]

    # Today's donations - FIXED: changed timestamp to created_at
    today_donations = conn.execute(
        "SELECT COUNT(*) FROM donations WHERE DATE(created_at)=DATE('now')"
    ).fetchone()[0]

    # Total successful donation amount
    total_amount = conn.execute(
        "SELECT COALESCE(SUM(amount),0) FROM donations WHERE status='success'"
    ).fetchone()[0]

    # Donation records with search - FIXED: changed timestamp to created_at
    donations = conn.execute("""
        SELECT users.name,
               users.email,
               donations.amount,
               donations.status,
               DATE(donations.created_at) as date
        FROM donations
        JOIN users ON donations.user_id = users.id
        WHERE users.name LIKE ?
           OR users.email LIKE ?
           OR donations.status LIKE ?
           OR DATE(donations.created_at) LIKE ?
        ORDER BY donations.created_at DESC
    """, (
        f"%{search}%",
        f"%{search}%",
        f"%{search}%",
        f"%{search}%"
    )).fetchall()

    conn.close()

    return render_template(
        "admin_donations.html",
        total_donations=total_donations,
        today_donations=today_donations,
        total_amount=total_amount,
        donations=donations,
        search=search
    )

@app.route("/admin/logins")
def admin_logins():
    if "user_id" not in session:
        return redirect("/")

    conn = get_db_connection()

    # FIXED: changed timestamp to created_at
    logins = conn.execute("""
        SELECT users.name,
               users.email,
               DATE(login_logs.created_at) AS date
        FROM login_logs
        JOIN users ON login_logs.user_id = users.id
        WHERE users.email NOT LIKE '%@ngo%'
        ORDER BY login_logs.created_at DESC
    """).fetchall()

    conn.close()

    return render_template("admin_logins.html", logins=logins)

############################################################
@app.route("/download/users")
def download_users():
    if "role" not in session or session["role"] != "admin":
        return redirect("/")
    
    conn = get_db_connection()
    cursor = conn.cursor()

    # FIXED: Use correct table and column names
    cursor.execute("""
        SELECT name, email, phone, address, aadhaar, DATE(created_at) as date
        FROM users
        ORDER BY created_at DESC
    """)
    rows = cursor.fetchall()

    # Custom headers for nice display
    headers = ["Name", "Email", "Phone", "Address", "Aadhaar", "Date"]
    conn.close()

    si = StringIO()
    writer = csv.writer(si)

    writer.writerow(headers)
    for row in rows:
        writer.writerow(row)

    return Response(
        si.getvalue(),
        mimetype="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=registered_users.csv"
        }
    )

#######################################################################################

@app.route("/download/donations")
def download_donations():
    if "role" not in session or session["role"] != "admin":
        return redirect("/")
    
    conn = get_db_connection()
    cursor = conn.cursor()

    # FIXED: Use correct column names and JOIN with users table
    cursor.execute("""
        SELECT 
            u.name,
            u.email,
            d.amount,
            d.status,
            DATE(d.created_at) as date
        FROM donations d
        JOIN users u ON d.user_id = u.id
        ORDER BY d.created_at DESC
    """)
    rows = cursor.fetchall()

    # Custom headers for nice display
    headers = ["Name", "Email", "Amount", "Status", "Date"]
    conn.close()

    si = StringIO()
    writer = csv.writer(si)

    writer.writerow(headers)
    for row in rows:
        writer.writerow(row)

    return Response(
        si.getvalue(),
        mimetype="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=donations.csv"
        }
    )

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)
