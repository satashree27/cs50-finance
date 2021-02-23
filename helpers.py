from webconfig import API_KEY
import requests
import urllib.parse

from flask import redirect, render_template, request, session
from functools import wraps

def error_msg(message, code=400):
    return render_template("error_msg.html", code=code, message=message), code


def login_required(f):
    """
    http://flask.pocoo.org/docs/1.0/patterns/viewdecorators/
    """
    @wraps(f)
    def wrap(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return wrap


def lookup(symbol):
    """Look up quote for symbol."""
    # Contact API
    try:
        api_key = API_KEY
        response = requests.get(f"https://cloud-sse.iexapis.com/stable/stock/{urllib.parse.quote_plus(symbol)}/quote?token={api_key}")
        response.raise_for_status()
    except requests.RequestException:
        return None
 
    # Parse response
    try:
        quote = response.json()
        return {
            "name": quote["companyName"],
            "price": float(quote["latestPrice"]),
            "symbol": quote["symbol"]
        }
    except (KeyError, TypeError, ValueError):
        return None


def usd(value):
    """Format value as USD."""
    return f"${value:,.2f}"