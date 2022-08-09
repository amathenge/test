from flask import Flask, render_template, request, redirect, url_for, session
from flask_recaptcha import ReCaptcha
import os
from database import get_db
import cred
import hashlib
from datetime import datetime
from decimal import Decimal, getcontext

app = Flask(__name__)

app.config['SECRET_KEY'] = os.urandom(24)
# recaptcha
# app.config['RECAPTCHA_SITE_KEY'] = cred.recaptcha_site_key
# app.config['RECAPTCHA_SECRET_KEY'] = cred.recaptcha_secret_key

# recaptcha = ReCaptcha(app)

def hashpass(pwd):
    return hashlib.md5(pwd.encode()).hexdigest()

@app.template_filter('nl2br')
def nl2br(item):
    if isinstance(item, str):
        return item.replace('\n','<br>')
    return item

@app.route('/', defaults={'msg': None})
@app.route('/<msg>')
def home(msg):
    email = None
    if 'email' in session:
        email = session['email']
        return render_template('home.html', email=email, msg=msg)

    return redirect(url_for('login', msg=msg))

# @app.route('/login')
# def home2():
#     return render_template('login.html')

@app.route('/login', methods=['GET','POST'], defaults={'msg': None})
@app.route('/login/<msg>', methods=['GET','POST'])
def login(msg):
    if 'email' in session:
        session.pop('email')

    if request.method == 'POST':
        credentials = {}
        credentials['email'] = request.form['email'].lower()
        credentials['password'] = request.form['password']
        # here's where we check to make sure stuff is OK and then pass it on to home.
        db = get_db()
        cur = db.cursor()
        sql = 'select email, firstname, lastname, password from users where email = ?'
        cur.execute(sql, (credentials['email'],))
        row = cur.fetchone()
        if not row:
            msg = 'Invalid User or Password'
            return redirect(url_for('login', msg=msg))
        # password check here before we do the next steps.
        encpass = hashpass(credentials['password'])

        if encpass == row['password']:
            session['email'] = row['email']
            session['firstname'] = row['firstname']
            session['lastname'] = row['lastname']
            msg = 'Login Success'
        else:
            # only return this if the password does not match the email address
            msg = 'Invalid user or password'

        return redirect(url_for('home', msg=msg))
    return render_template('login.html', msg=msg)

@app.route('/adduser', methods=['GET','POST'])
def adduser():
    if 'email' not in session:
        return redirect(request.referrer)

    if request.method == 'POST':
        email = request['email'].lower()
        firstname = request['firstname']
        lastname = request['lastname']
        password = request['password']
        joindate = datetime.now()
        description = request['description']

        db = get_db()
        cur = db.cursor()
        sql = 'select * from users where email = ?'
        cur.execute(sql, (email,))
        row = cur.fetchone()
        if len(row) > 0:
            return redirect(request.referrer)

        sql = 'insert into users (email, firstname, lastname, password, description) values (?, ?, ?, ?, ?)'
        cur.execute(sql, (email, firstname, lastname, password, description))
        db.commit()
        return redirect(url_for('users'))

    return render_template('adduser.html')

@app.route('/users', methods=['GET','POST'])
def users():
    if 'email' not in session:
        return redirect(request.referrer)

    db = get_db()
    cur = db.cursor()
    sql = 'select email, firstname, lastname, description from users order by firstname'
    return render_template('users.html')

def calcLoanPayment(payment, loan, rate):
    results = list()
    interest = Decimal(0)
    cumulative = Decimal(0)
    cumulative_interest = Decimal(0)
    # calculate total interest
    total_interest = Decimal(0)
    l = loan
    months = 0
    while l > 0:
        months += 1
        interest = Decimal(l * rate)
        total_interest += interest
        l -= (payment-interest)
    total_amount = loan + total_interest
    l = loan
    month = 0
    monthly_amount = payment
    while l > 0:
        month += 1
        interest = Decimal(l * rate)
        cumulative_interest += interest
        if month == months:
            monthly_amount = total_amount - Decimal(payment * (month-1))
        results.append({"m": month, "l": l, "p": monthly_amount, "i": interest, "pp": monthly_amount-interest, "ci": cumulative_interest})
        l -= (payment-interest)
    return results

