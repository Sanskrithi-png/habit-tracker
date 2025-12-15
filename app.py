from flask import Flask, render_template, request, redirect
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from pathlib import Path

from db import get_db, init_db
from user import User

app = Flask(__name__)
app.secret_key = "CHANGE_THIS_SECRET"

if not Path("app.db").exists():
    init_db()

login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)

# ---------- AUTH ----------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        db = get_db()
        try:
            db.execute(
                "INSERT INTO users (username, password) VALUES (?, ?)",
                (request.form["username"],
                 generate_password_hash(request.form["password"]))
            )
            db.commit()
            return redirect("/login")
        except:
            return "Username already exists"
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        db = get_db()
        user = db.execute(
            "SELECT * FROM users WHERE username=?",
            (request.form["username"],)
        ).fetchone()
        if user and check_password_hash(user["password"], request.form["password"]):
            login_user(User(user))
            return redirect("/")
        return "Invalid credentials"
    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect("/login")

# ---------- HELPERS ----------
def month_dates(year, month):
    start = datetime(year, month, 1)
    end = (start.replace(day=28) + timedelta(days=4)).replace(day=1)
    dates = []
    while start < end:
        dates.append(start.strftime("%Y-%m-%d"))
        start += timedelta(days=1)
    return dates

def streak(user_id, habit):
    db = get_db()
    count = 0
    day = datetime.today()
    while True:
        d = day.strftime("%Y-%m-%d")
        row = db.execute(
            "SELECT value FROM habits WHERE user_id=? AND habit=? AND date=?",
            (user_id, habit, d)
        ).fetchone()
        if row and row["value"] == 1:
            count += 1
            day -= timedelta(days=1)
        else:
            break
    return count

# ---------- MAIN ----------
@app.route("/")
@login_required
def index():
    db = get_db()
    month = int(request.args.get("month", datetime.now().month))
    year = datetime.now().year

    habits = [r["habit"] for r in db.execute("SELECT habit FROM habit_list")]
    dates = month_dates(year, month)

    data = {}
    for d in dates:
        rows = db.execute(
            "SELECT habit, value FROM habits WHERE user_id=? AND date=?",
            (current_user.id, d)
        ).fetchall()
        data[d] = {r["habit"]: r["value"] for r in rows}

    return render_template(
        "month.html",
        data=data,
        habits=habits,
        month=month
    )

@app.route("/update", methods=["POST"])
@login_required
def update():
    db = get_db()
    db.execute(
        "REPLACE INTO habits VALUES (?, ?, ?, ?)",
        (
            current_user.id,
            request.form["date"],
            request.form["habit"],
            1 if request.form.get("value") else 0
        )
    )
    db.commit()
    return ("", 204)

@app.route("/add_habit", methods=["POST"])
@login_required
def add_habit():
    h = request.form["habit"].strip()
    if h:
        db = get_db()
        db.execute("INSERT OR IGNORE INTO habit_list VALUES (?)", (h,))
        db.commit()
    return redirect("/")

@app.route("/dashboard")
@login_required
def dashboard():
    db = get_db()
    habits = [r["habit"] for r in db.execute("SELECT habit FROM habit_list")]

    stats = []
    for h in habits:
        completed = db.execute(
            "SELECT COUNT(*) FROM habits WHERE user_id=? AND habit=? AND value=1",
            (current_user.id, h)
        ).fetchone()[0]

        stats.append({
            "habit": h,
            "completed": completed,
            "streak": streak(current_user.id, h)
        })

    return render_template(
        "dashboard.html",
        stats=stats,
        share_url=f"{request.host_url}share/{current_user.id}"
    )

@app.route("/share/<int:user_id>")
def share(user_id):
    db = get_db()
    month = int(request.args.get("month", datetime.now().month))
    year = datetime.now().year

    habits = [r["habit"] for r in db.execute("SELECT habit FROM habit_list")]
    dates = month_dates(year, month)

    data = {}
    for d in dates:
        rows = db.execute(
            "SELECT habit, value FROM habits WHERE user_id=? AND date=?",
            (user_id, d)
        ).fetchall()
        data[d] = {r["habit"]: r["value"] for r in rows}

    return render_template("share.html", data=data, habits=habits, month=month)

if __name__ == "__main__":
    app.run(debug=True)
