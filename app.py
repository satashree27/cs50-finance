import os
import sqlite3
from flask import Flask, render_template, request, redirect, session, flash, jsonify
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
from helpers import error_msg, login_required, lookup, usd

app = Flask(__name__)

app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses are not cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)


db = sqlite3.connect("finance.db", check_same_thread=False)
def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d
db.row_factory = dict_factory


@app.route("/")
def homepage():
    return render_template("homepage.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    session.clear()
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if not username:
            return error_msg("Must provide username", 403)
        elif not password:
            return error_msg("Must provide password", 403)

        cursor = db.cursor()
        rows = cursor.execute("SELECT * FROM users WHERE username = (?)", [username]).fetchall()
        if len(rows)!=1 or not check_password_hash(rows[0]["hash"], password):
            return error_msg("Invalid username/password combination", 403)
        
        cursor.close()
        session["user_id"] = rows[0]["id"]
        return redirect("/dashboard")
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if not request.form.get("username"):
            return error_msg("must provide username", 400)
        elif not password:
            return error_msg("Must provide password", 400)
        elif password != request.form.get("confirmation"):
            return error_msg("Passwords do not match", 400)

        hashpass = generate_password_hash(password)
        cursor = db.cursor()
        result = db.execute("INSERT INTO users (username, hash) VALUES (?, ?)", [username, hashpass])
        db.commit()
        if not result:
            return error_msg("Username unavailable", 400)
        
        rows = cursor.execute("SELECT * FROM users WHERE username = (?)", [username]).fetchall()
        session["user_id"] = rows[0]["id"]
        flash("Registered!")
        cursor.close()
        return redirect("/dashboard")
    return render_template("register.html")


@app.route("/check", methods=["GET"])
def check():
    cursor = db.cursor()
    username = request.args.get('username')
    other_username = db.execute("SELECT username FROM users WHERE username=(?)", [username]).fetchall()
    cursor.close()
    try:
        result = other_username[0]['username']
        if not result:
            return jsonify(True)
        else:
            return jsonify(False)
    except IndexError:
        return jsonify(True)


@app.route("/dashboard", methods=["GET", "POST"])
@login_required
def dashboard():
    cursor = db.cursor()
    username = cursor.execute("SELECT username FROM users WHERE id=(?)", [session["user_id"]]).fetchall()[0]["username"]
    # Add more cash
    if request.method == "POST":
        add_cash = request.form.get("cash")
        user_cash = cursor.execute("SELECT cash FROM users WHERE id=(?)", [session["user_id"]]).fetchall()[0]["cash"]
        cursor.execute("UPDATE users SET cash=(?) WHERE username=(?)", [user_cash+float(add_cash), username])
        db.commit()
        cursor.close()
        flash("Cash added!")
        return redirect("/dashboard")

    stocks = cursor.execute("SELECT symbol, shares FROM portfolio WHERE username=(?)", [username]).fetchall()
    total_sum = []
    if stocks != None:
        for stock in stocks:
            symbol = str(stock["symbol"])
            shares = int(stock["shares"])
            name = lookup(symbol)["name"]
            price = lookup(symbol)["price"]
            total = shares*price
            stock["name"] = name
            stock["price"] = usd(price)
            stock["total"] = usd(total)
            total_sum.append(float(total))
    
    cash = cursor.execute("SELECT cash FROM users WHERE id=(?)", [session["user_id"]]).fetchall()[0]["cash"]
    cash_total = cash + sum(total_sum)
    cursor.close()
    return render_template("dashboard.html", stocks=stocks, cash=usd(cash), cash_total=usd(cash_total))


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    if request.method == "POST":
        stock = lookup(request.form.get("symbol"))
        if stock == None:
            return error_msg("Invalid symbol", 400)
        else:
            return render_template("quoted.html", name=stock["name"], symbol=stock["symbol"], price=usd(stock["price"]))
    else:
        return render_template("quote.html")


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    cursor = db.cursor()
    if request.method == "POST":
        stock = lookup(request.form.get("symbol"))
        shares = request.form.get("shares")
        if stock == None:
            return error_msg("Invalid symbol", 400)
        elif not shares or int(shares) < 1:
            return error_msg("No. of shares must be atleast 1", 400)
        
        cash = cursor.execute("SELECT cash FROM users WHERE id=(?)", [session["user_id"]]).fetchall()[0]["cash"]
        username = cursor.execute("SELECT username FROM users WHERE id=(?)", [session["user_id"]]).fetchall()[0]["username"]
        shares_value = int(shares)*stock["price"]
        if cash < shares_value:
            return error_msg("Not enough cash available", 403)
        else:
            symbol = stock["symbol"]
            cursor.execute("UPDATE users SET cash=(?) WHERE id=(?)", [cash-shares_value, session["user_id"]])
            user_shares = cursor.execute("SELECT shares FROM portfolio WHERE username=(?) AND symbol=(?)", [username, symbol]).fetchall()
            print(user_shares)
            if(len(user_shares) == 0):
                cursor.execute("INSERT INTO portfolio (username, symbol, shares) VALUES (?, ?, ?)", [username, symbol, shares])
            else:
                user_shares = user_shares[0]["shares"]
                cursor.execute("UPDATE portfolio SET shares=(?) WHERE username=(?) AND symbol=(?)", [int(user_shares)+int(shares), username, symbol])
            cursor.execute("INSERT INTO history (username, symbol, action, price, shares) VALUES (?, ?, ?, ?, ?)", [username, symbol, "BUY", stock["price"], shares])
            db.commit()
            cursor.close()
            flash("Bought!")
            return redirect("/dashboard")
    else:
        return render_template("buy.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    cursor = db.cursor()
    username = cursor.execute("SELECT username FROM users WHERE id=(?)", [session["user_id"]]).fetchall()[0]["username"]
    if request.method == "POST":
        symbol = request.form.get("symbol")
        shares = request.form.get("shares")
        username = cursor.execute("SELECT username FROM users WHERE id=(?)", [session["user_id"]]).fetchall()[0]["username"]
        cash = cursor.execute("SELECT cash FROM users WHERE id=(?)", [session["user_id"]]).fetchall()[0]["cash"]
        user_shares = cursor.execute("SELECT shares FROM portfolio WHERE username=(?) AND symbol=(?)", [username, symbol]).fetchall()[0]["shares"]
        stock = lookup(symbol)
        if stock == None:
            return error_msg("Please provide a valid symbol", 400)
        elif not shares or int(shares)<1 or int(shares)>int(user_shares):
            return error_msg("Please provide valid share number", 400)

        shares_value = int(shares)*stock["price"]
        cursor.execute("UPDATE users SET cash=(?) WHERE id=(?)", [cash+shares_value, session["user_id"]])
        cursor.execute("INSERT INTO history (username, symbol, action, price, shares) VALUES (?, ?, ?, ?, ?)", [username, symbol, "SELL", stock["price"], shares])
        if int(shares) == int(user_shares):
            cursor.execute("DELETE FROM portfolio WHERE username=(?) AND symbol=(?)", [username, symbol])
        else:
            cursor.execute("UPDATE portfolio SET shares=(?) WHERE username=(?) AND symbol=(?)", [int(user_shares)-int(shares), username, symbol])
        db.commit()
        cursor.close()
        flash("Sold!")
        return redirect("/dashboard")
    else:
        symbols = cursor.execute("SELECT symbol FROM portfolio WHERE username=(?)", [username]).fetchall()
        cursor.close()
        return render_template("sell.html", symbols=symbols)


@app.route("/history")
@login_required
def history():
    cursor = db.cursor()
    username = cursor.execute("SELECT username FROM users WHERE id=(?)", [session["user_id"]]).fetchall()[0]["username"]
    stocks = cursor.execute("SELECT symbol, action, price, shares, date, time FROM history WHERE username=(?)", [username]).fetchall()
    for stock in stocks:
        symbol = str(stock["symbol"])
        shares = int(stock["shares"])
        stock["name"] = lookup(symbol)["name"]
        stock["price"] = usd(stock["price"])
    cursor.close()
    return render_template("history.html", stocks=stocks)


# Change password
@app.route("/change_pwd", methods=["GET", "POST"])
@login_required
def change_pwd():
    if request.method == "GET":
        return render_template("change_pwd.html")
    cursor = db.cursor()
    old_pwd = request.form.get("old_password")
    new_pwd = request.form.get("new_password")
    confirmation = request.form.get("confirmation")

    if not old_pwd or not new_pwd or not confirmation:
        return error_msg("Missing field!", 400)
    user = cursor.execute("SELECT * FROM users WHERE id=(?)", [session["user_id"]]).fetchall()
    if not check_password_hash(user[0]["hash"], old_pwd):
        return error_msg("Invalid password", 400)
    if new_pwd!=confirmation:
        return error_msg("Passwords do not match", 400)

    hashpass = generate_password_hash(new_pwd)
    cursor.execute("UPDATE users SET hash=(?) WHERE username=(?)", [hashpass, user[0]["username"]])
    db.commit()
    cursor.close()
    flash("Password changed!")
    return redirect("/dashboard")


if __name__ == "__main__":
    app.secret_key = 'mysecret'
    app.run(debug = True)
