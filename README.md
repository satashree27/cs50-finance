# cs50-finance
Web based application built using Flask that uses IEX API and SQL database to simulate a share-trading website. This is basically the CS50-Finance project implemented from scratch.

### Buy-Sell-Stock
The task is to built a web application that simulates a stock trading website, via which users can “buy” and “sell” stocks. This is basically the problem statement of CS50 Web Track project.
The app queries [IEX](https://iexcloud.io/) for realtime stocks price.
Please check [C$50-Finance](https://cs50.harvard.edu/x/2020/tracks/web/finance/)

For the backend of this project Flask was used. The frontend is mainly on HTML and Bootstrap CSS.
SQLite database is used as it is simple for small-scale apps in the development phase.

#### Database
SQLite databe has been used (finance.db) with 3 tables: users, portfolio, and history.
*users* stores the users registered and their cash available (Note that by defalt a newly registered user is alloted $10000.0).
*portfolio* describes the different shares bought by a user.
*history* decribes the whole history of the actions (BUY or SELL) taken by the user using this app.

The table schema are as follows:

For *users*:
CREATE TABLE IF NOT EXISTS 'users'(
'id' INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
'username' TEXT UNIQUE NOT NULL,
'hash' TEXT NOT NULL,
'cash' NUMERIC NOT NULL DEFAULT 10000.0);

For *portfolio*:
CREATE TABLE IF NOT EXISTS 'portfolio'(
'id' INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
'username' TEXT NOT NULL,
'symbol' VARCHAR(10),
'shares' INTEGER);

For *history*:
CREATE TABLE IF NOT EXISTS 'history'(
'id' INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
'username' TEXT NOT NULL,
'symbol' VARCHAR(10),
'action' VARCHAR(10),
'price' REAL,
'shares' INTEGER,
'date' DATE DEFAULT CURRENT_DATE,
'time' TIME DEFAULT CURRENT_TIME);

#### Run
Install the required dependencies and run the follwoing command:
```
python app.py
```

#### Note:
As "personal touch" added the change password and add-cash functionality. For the message alerts, used flask [*flash*](https://flask.palletsprojects.com/en/1.1.x/patterns/flashing/).
