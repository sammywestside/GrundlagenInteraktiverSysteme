import csv
import datetime
import pytz
import requests
import subprocess
import urllib
import uuid
import sys
import time

from flask import redirect, render_template, session
from functools import wraps
import functools


def apology(message, code=400):
    """Render message as an apology to user."""
    def escape(s):
        """
        Escape special characters.

        https://github.com/jacebrowning/memegen#special-characters
        """
        for old, new in [("-", "--"), (" ", "-"), ("_", "__"), ("?", "~q"),
                         ("%", "~p"), ("#", "~h"), ("/", "~s"), ("\"", "''")]:
            s = s.replace(old, new)
        return s
    return render_template("apology.html", top=code, bottom=escape(message)), code


def login_required(f):
    """
    Decorate routes to require login.

    http://flask.pocoo.org/docs/0.12/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function

@functools.lru_cache(maxsize=1)
def lookup(symbol, retries=3):
    """Look up quote for symbol."""

    for attempt in range(retries):
        try:
            # Prepare API request
            if symbol is not None:
                symbol = symbol.upper()
            end = datetime.datetime.now(pytz.timezone("US/Eastern"))
            start = end - datetime.timedelta(days=7)

            # Yahoo Finance API
            url = (
                f"https://query1.finance.yahoo.com/v7/finance/download/{urllib.parse.quote_plus(symbol)}"
                f"?period1={int(start.timestamp())}"
                f"&period2={int(end.timestamp())}"
                f"&interval=1d&events=history&includeAdjustedClose=true"
            )

            # Query API
            # cookies={"session": str(uuid.uuid4())}
            response = requests.get(url, headers={"User-Agent": "curl/7.68.0", "Accept": "*/*"})
            if response.status_code == 429:
                time.sleep(3)
                continue
            response.raise_for_status()

            # CSV header: Date,Open,High,Low,Close,Adj Close,Volume
            quotes = list(csv.DictReader(response.content.decode("utf-8").splitlines()))
            quotes.reverse()
            price = round(float(quotes[0]["Adj Close"]), 2)
            return {
                "name": symbol,
                "price": price,
                "symbol": symbol
            }
        except (requests.RequestException, ValueError, KeyError, IndexError) as e:
            # print("error:", e)
            # exc_type, exc_obj, exc_tb = sys.exc_info()
            print(f"Error fetching data: {e}")
            return None
    else:
        print("To many retries")
        return None

def usd(value):
    """Format value as USD."""
    return f"${value:,.2f}"