def calcTotalsPayment(payment, loan, rate):
    interest = Decimal(0)
    c_interest = Decimal(0)
    monthly_payment = payment
    cumulative = Decimal(0)
    months = 0
    while loan > 0:
        months += 1
        interest = loan * rate
        c_interest += interest
        if monthly_payment > loan:
            cumulative += loan+interest
        else:
            cumulative += monthly_payment
        loan -= (monthly_payment-interest)

    return {"m": months, "i": c_interest, "p": cumulative}

def calcLoan(months, loan, rate):
#    getcontext().prec = 4
    results = list()
    principal = Decimal(loan) / Decimal(months)
    interest = 0
    cumulative = 0
    cumulative_interest = 0
    # calculate the total payments
    total_interest = Decimal(0)
    l = loan
    for month in range(1, months+1):
        interest = Decimal(l*rate)
        total_interest += interest
        l -= principal
    interest = Decimal(0)
    total_amount = Decimal(loan) + total_interest
    monthly_amount = Decimal(total_amount) / Decimal(months)
    monthly_amount = round(monthly_amount+Decimal(1), 0)
    for month in range(1, months+1):
        interest = Decimal(loan) * Decimal(rate)
        cumulative_interest = Decimal(cumulative_interest) + Decimal(interest)
        if month == months:
            monthly_amount = total_amount - (Decimal(monthly_amount * (months-1)))
        results.append({"m": month, "l": loan, "p": principal, "i": interest, "pp": principal+interest, "ci": cumulative_interest, "s": monthly_amount})
        loan = Decimal(loan)-Decimal(principal)
        cumulative += Decimal(principal)

    return results

def calcTotals(months, loan, rate):
#    getcontext().prec = 4
    interest = 0
    c_interest = 0
    cumulative = 0
    principal = Decimal(loan) / Decimal(months)
    for month in range(1, months+1):
        interest = Decimal(loan) * Decimal(rate)
        c_interest = Decimal(c_interest) + Decimal(interest)
        cumulative = Decimal(cumulative) + Decimal(principal) + Decimal(interest)
        loan = Decimal(loan) - Decimal(principal)

    return {"i": c_interest, "p": cumulative}

@app.route('/fawa', methods=['GET', 'POST'])
def fawa():
    reply = None
    data = None
    totals = None
    if request.method == 'POST':
        months = request.form['months']
        loan = request.form['loan']
        rate = request.form['rate']
        try:
            months = int(months)
            loan = Decimal(loan)
            rate = Decimal(rate)
            reply = f"months = {months} and loan = {loan} and rate={rate}"
            data = calcLoan(months, loan, rate)
            totals = calcTotals(months, loan, rate)
        except:
            reply = 'invalid data months={} and loan={} and rate={}'.format(months, loan, rate)

    return render_template('fawa.html', reply=reply, data=data, totals=totals)

@app.route('/fawa_pay', methods=['GET','POST'])
def fawa_pay():
    reply = None
    data = None
    totals = None
    if request.method == 'POST':
        payment = request.form['payment']
        loan = request.form['loan']
        rate = request.form['rate']
        try:
            payment = Decimal(payment)
            loan = Decimal(loan)
            rate = Decimal(rate)
            reply = f"payment={payment} and loan={loan} and rate={rate}"
            data = calcLoanPayment(payment, loan, rate)
            totals = calcTotalsPayment(payment, loan, rate)
        except:
            replay = "invalid data payment={} and loan={} and rate={}".format(payment, loan, rate)

    return render_template('fawa_pay.html', reply=reply, data=data, totals=totals)

@app.route('/logout')
def logout():
    if 'email' in session:
        session.pop('email')
        session.clear()
    return redirect(url_for('home', msg=None))
