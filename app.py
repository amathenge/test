from flask import Flask, render_template, request, redirect, url_for, session
from flask_recaptcha import ReCaptcha
import os
from database import get_db
import cred
import hashlib
from datetime import datetime

app = Flask(__name__)

app.config['SECRET_KEY'] = os.urandom(24)
# recaptcha
app.config['RECAPTCHA_SITE_KEY'] = cred.recaptcha_site_key
app.config['RECAPTCHA_SECRET_KEY'] = cred.recaptcha_secret_key

recaptcha = ReCaptcha(app)

def hashpass(pwd):
    return hashlib.md5(pwd.encode()).hexdigest()

@app.template_filter('nl2br')
def nl2br(item):
    if isinstance(item, str):
        return item.replace('\n','<br>')
    return item

@app.route('/')
def home(msg):
    email = None
    if 'email' in session:
        email = session['email']
        return render_template('home.html', email=email, msg=msg)

    return redirect(url_for('login'))

# @app.route('/login')
# def home2():
#     return render_template('login.html')

@app.route('/login', methods=['GET','POST'])
def login():
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
        cur.execute(sql, (credentials['user'],))
        row = cur.fetchone()
        if len(row) == 0:
            return redirect(request.referrer)
        session['email'] = row['email']
        session['firstname'] = row['firstname']
        session['lastname'] = row['lastname']

        return redirect(url_for('home', msg='Invalid User or Password'))

    return render_template('login.html')

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

@app.route('/logout')
def logout():
    return redirect(url_for('home', msg=None))
