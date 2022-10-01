from distutils.log import debug
from flask import Flask, render_template
from flask_mysqldb import MySQL

app = Flask(__name__)
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'skripsi_anime'
mysql = MySQL(app)

@app.route("/")
def index():
    cursor = mysql.connection.cursor()
    cursor.execute('SELECT * FROM anime ORDER BY members DESC LIMIT 40')
    anime = cursor.fetchall()
    return render_template("index.html", anime=anime)

@app.route("/admin")
def admin():
    return render_template("admin.html")

@app.route("/user")
def user():
    return render_template("user.html")

@app.route("/login")
def login():
    return render_template("login.html")

if __name__ == "__main__":
    app.run(debug=True)