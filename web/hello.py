from flask import Flask, render_template, redirect, session, request
from flask_mysqldb import MySQL

import pandas as pd
import pickle
import numpy as np
from surprise import KNNBasic
from surprise.model_selection import train_test_split
from surprise.model_selection import GridSearchCV
from surprise import Reader, Dataset
import surprise.accuracy


app = Flask(__name__)
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'skripsi_anime'
mysql = MySQL(app)
app.secret_key = 'aplikasi_rekomendasi_anime_ekky'

folder = "../../Dataset SKRIPSI/"

@app.route("/")
def index():
    cursor = mysql.connection.cursor()
    cursor.execute('SELECT * FROM anime ORDER BY members DESC LIMIT 40')
    anime = cursor.fetchall()
    return render_template("index.html", anime=anime)

@app.route("/search", methods=['GET'])
def search():
    if request.method == 'GET':
        search = request.args.get("search")
        cursor = mysql.connection.cursor()
        cursor.execute('SELECT * FROM anime WHERE title LIKE %s ORDER BY members DESC', ["%"+search+"%"])
        anime = cursor.fetchall()
    return render_template("search.html", anime=anime, search=search)    

@app.route("/admin")
def admin():
    if session.get("login"):
        if session['tipe'] == "admin":
            return render_template("admin/admin.html", navlink_index = 'active')
        else:
            return redirect('admin/user')
    return redirect('/')

@app.route("/admin/user")
def admin_user():
    filename = folder + "users_data"
    UsersDF = pickle.load(open(filename,'rb'))
    UsersDF = UsersDF.head(100)

    return render_template("admin/users.html", navlink_user = 'active' , user = [UsersDF.to_html(table_id='example1', classes = 'table table-bordered table-hover display nowrap', header = "true")] )

@app.route("/admin/dataset")
def admin_dataset():
    filename = folder + "scores_data"
    ScoresDF = pickle.load(open(filename,'rb'))
    ScoresDF = ScoresDF.head(100)

    return render_template("admin/dataset.html", navlink_dataset = 'active' , score = [ScoresDF.to_html(table_id='example1', classes = 'table table-bordered table-hover display nowrap', header = "true")])

@app.route("/admin/hasil_rekomendasi")
def admin_hasil_rekomendasi():
    filename = folder + "users_data"

    return render_template("admin/user.html")

@app.route("/admin/pengujian")
def admin_pengujian():
    filename = folder + "users_data"
    UsersDF = pickle.load(open(filename,'rb'))

    return render_template("admin/user.html")

@app.route("/user")
def user():
    return render_template("user/user.html")

@app.route("/user/input", methods=['GET'])
def user_input():

    return render_template("user/form.html")

@app.route("/login")
def login():
    return render_template("login.html")

@app.route("/proses_login", methods=['POST'])
def proses_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        cursor = mysql.connection.cursor()
        cursor.execute('SELECT * FROM user WHERE username = %s AND password = %s', (username, password))
        account = cursor.fetchone()

        if account:
            session['login'] = True
            session['username'] = account[0]
            session['tipe'] = account[2]
            if session['tipe'] == 'admin':
                return redirect('admin')
            elif session['tipe'] == 'user':
                return redirect('user')
        else:
            msg = "Incorrect username / password"
    return render_template('login.html',msg=msg)    

@app.route("/sign_up")
def sign_up():
    return render_template("sign_up.html")

@app.route("/logout")
def logout():
    session.pop('username',None)
    session.pop('tipe',None)
    session.pop('login',None)
    return redirect('/')

if __name__ == "__main__":
    app.run(debug=True)