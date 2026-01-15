from flask import Flask, render_template, request, redirect, session
import sqlite3
import random
from datetime import datetime
import os

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

    return redirect("/")


# ---------------- LOGIN ----------------
@app.route("/login", methods=["POST"])
def login():
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

    return render_template("auth.html", login_error="Invalid login credentials")



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
        ORDER BY timestamp DESC
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

    # Total registrations
    total_users = conn.execute(
        "SELECT COUNT(*) FROM users"
    ).fetchone()[0]

    # Today's registrations
    today_users = conn.execute(
        "SELECT COUNT(*) FROM users WHERE DATE(created_at)=DATE('now')"
    ).fetchone()[0]

    # User list with search
    users = conn.execute("""
        SELECT id, name, email, phone, address, aadhaar, DATE(created_at) as date
        FROM users
        WHERE name LIKE ?
           OR email LIKE ?
           OR phone LIKE ?
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

    # Today's donations
    today_donations = conn.execute(
        "SELECT COUNT(*) FROM donations WHERE DATE(timestamp)=DATE('now')"
    ).fetchone()[0]

    # Total successful donation amount
    total_amount = conn.execute(
        "SELECT COALESCE(SUM(amount),0) FROM donations WHERE status='success'"
    ).fetchone()[0]

    # Donation records with search
    donations = conn.execute("""
        SELECT users.name,
               users.email,
               donations.amount,
               donations.status,
               DATE(donations.timestamp) as date
        FROM donations
        JOIN users ON donations.user_id = users.id
        WHERE users.name LIKE ?
           OR users.email LIKE ?
           OR donations.status LIKE ?
           OR DATE(donations.timestamp) LIKE ?
        ORDER BY donations.timestamp DESC
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

    logins = conn.execute("""
        SELECT users.name,
               users.email,
               DATE(login_logs.timestamp) AS date
        FROM login_logs
        JOIN users ON login_logs.user_id = users.id
        WHERE users.email NOT LIKE '%@ngo%'
        ORDER BY login_logs.timestamp DESC
    """).fetchall()

    conn.close()

    return render_template("admin_logins.html", logins=logins)



# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)
