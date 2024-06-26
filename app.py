import os
import sqlite3
import sys

from flask import Flask, flash, redirect, render_template, request, session, g, jsonify
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd
import datetime
import re

# Configure application
app = Flask(__name__)
app.secret_key = "secret-key"

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

app.debug = True

# Configure Database
DATABASE = "finance.db"

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    
    db.row_factory = sqlite3.Row

    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def query_db(query, args=(), one=False):
    try:
        if not isinstance(args, tuple):
            args = (args,)

        conn = get_db()
        cur = conn.cursor()

        cur.execute(query, args)

        if one:
            rv = cur.fetchone()
        else:
            rv = cur.fetchall()
        cur.close()

        return (rv[0] if rv else None) if one else rv
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        print(f"An error occured on line: {exc_tb.tb_lineno}: {e}")

def insert_query(table, data):
    columns = ','.join(data.keys())
    placeholders = ', '.join(['?'] * len(data))
    values = tuple(data.values())

    query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
    get_db().execute(query, values)
    get_db().commit()

def update_query(table, data, data2):
    columns = ','.join(data.keys())
    columns2 = ','.join(data2.keys())
    placeholders = ','.join(['?']) * len((data))
    values = tuple(data.values())
    values2 = tuple(data2.values())

    query = f"UPDATE {table} SET ({columns}) = ({placeholders}) WHERE ({columns2}) = ({placeholders})"
    get_db().execute(query, values, values2)
    get_db().commit()

def modify_db(query, args=()):
    try: 
        conn = get_db()
        cur = conn.execute(query, args)
        conn.commit()
        cur.close()
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        print(f"An error occured on line: {exc_tb.tb_lineno}: {e}")

@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

def get_active_user():
    return session.get("user_id")

@app.route('/api/user-id', methods=["GET"])
def get_user_id():
    user_id = get_active_user()
    return jsonify({"user_id": user_id})

@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    query = "SELECT symbol, shares FROM possesions WHERE user_id = ?"
    stocks = query_db(query, (session.get("user_id"),))
    stock_data = []

    total = 0

    for stock in stocks:
        symbol = stock["symbol"]
        stock_info = lookup(symbol)
        price = stock_info["price"]
        price_value = usd(price)
        shares = stock["shares"]
        total = price * shares
        total_value = usd(total)

        stock_data.append({
            "symbol": symbol,
            "price": price_value,
            "shares": shares,
            "total": total_value
        })

    cash_query = "SELECT cash FROM users WHERE id = ?"
    cash = query_db(cash_query, (session.get("user_id"),))
    cash_value = cash[0]["cash"]
    cash_balance = usd(float(cash_value))

    grand_total = cash_value + total
    grandtotal = usd(grand_total)

    return render_template("index.html", stock_data=stock_data, cash_balance=cash_balance, grandtotal=grandtotal)

