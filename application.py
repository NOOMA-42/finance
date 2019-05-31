from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions
from werkzeug.security import check_password_hash, generate_password_hash


from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

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


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    portfoliosheet = db.execute("SELECT symbol, SUM(shares) FROM portfolio WHERE userid = :userid GROUP BY symbol",userid=session.get("user_id") )
    symbolst=[]
    pricelst=[]
    sharelst=[]
    namelst=[]
    totalst=[]

    for dic in portfoliosheet:
        symbolst.append(dic['symbol'])
        sharelst.append(dic['SUM(shares)'])
        pricelst.append(lookup(dic['symbol'])["price"])
        namelst.append(lookup(dic['symbol'])['name'])
        totalst.append(dic['SUM(shares)'] * lookup(dic['symbol'])['price'])
    sheet = {"price":pricelst, "shares":sharelst, "name":namelst, "total":totalst, "symbol":symbolst}
    grandcash = sum(totalst) + db.execute("SELECT cash FROM users WHERE id = :userid", userid=session.get("user_id"))[0]['cash']
    return render_template("index.html", sheet = sheet, listnum = len(pricelst), grandcash = grandcash)

@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""

    if request.method == "POST":
        if not request.form.get("symbol") or not lookup(request.form.get("symbol")):
            return apology("Missing symbol",400)
        cash = db.execute("SELECT cash FROM users WHERE id = :userid",
                          userid=session.get("user_id"))[0]['cash']
        cash = cash- int((request.form.get("shares")))*lookup(request.form.get("symbol"))["price"]
        if cash < 0:
            return apology("Can't afford",400)

        portfolio = db.execute("INSERT INTO portfolio(price, userid, symbol, shares) VALUES(:price, :userid, :symbol, :shares)",
        price = lookup(request.form.get("symbol"))["price"],
        userid = session.get("user_id"),
        symbol = request.form.get("symbol"),
        shares = request.form.get("shares")
            )
        updatecash = db.execute("UPDATE users SET cash = :cash WHERE id = :userid", userid=session.get("user_id"), cash = cash)
        return redirect("/")

    else:
        return render_template("buy.html")



@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    history = db.execute("SELECT symbol, price, shares, time FROM portfolio WHERE userid = :userid ORDER BY time",userid=session.get("user_id"))
    return render_template("history.html",sheet = history)

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
        rows= db.execute("SELECT * FROM users WHERE username = :username",
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


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == "POST":
        if lookup(request.form.get("quote")):
            return render_template("showquote.html", symbol = lookup(request.form.get("quote"))["symbol"]
            ,name = lookup(request.form.get("quote"))["name"]
            ,price = lookup(request.form.get("quote"))["price"])
        else:
            return apology("Ivalid symbol", 400)
    else:
        return render_template("quote.html")




@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "POST":
        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("Missing username", 400)
        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("Missing password", 400)
        # Ensure confirmation was submitted
        elif not request.form.get("confirmation"):
            return apology("Missing confirmation", 400)
        elif request.form.get("confirmation") != request.form.get("password"):
            return apology("Missing confirmation", 400)

        results = db.execute("INSERT INTO users(username,hash) VALUES(:username,:password)" ,
                           username = request.form.get("username"), password = generate_password_hash(request.form.get("username")))
        if not results:
            return apology("Username Taken", 400)

        return redirect("/")
    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    if request.method == "POST":
        A = db.execute("SELECT shares FROM portfolio WHERE userid = :userid AND symbol = :symbol",
            symbol = request.form.get("symbol"),
            userid = session.get("user_id"))[0]["shares"] - int(request.form.get("shares"))
        B = - int(request.form.get("shares"))

        cash = db.execute("SELECT cash FROM users WHERE id = :userid",
               userid = session.get("user_id"))[0]["cash"] + lookup(request.form.get("symbol"))["price"] * int(request.form.get("shares"))

        if A > 0 and B < 0:
            sellstock = db.execute("INSERT INTO portfolio (shares, symbol, userid, price) VALUES (:shares, :symbol, :userid, :price)",
                        symbol = request.form.get("symbol"), userid = session.get("user_id"), shares = B, price = lookup(request.form.get("symbol"))["price"])
            cashplus = db.execute("UPDATE users SET cash = :usercash WHERE id = :userid",userid = session.get("user_id"),
                       usercash = cash)
            return redirect("/")
        else:
            return apology("TOO MANY SHARES",400)
    else:
        portfoliosheet = db.execute("SELECT symbol FROM portfolio WHERE userid = :userid GROUP BY symbol", userid = session.get("user_id"))
        return render_template("sell.html",sheet = portfoliosheet)


def errorhandler(e):
    """Handle error"""
    return apology(e.name, e.code)


# listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
