from flask import Flask, render_template, request, redirect, session
import sqlite3
import random
from datetime import datetime

app = Flask(__name__)
app.secret_key = "secret123"


# ---------------- DB CONNECTION ----------------
def get_db_connection():
    conn = sqlite3.connect("database.db")
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

    conn.execute("""
        INSERT INTO users
        (name, email, password, phone, address, aadhaar, role, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (name, email, password, phone, address, aadhaar, "user", datetime.now()))

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


# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)