@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    try:
        purchase = []

        if request.method == "POST":

            symbol = request.form.get("symbol")
            if not symbol:
                return apology("Cannot Find Symbol", 400)

            fshares = request.form.get("shares")
            if fshares is None or not fshares.isdigit():
                return apology("Invalid Number of Shares", 400)

            user_id = session.get("user_id")
            query_user = "SELECT cash FROM users WHERE id = ?"
            user_info = query_db(query_user, (user_id,))
            cash_balance= user_info[0]["cash"]

            shares = int(fshares)
            stock_lookup = lookup(symbol)
            if stock_lookup is not None:
                price_value = stock_lookup["price"]
                stock_name = stock_lookup["name"]
                stock_symbol = stock_lookup["symbol"]
            else:
                return apology("Invalid Symbol", 400)

            total_price = price_value * shares

            query_existing_stock = "SELECT id FROM stocks WHERE name = ?"
            existing_stock = query_db(query=query_existing_stock, args=stock_name, one=True)
            if existing_stock:
                stock_id = existing_stock
                print(f"stock_id: {stock_id}")
            else:
                max_stock_id = query_db(query = "SELECT MAX(id) AS max_id FROM stocks", one=True)
                print(f"max_stock_id: {max_stock_id}")
                if max_stock_id is not None:
                    next_stock_id = max_stock_id + 1
                    stock_dict = {
                        'id' : next_stock_id,
                        'symbol': symbol,
                        'name': stock_name,
                        'price': price_value
                    }
                    insert_query("stocks", stock_dict)
                    # insert = ("INSERT INTO stocks (id, symbol, name, price) VALUES (?, ?, ?, ?)", next_stock_id, symbol, stock_name, price_value)
                    stock_id = next_stock_id
                else:
                    next_stock_id = 1
                    stock_id = next_stock_id
                    # insert_query('stocks', stock_dict)
                    get_db().execute("INSERT INTO stocks (id, symbol, name, price) VALUES (?, ?, ?, ?)", (next_stock_id, symbol, stock_name, price_value))

            timestamp = datetime.datetime.now()

            if total_price <= cash_balance:
                new_balance = cash_balance - total_price
                transactions_dict = {
                    'user_id': user_id,
                    'stock_id': stock_id,
                    'shares': shares,
                    'price': price_value,
                    'timestamp': timestamp,
                    'type': "buy",
                    'symbol': symbol
                }

                insert_query('transactions', transactions_dict)
                # db_insert.execute("INSERT INTO transactions(user_id, stock_id, shares, price, timestamp, type, symbol) VALUES (?, ?, ?, ?, ?, ?, ?)", (user_id, stock_id, shares, total_price, timestamp, "buy", symbol))
                query_exisiting_possesion = "SELECT symbol FROM possesions WHERE stock_id = ?"
                existing_possesion = query_db(query=query_exisiting_possesion, args=stock_id, one=True)
                if existing_possesion:
                    if existing_possesion == symbol:
                        query_possesion = "SELECT shares FROM possesions WHERE stock_id = ?"
                        possesion_shares = query_db(query=query_possesion, args=stock_id, one=True)
                        new_shares = possesion_shares + shares
                        get_db().execute("UPDATE possesions SET shares = ? WHERE stock_id = ?", (new_shares, stock_id))
                    else:
                        insert_query('possesions', posessions_dict)
                        # get_db().execute("INSERT OR REPLACE INTO possesions (user_id, stock_id, shares, symbol) VALUES (?, ?, COALESCE((SELECT shares FROM possesions WHERE stock_id = ?), 0) + ?, ?)", (user_id, stock_id, stock_id, shares, symbol))
                else:
                    posessions_dict = {
                        "user_id": user_id,
                        "stock_id": stock_id,
                        "shares": shares,
                        "symbol": symbol
                    }
                    insert_query('possesions', posessions_dict)
                    # get_db().execute("INSERT OR REPLACE INTO possesions (user_id, stock_id, shares, symbol) VALUES (?, ?, COALESCE((SELECT shares FROM possesions WHERE stock_id = ?), 0) + ?, ?)",(user_id, stock_id, stock_id, shares, symbol))

                # get_db().execute(f"UPDATE users SET cash = {new_balance} WHERE id = {user_id}")
                modify_db("UPDATE users SET cash = ? WHERE id = ?", (new_balance, user_id))
                usd_balance = usd(new_balance)

                purchase_data = {
                    "symbol": symbol,
                    "shares": shares,
                    "price": usd(total_price),
                    "timestamp": timestamp,
                    "usd_balance": usd_balance
                }
                purchase.clear()
                purchase.append(purchase_data)

                return render_template("buy.html", purchase_data=purchase_data, purchase=purchase)

            elif total_price > cash_balance:
                print(total_price)
                print(cash_balance)
                return apology("Not enough money", 400)

        else:
            return render_template("buy.html", purchase=None)
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        print(f"An error occured on line: {exc_tb.tb_lineno}: {e}")

@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    history = []

    query_transactions = "SELECT type, price, shares, timestamp, symbol FROM transactions WHERE user_id = ?"
    transactions = query_db(query_transactions, (session.get("user_id"),))

    for transaction in transactions:
        history_dict = {
            "symbol": transaction["symbol"],
            "type": transaction["type"],
            "price": usd(transaction["price"]),
            "shares": transaction["shares"],
            "time": transaction["timestamp"]
        }
        history.append(history_dict)

    return render_template("history.html", history=history)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""
    try:
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
            query_username = ("SELECT * FROM users WHERE username = ?")
            cursor = get_db().execute(query_username, (request.form.get("username"),))
            rows = cursor.fetchall()
            print(f'user info: {rows}')
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
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        print(f"An error occured on line: {exc_tb.tb_lineno}: {e}")

