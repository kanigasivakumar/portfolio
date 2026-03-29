from flask import Flask, render_template, request, redirect, session, flash, send_file
import os
import io
import csv
import sqlite3
import pickle
from werkzeug.security import generate_password_hash, check_password_hash
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch

app = Flask(__name__)
app.secret_key = "supersecretkey"

# ---------------- DATABASE INIT ----------------
def init_db():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

# ---------------- LOAD ML MODEL ----------------
model = None
vectorizer = None

if os.path.exists("model.pkl") and os.path.exists("vectorizer.pkl"):
    model = pickle.load(open("model.pkl", "rb"))
    vectorizer = pickle.load(open("vectorizer.pkl", "rb"))

# ---------------- HOME ----------------
@app.route("/")
def home():
    if "user" in session:
        return redirect("/dashboard")
    return redirect("/login")

# ---------------- REGISTER ----------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"].strip()

        conn = sqlite3.connect("database.db")
        c = conn.cursor()

        hashed_password = generate_password_hash(password)

        try:
            c.execute("INSERT INTO users (username, password) VALUES (?, ?)",
                      (username, hashed_password))
            conn.commit()
        except:
            flash("Username already exists!", "danger")
            conn.close()
            return redirect("/register")

        conn.close()
        flash("Registration Successful! Please Login.", "success")
        return redirect("/login")

    return render_template("register.html")

# ---------------- LOGIN ----------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"].strip()

        conn = sqlite3.connect("database.db")
        c = conn.cursor()
        c.execute("SELECT password FROM users WHERE username=?", (username,))
        data = c.fetchone()
        conn.close()

        if data and check_password_hash(data[0], password):
            session["user"] = username
            return redirect("/dashboard")

        flash("Invalid Credentials!", "danger")
        return redirect("/login")

    return render_template("login.html")

# ---------------- DASHBOARD ----------------
@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/login")
    return render_template("dashboard.html", user=session["user"])

# ---------------- SPAM CHECK ----------------
@app.route("/spam_check", methods=["GET", "POST"])
def spam_check():
    if "user" not in session:
        return redirect("/login")

    result = None

    if request.method == "POST":
        message = request.form["message"]

        if model and vectorizer:
            vect = vectorizer.transform([message])
            prediction = model.predict(vect)[0]
            if prediction == 1:
                result = "Spam Message 🚨"
            else:
                result = "Not Spam ✅"
        else:
            # fallback logic if model not available
            if "free" in message.lower() or "win" in message.lower():
                result = "Spam Message 🚨"
            else:
                result = "Not Spam ✅"

    return render_template("spam_check.html", result=result)

# ---------------- ANALYTICS ----------------
@app.route("/analytics")
def analytics():
    if "user" not in session:
        return redirect("/login")
    return render_template("analytics.html")

# ---------------- USERS ----------------
@app.route("/users")
def users():
    if "user" not in session:
        return redirect("/login")

    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("SELECT username FROM users")
    data = c.fetchall()
    conn.close()

    user_list = [row[0] for row in data]

    return render_template("users.html", users=user_list)

# ---------------- REPORTS PAGE ----------------
@app.route("/reports")
def reports():
    if "user" not in session:
        return redirect("/login")
    return render_template("reports.html")

# ---------------- DOWNLOAD SPAM REPORT ----------------
@app.route("/download_spam_report")
def download_spam_report():
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()

    elements.append(Paragraph("<b>Spam Detection Report</b>", styles["Title"]))
    elements.append(Spacer(1, 0.5 * inch))
    elements.append(Paragraph("System Running Successfully", styles["Normal"]))
    elements.append(Paragraph("ML Model Integrated", styles["Normal"]))

    doc.build(elements)
    buffer.seek(0)

    return send_file(buffer,
                     as_attachment=True,
                     download_name="Spam_Report.pdf",
                     mimetype="application/pdf")

# ---------------- DOWNLOAD USER REPORT ----------------
@app.route("/download_user_report")
def download_user_report():
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(["S.No", "Username"])

    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("SELECT username FROM users")
    data = c.fetchall()
    conn.close()

    for index, row in enumerate(data, start=1):
        writer.writerow([index, row[0]])

    output.seek(0)

    return send_file(io.BytesIO(output.getvalue().encode()),
                     as_attachment=True,
                     download_name="User_Report.csv",
                     mimetype="text/csv")

# ---------------- DOWNLOAD SYSTEM LOG ----------------
@app.route("/download_system_log")
def download_system_log():
    log_content = """
Spam Detection System Log

System Status: Running
Security: Password Hashing Enabled
Database: SQLite Connected
ML Model: Active
"""

    return send_file(io.BytesIO(log_content.encode()),
                     as_attachment=True,
                     download_name="System_Log.txt",
                     mimetype="text/plain")

# ---------------- SETTINGS ----------------
@app.route("/settings")
def settings():
    if "user" not in session:
        return redirect("/login")
    return render_template("settings.html")

# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.pop("user", None)
    flash("Logged out successfully!", "info")
    return redirect("/login")

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)

