import os
from datetime import datetime
from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")

#Home page with main table of data
@app.route("/")
@login_required
def index():
    user_id = session["user_id"]
    rows = db.execute("SELECT * FROM Index_t")
    row = db.execute("SELECT balance FROM users WHERE id = :user_id", user_id = user_id)
    user_cash = row[0]["balance"]
    sum = 0
    for i in rows:
        db.execute("SELECT total FROM Index_t")
        total = i["total"]
        sum = sum  + total
    total_cash = user_cash + sum
    return render_template("index.html", user_cash=user_cash, rows=rows, total_cash=total_cash)

#Analyze page showing the chart
@app.route("/chart")
@login_required
def chart():

    #List of expences values
    prices = db.execute("SELECT Price FROM chart_1")
    values = []
    for price in prices:
        values.append(price["Price"])

    #List of expences names
    names = db.execute("SELECT Name FROM chart_1")
    labels = []
    for name in names:
        labels.append(name["Name"])

    colors = ["#3e95cd", "#8e5ea2", "#3cba9f", "#e8c3b9", "#c45850", "#aeb6bf"]

    return render_template("chart.html", title = "Current Month Expences [$]", values=values, labels=labels, colors=colors)

#Pay page, allows to update all the expances in the table and the chart
@app.route("/pay", methods=["GET", "POST"])
@login_required
def pay():

    if request.method == "POST":

        payment = request.form.get("payment")
        if payment == "Payment":
            return apology("must provide a payment type", 400)

        if not request.form.get("amount"):
            return apology("must provide an amount", 400)

        amount = float(request.form.get("amount"))
        if amount <= 0:
            return apology("must provide a positive number", 403)

        user_id = session["user_id"]
        row = db.execute("SELECT balance FROM users WHERE id = :user_id", user_id = user_id)
        user_cash = row[0]["balance"]

        date = datetime.now()
        month_year = date.strftime("%b/%Y")
        rows = db.execute("SELECT * FROM Index_t")

        #checking if this month already exists
        if len(rows) == 0:
            db.execute("INSERT INTO Index_t (month_year) VALUES (:month_year)", month_year = month_year)
        else:
            i = 0
            for row in rows:
                if month_year == row["month_year"]:
                    break
                else:
                    i = i + 1
            if i == len(rows):
                db.execute("INSERT INTO Index_t (month_year) VALUES (:month_year)", month_year = month_year)

        row2 = db.execute("SELECT total FROM Index_t WHERE month_year = :month_year", month_year = month_year)
        total = row2[0]["total"]

        #overdraft notice
        if amount > user_cash:
            return apology("beware, overdraft!", 403)

        user_cash = user_cash - amount
        total = total - amount

        #updating the relevant table tab
        if payment == "Rent":
            rent = db.execute("SELECT rent FROM Index_t WHERE month_year = :month_year", month_year = month_year)
            new_rent = rent[0]["rent"] + amount
            db.execute("UPDATE Index_t SET rent = :rent WHERE month_year = :month_year", month_year = month_year, rent = new_rent)
            db.execute("UPDATE chart_1 SET Price = :price WHERE Name = :name", name = "rent", price = new_rent)

        elif payment == "Bills":
            bills = db.execute("SELECT bills FROM Index_t WHERE month_year = :month_year", month_year = month_year)
            new_bills = bills[0]["bills"] + amount
            db.execute("UPDATE Index_t SET bills = :bills WHERE month_year = :month_year", month_year = month_year, bills = new_bills)
            db.execute("UPDATE chart_1 SET Price = :price WHERE Name = :name", name = "bills", price = new_bills)

        elif payment == "Groceries":
            groceries = db.execute("SELECT groceries FROM Index_t WHERE month_year = :month_year", month_year = month_year)
            new_groceries = groceries[0]["groceries"] + amount
            db.execute("UPDATE Index_t SET groceries = :groceries WHERE month_year = :month_year", month_year = month_year, groceries = new_groceries)
            db.execute("UPDATE chart_1 SET Price = :price WHERE Name = :name", name = "groceries", price = new_groceries)

        elif payment == "Pets":
            pets = db.execute("SELECT pets FROM Index_t WHERE month_year = :month_year", month_year = month_year)
            new_pets = pets[0]["pets"] + amount
            db.execute("UPDATE Index_t SET pets = :pets WHERE month_year = :month_year", month_year = month_year, pets = new_pets)
            db.execute("UPDATE chart_1 SET Price = :price WHERE Name = :name", name = "pets", price = new_pets)

        elif payment == "Shopping":
            shopping = db.execute("SELECT shopping FROM Index_t WHERE month_year = :month_year", month_year = month_year)
            new_shopping = shopping[0]["shopping"] + amount
            db.execute("UPDATE Index_t SET shopping = :shopping WHERE month_year = :month_year", month_year = month_year, shopping = new_shopping)
            db.execute("UPDATE chart_1 SET Price = :price WHERE Name = :name", name = "shopping", price = new_shopping)

        else:
            other = db.execute("SELECT other_expences FROM Index_t WHERE month_year = :month_year", month_year = month_year)
            new_other = other[0]["other_expences"] + amount
            db.execute("UPDATE Index_t SET other_expences = :other WHERE month_year = :month_year", month_year = month_year, other = new_other)
            db.execute("UPDATE chart_1 SET Price = :price WHERE Name = :name", name = "other", price = new_other)

        db.execute("UPDATE Index_t SET total = :total WHERE month_year = :month_year", total = total, month_year = month_year)
        db.execute("UPDATE users SET balance = :balance WHERE id = :user_id", balance = user_cash, user_id = user_id)
        flash("Payed!")
        return redirect("/")
    else:
        return render_template("pay.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        if not username:
            return apology("must provide username", 403)

        rows = db.execute("SELECT * FROM users WHERE username = :username", username=username)
        if len(rows) != 0:
            return apology("Username already taken", 403)

        password = request.form.get("password")
        if not password:
            return apology("must provide password", 403)

        password_again = request.form.get("password_again")
        if not password_again:
            return apology("must provide password", 403)
        if password_again != password:
            return apology("passwords must be identical", 403)

        password_hash = generate_password_hash(password)

        db.execute("INSERT INTO users (username, hash) VALUES (:username, :hash)", username=username, hash=password_hash)
        flash("Registered!")
        return redirect("/")
    else:
        return render_template("register.html")

#Add_Income page, allows to update the income values
@app.route("/add_income", methods=["GET", "POST"])
@login_required
def add_income():

    if request.method == "POST":

        income = request.form.get("income")
        if income == "Income":
            return apology("must provide an income type", 400)

        if not request.form.get("amount"):
            return apology("must provide an amount", 400)

        amount = float(request.form.get("amount"))
        if amount <= 0:
            return apology("must provide a positive number", 403)

        user_id = session["user_id"]
        row = db.execute("SELECT balance FROM users WHERE id = :user_id", user_id = user_id)
        user_cash = row[0]["balance"]

        date = datetime.now()
        month_year = date.strftime("%b/%Y")
        rows = db.execute("SELECT * FROM Index_t")

        #If the month already exists, enter to the relevant place
        if len(rows) == 0:
            db.execute("INSERT INTO Index_t (month_year) VALUES (:month_year)", month_year = month_year)
        else:
            i = 0
            for row in rows:
                if month_year == row["month_year"]:
                    break
                else:
                    i = i + 1
            if i == len(rows):
                db.execute("INSERT INTO Index_t (month_year) VALUES (:month_year)", month_year = month_year)

        row2 = db.execute("SELECT total FROM Index_t WHERE month_year = :month_year", month_year = month_year)
        total = row2[0]["total"]

        user_cash = user_cash + amount
        total = total + amount

        #Updatinh the relevant table tab
        if income == "Salary":
            salary = db.execute("SELECT salary FROM Index_t WHERE month_year = :month_year", month_year = month_year)
            new_salary = salary[0]["salary"] + amount
            db.execute("UPDATE Index_t SET salary = :salary WHERE month_year = :month_year", month_year = month_year, salary = new_salary)

        else:
            other = db.execute("SELECT other_income FROM Index_t WHERE month_year = :month_year", month_year = month_year)
            new_other = other[0]["other_income"] + amount
            db.execute("UPDATE Index_t SET other_income = :other WHERE month_year = :month_year", month_year = month_year, other = new_other)

        #Updating the total and the balance
        db.execute("UPDATE Index_t SET total = :total WHERE month_year = :month_year", total = total, month_year = month_year)
        db.execute("UPDATE users SET balance = :balance WHERE id = :user_id", balance = user_cash, user_id = user_id)

        flash("Income!")
        return redirect("/")

    else:
        return render_template("add_income.html")


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