@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == "POST":
        symbol = request.form.get("symbol")
        if not symbol:
            return apology("Please Enter a Symbol", 400)

        quote_data = lookup(symbol.upper())
        if quote_data == None or not quote_data:
            return apology("Invalid Symbol", 400)

        quote = [{
            "name": quote_data["name"],
            "symbol": quote_data["symbol"],
            "price": usd(quote_data["price"])
        }]

        return render_template("quoted.html", quote=quote)

    else:
        return render_template("quote.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    try:
        if request.method == "POST":
            name = request.form.get("username")
            if not name:
                return apology("Username cannot be empty", 400)
            password = request.form.get("password")
            if not password:
                return apology("Password cannot be empty", 400)

            confirmation = request.form.get("confirmation")
            if password != confirmation:
                return apology("Passwords do not match", 400)

            query_user = ("SELECT * FROM users WHERE username = ?", (name,))
            existing_user = query_db(query_user)
            print(existing_user)

            if existing_user:
                return apology("Username already exists", 400)

            def password_check(password):
                contains_number = re.search(r'\d', password)
                contains_capital = re.search(r'[A-Z]', password)
                contains_symbol = re.search(r'[,.-_]', password)

                return contains_number and contains_capital and contains_symbol

            if not password_check(password):
                return apology("Password does not meet requirements", 400)

            hash = generate_password_hash(password)
            print(f"Name: {name}; Code: {hash}")
            query_registration = ("INSERT INTO users (username, hash) VALUES (?, ?)")
            get_db().execute(query_registration, (name, hash))
            get_db().commit()

            return render_template("login.html"), 200

        else:
            return render_template("register.html")
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        print(f"An error occured on line: {exc_type, exc_tb.tb_lineno}: {e}")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    try:
        stocks = []

        if request.method == "POST":
            symbol = request.form.get("symbol")
            if not symbol:
                return apology("Please Select Stock", 403)

            fshares = request.form.get("shares")
            if not fshares:
                return apology("Missing Shares", 403)
            shares = int(fshares)

            query_stock = ("SELECT id FROM stocks WHERE symbol = ?")
            stock_id = query_db(query=query_stock,args=(symbol,), one=True)
            if not stock_id:
                return apology("Invalid Stock Symbol", 403)
            stock_id = stock_id

            stock_lookup = lookup(symbol)
            if stock_lookup is not None:
                price = stock_lookup["price"]

            query_user = ("SELECT cash FROM users WHERE id = ?")
            user_info= query_db(query=query_user, args=(session.get("user_id"),), one=True)
            cash_balance = int(user_info)
            value = price * shares
            timestamp = datetime.datetime.now()

            selling_dict = {
                'user_id': session.get('user_id'),
                'stock_id': stock_id,
                'shares': shares,
                'price': price,
                'timestamp': timestamp,
                'type': "sell",
                'symbol': symbol
            }

            selling = insert_query('transactions', selling_dict)
            # selling = db_insert.execute("INSERT INTO transactions(user_id, stock_id, shares, price, timestamp, type, symbol) VALUES (?, ?, ?, ?, ?, ?, ?)", (session.get("user_id"), stock_id, shares, price, timestamp, "sell", symbol))
        
            query_posessions = ("SELECT SUM(shares) AS total_shares FROM possesions WHERE stock_id = ?")
            result = query_db(query=query_posessions, args=(stock_id,))
            # result = get_db().execute(query_posessions, stock_id)
            current_shares = result[0]["total_shares"]
            # if result[0]['total_shares'] and result[0]['total_shares']:
            #     current_shares = result[0]['total_shares']

            if current_shares is not None and current_shares >= shares:
                new_shares = current_shares - shares
                print(new_shares)
                if new_shares == 0:
                    modify_db("DELETE FROM possesions WHERE stock_id = ?", (stock_id,))
                else:
                    modify_db("UPDATE possesions SET shares = ? WHERE stock_id = ?", (new_shares, stock_id))
            else:
                return apology("Invalid Number of Shares", 400)
    
            new_balance = cash_balance + value
            modify_db("UPDATE users SET cash = ? WHERE id = ?", (new_balance, session.get("user_id")))
            success_message = "Successfully sold stocks"
            usd_balance = usd(new_balance)

            sell_data = {
                "symbol": symbol,
                "shares": shares,
                "price": usd(price),
                "timestamp": timestamp,
                "usd_balance": usd_balance
            }

            return render_template("sell.html", selling=selling, success_message=success_message, sell_data=sell_data)

        else:
            query_stocks = ("SELECT * FROM stocks")
            stocks = query_db(query=query_stocks)

            return render_template("sell.html", stocks=stocks)
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        print(f"An error occured on line: {exc_tb.tb_lineno}: {e}")