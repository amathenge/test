from flask import Flask, render_template, request, redirect, url_for, session
from flask_recaptcha import ReCaptcha
import os
from database import get_db
import cred

app = Flask(__name__)

app.config['SECRET_KEY'] = os.urandom(24)
# recaptcha
app.config['RECAPTCHA_SITE_KEY'] = cred.recaptcha_site_key
app.config['RECAPTCHA_SECRET_KEY'] = cred.recaptcha_secret_key

recaptcha = ReCaptcha(app)

@app.template_filter('nl2br')
def nl2br(item):
    if isinstance(item, str):
        return item.replace('\n','<br>')
    return item

@app.route('/')
def home():
    user = None
    if user in session:
        user = session['user']
    return render_template('home.html', user=user)

@app.route('/login')
def home2():
    return render_template('login.html')

@app.route('/login', methods=['GET','POST'])
def login():
    if user in session:
        return redirect(url_for('home'))

    if request.method == 'POST':
        credentials = {}
        credentials['user'] = request.form['email']
        credentials['password'] = request.form['password']
        return render_template('loginform.html', credentials=credentials)

    return redirect(url_for('home2'))