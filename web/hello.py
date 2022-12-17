from flask import Flask, render_template, redirect, session, request, url_for
from flask_mysqldb import MySQL
from sqlalchemy import create_engine

import pandas as pd
import pickle
import numpy as np
from sklearn.preprocessing import MinMaxScaler
from surprise import KNNBasic
from surprise.model_selection import train_test_split
from surprise.model_selection import KFold
from surprise.model_selection import cross_validate
from surprise import Reader, Dataset
import surprise.accuracy

db_host = 'localhost'
db_username = 'root'
db_password = ''
db_name = 'skripsi_anime'

app = Flask(__name__)
app.config['MYSQL_HOST'] = db_host
app.config['MYSQL_USER'] = db_username
app.config['MYSQL_PASSWORD'] = db_password
app.config['MYSQL_DB'] = db_name
mysql = MySQL(app)
app.secret_key = 'aplikasi_rekomendasi_anime_ekky'

folder = "../../Dataset SKRIPSI/"

@app.route("/", methods=['GET'])
@app.route("/<int:page>", methods=['GET'])
def index(page = 0):
    cursor = mysql.connection.cursor()
    cursor.execute('select count(anime_id) from anime')
    count = cursor.fetchone()
    count = int(count[0]/40)
    pagination = (page,page+1,count)
    
    offset = page*40
    offset = str(offset)
    
    query = 'SELECT * FROM anime ORDER BY members DESC LIMIT ' + offset + ',40'
    cursor.execute(query)
    anime = cursor.fetchall()
    return render_template("index.html", anime=anime, title="Home", pagination = pagination)

@app.route("/login")
def login():
    return render_template("login.html", title="Login")

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

@app.route("/sign_up") ## Belom
def sign_up():
    return render_template("sign_up.html", title="Sign Up")

@app.route("/proses_sign_up", methods=['POST']) ## Belom
def proses_sign_up():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        cursor = mysql.connection.cursor()
        cursor.execute('SELECT * FROM user WHERE username = %s AND password = %s', (username, password))
        account = cursor.fetchone()

        if account:
            msg = "Username already exist!"
        else:
            cursor.execute('INSERT INTO user values(%s,%s,%s)', (username, password, 'user'))
            #jangan lupa dicommit setelah insert
            mysql.connection.commit()
            session['login'] = True
            session['username'] = username
            session['tipe'] = 'user'
            return redirect('user')
    
    return render_template('login.html',msg=msg) 

@app.route("/logout")
def logout():
    session.pop('username',None)
    session.pop('tipe',None)
    session.pop('login',None)
    return redirect('/')

@app.route("/search", methods=['GET'])
def search():
    if request.method == 'GET':
        search = request.args.get("search")
        cursor = mysql.connection.cursor()
        cursor.execute('SELECT * FROM anime WHERE title LIKE %s ORDER BY members DESC', ["%"+search+"%"])
        anime = cursor.fetchall()

        title = "Search : "+search 
    return render_template("search.html", anime=anime, search=search, title=title)    

@app.route("/admin") ## Belom
def admin():
    if session.get("login"):
        if session['tipe'] == "admin":
            cursor = mysql.connection.cursor()
            cursor.execute('select count(username) from user')
            banyak_anime = cursor.fetchone()

            cursor.execute('select count(username) from useranime')
            banyak_user = cursor.fetchone()

            cursor.execute('select count(id_rekomendasi) from nomor_rekomendasi')
            banyak_rekomendasi = cursor.fetchone()

            cursor.execute('SELECT count(anime_id) FROM anime')
            banyak_rating = cursor.fetchone()
            return render_template("admin/admin.html", navlink_index = 'active', title="Home", banyak_anime=banyak_anime, banyak_user=banyak_user, banyak_rekomendasi=banyak_rekomendasi, banyak_rating=banyak_rating)
        else:
            return redirect('user')
    return redirect('/')

@app.route("/admin/user")
def admin_user():
    if session.get("login"):
        if session['tipe'] == "admin":
            filename = folder + "users_data"
            UsersDF = pickle.load(open(filename,'rb'))
            UsersDF = UsersDF.head(1000)
            return render_template("admin/users.html",title="User" , navlink_user = 'active' , user = [UsersDF.to_html(table_id='example1', classes = 'table table-bordered table-hover display nowrap', header = "true")] )
        else:
            return redirect('user')

@app.route("/admin/dataset")
def admin_dataset():
    if session.get("login"):
        if session['tipe'] == "admin":
            cursor = mysql.connection.cursor()
            cursor.execute('select username, anime_id, my_score, my_status from useranime')
            user = cursor.fetchmany(10000)

            cursor = mysql.connection.cursor()
            cursor.execute('select username, COUNT(anime_id) from useranime group by username')
            count = cursor.fetchall()

            return render_template("admin/dataset.html",title="User Anime", navlink_dataset = 'active' , user=user, count=count)
        else:
            return redirect('user')
    return redirect('/')

@app.route("/admin/hasil_rekomendasi") 
def admin_hasil_rekomendasi():
    if session.get("login"):
        if session['tipe'] == "admin":
            cursor = mysql.connection.cursor()
            cursor.execute('select history_rekomendasi.id_rekomendasi, username, tipe_rekomendasi, min_k, max_k, banyak_rating_user from nomor_rekomendasi inner join history_rekomendasi on history_rekomendasi.id_rekomendasi = nomor_rekomendasi.id_rekomendasi GROUP BY history_rekomendasi.id_rekomendasi')
            rekomendasi = cursor.fetchall()

            return render_template("admin/hasil_rekomendasi.html",navlink_rekomendasi = 'active' ,title="Hasil Rekomendasi", rekomendasi=rekomendasi)
        else:
            return redirect('user')
    return redirect('/')

@app.route("/admin/detail_rekomendasi/<id_rekomendasi>", methods=['GET']) 
def admin_detail_rekomendasi(id_rekomendasi):
    if session.get("login"):
        if session['tipe'] == "admin":
            cursor = mysql.connection.cursor()
            cursor.execute('select username, history_rekomendasi.anime_id, title, image_url, history_rekomendasi.score from history_rekomendasi inner join anime on history_rekomendasi.anime_id = anime.anime_id WHERE id_rekomendasi = %s', [id_rekomendasi])
            rekomendasi = cursor.fetchall()

            return render_template("admin/detail_rekomendasi.html", navlink_rekomendasi = 'active', title="Hasil Rekomendasi", rekomendasi=rekomendasi, id_rekomendasi=id_rekomendasi)
        else:
            return redirect('user')
    return redirect('/')

@app.route("/admin/pengujian") ## Belom
def admin_pengujian():
    cursor = mysql.connection.cursor()
    cursor.execute('select history_rekomendasi.id_rekomendasi, username, tipe_rekomendasi, min_k, max_k, mae, rmse, banyak_rating_user from nomor_rekomendasi inner join history_rekomendasi on history_rekomendasi.id_rekomendasi = nomor_rekomendasi.id_rekomendasi GROUP BY history_rekomendasi.id_rekomendasi')
    rekomendasi = cursor.fetchall()
    
    cursor.execute('select min_k from nomor_rekomendasi WHERE tipe_rekomendasi = %s ORDER BY tipe_rekomendasi ASC, min_k ASC ', ["cf"])
    label = [item[0] for item in cursor.fetchall()]
    cursor.execute('select min_k from nomor_rekomendasi WHERE tipe_rekomendasi = %s ORDER BY tipe_rekomendasi ASC, min_k ASC ', ["wcf"])
    label2 = [item[0] for item in cursor.fetchall()]
    print(label)
    cursor.execute('select mae from nomor_rekomendasi WHERE tipe_rekomendasi = %s ORDER BY tipe_rekomendasi ASC, min_k ASC ', ["cf"])
    cf_mae = [item[0] for item in cursor.fetchall()]
    cursor.execute('select rmse from nomor_rekomendasi WHERE tipe_rekomendasi = %s ORDER BY tipe_rekomendasi ASC, min_k ASC ', ["cf"])
    cf_rmse = [item[0] for item in cursor.fetchall()]
    cursor.execute('select mae from nomor_rekomendasi WHERE tipe_rekomendasi = %s ORDER BY tipe_rekomendasi ASC, min_k ASC ', ["wcf"]) 
    wcf_mae = [item[0] for item in cursor.fetchall()]
    cursor.execute('select rmse from nomor_rekomendasi WHERE tipe_rekomendasi = %s ORDER BY tipe_rekomendasi ASC, min_k ASC ', ["wcf"])
    wcf_rmse = [item[0] for item in cursor.fetchall()]


    return render_template("admin/pengujian.html", title="Pengujian", navlink_pengujian = "active" ,rekomendasi=rekomendasi, label1=label, label2=label2, cf_mae=cf_mae, cf_rmse=cf_rmse, wcf_rmse=wcf_rmse, wcf_mae=wcf_mae)

@app.route("/user") 
def user():
    cursor = mysql.connection.cursor()
    cursor.execute('select useranime.anime_id, anime.image_url, anime.title, my_score, my_status from useranime inner join anime on useranime.anime_id = anime.anime_id where username = %s ORDER BY useranime.anime_id', [session.get('username')])
    user = cursor.fetchall()
    msg = request.args.get("msg")
    cursor = mysql.connection.cursor()
    cursor.execute('SELECT * FROM anime ORDER BY members DESC LIMIT 40')
    anime = cursor.fetchall()
    return render_template("user/user.html", user=user, msg=msg, title="Dashboard", anime=anime)

@app.route("/user/input", methods=['POST'])
def user_input():
    if request.method == 'POST':
        username = session.get('username')
        anime_id = request.form['anime_id']
        cursor = mysql.connection.cursor()
        # cari foto anime
        cursor.execute('SELECT title,image_url FROM anime WHERE anime_id = %s', [anime_id])
        img = cursor.fetchone()
        cursor.execute('SELECT useranime.anime_id, my_score, my_status, title, image_url FROM useranime inner join anime on useranime.anime_id = anime.anime_id WHERE username = %s AND useranime.anime_id = %s', [username, anime_id])
        useranime = cursor.fetchone()

        if useranime == None:
            edit = False
        else:
            edit = True
        title = "ID : "+anime_id
        return render_template("user/form.html", user=useranime, img=img, anime_id=anime_id, title=title, edit=edit)

@app.route("/user/input/proses", methods=['POST'])
def user_input_proses():
    if request.method == 'POST':
        username = session.get('username')
        anime_id = request.form['anime_id']
        my_score = request.form['my_score']
        my_status = request.form['my_status']

        if my_status == 'watching':
            my_status = 1
        elif my_status == 'completed':
            my_status = 2
        elif my_status == 'onhold':
            my_status = 3
        elif my_status == 'dropped':
            my_status = 4
        elif my_status == 'plantowatch':
            my_status = 6

        cursor = mysql.connection.cursor()
        cursor.execute('INSERT INTO useranime(username, anime_id, my_score, my_status) VALUES (%s,%s,%s,%s)', [username, anime_id, my_score, my_status])
        #jangan lupa dicommit setelah insert
        mysql.connection.commit()

    # return render_template('tes.html', var=var)
    return redirect("/user")

@app.route("/user/edit/proses", methods=['POST'])
def user_edit_proses():
    if request.method == 'POST':
        username = session.get('username')
        anime_id = request.form['anime_id']
        my_score = request.form['my_score']
        my_status = request.form['my_status']

        if my_status == 'watching':
            my_status = 1
        elif my_status == 'completed':
            my_status = 2
        elif my_status == 'onhold':
            my_status = 3
        elif my_status == 'dropped':
            my_status = 4
        elif my_status == 'plantowatch':
            my_status = 6

        # sql = 'UPDATE useranime SET my_score =  %s, my_status = %s WHERE username = %s AND anime_id = %s', [my_score, my_status, username, anime_id]
        # print(sql)
        cursor = mysql.connection.cursor()
        cursor.execute('UPDATE useranime SET my_score =  %s, my_status = %s WHERE username = %s AND anime_id = %s', [my_score, my_status, username, anime_id])
        #jangan lupa dicommit setelah insert
        mysql.connection.commit()

    # return render_template('tes.html', var=var)
    return redirect("/user")

@app.route("/user/rekomendasi")
def user_rekomendasi():
    cursor = mysql.connection.cursor()
    cursor.execute('select history_rekomendasi.anime_id, history_rekomendasi.score, anime.title, image_url from history_rekomendasi inner join anime on anime.anime_id = history_rekomendasi.anime_id where username = %s AND id_rekomendasi = (select max(id_rekomendasi) from history_rekomendasi where username = %s)', [session.get('username'), session.get('username')] )
    # cursor.execute('select useranime.anime_id, anime.image_url, anime.title, my_score, my_status from useranime inner join anime on useranime.anime_id = anime.anime_id where username = %s ORDER BY useranime.anime_id', [session.get('username')])
    user = cursor.fetchall()
    return render_template("user/rekomendasi.html", user=user, title="Rekomendasi Mu")

@app.route("/user/generate_rekomendasi", methods=['POST'])
def generate_rekomendasi():
    if session.get("login"):
        username = session.get("username")
        min_k = request.form["min_k"]
        min_k = int(min_k)
        max_k = 50
        tipe_rekomendasi = "wcf"
        
        # cek user udah ada rekomendasi apa belom
        cursor = mysql.connection.cursor()
        cursor.execute('select username, anime_id, my_score, my_status from useranime where username = %s', [username])
        useranime = cursor.fetchall()
        if useranime:
            print("ada isinya")
        else:
            print("ngga ada isinya")
            return redirect(url_for('user', msg="Isilah rating anime terlebih dahulu minimal satu data!"))
        
        #ambil banyak rating
        cursor.execute('select count(anime_id) from useranime where username = %s', [username])
        banyak_rating_user = cursor.fetchone()
        banyak_rating_user = banyak_rating_user[0]
        #ambil dari DB lalu convert ke dataframe pandas
        cursor = mysql.connection.cursor()
        cursor.execute('select username, anime_id, my_score, my_status from useranime')
        useranime = cursor.fetchall()
        ScoresDF = pd.DataFrame(useranime, columns=['username','anime_id','my_score','my_status'])
        print(ScoresDF)

        #### Membobotkan
        conditions = [
            (ScoresDF['my_status'] == 2),
            (ScoresDF['my_status'] == 3),
            (ScoresDF['my_status'] == 6),
            (ScoresDF['my_status'] == 1),
            (ScoresDF['my_status'] == 4)
        ]
        values = [5,1,2,4,2]
        ScoresDF['status_bobot'] = np.select(conditions,values)
        print(ScoresDF)
        ####

        # kf = KFold(n_splits = 5)

        #### Mengkalikan Rating dengan Status
        ScoresDF['scoreXstatus'] = ScoresDF['my_score'] * ScoresDF['status_bobot']
        ScoresDF[['scoreXstatus']] = MinMaxScaler().fit_transform(ScoresDF[['scoreXstatus']])
        # ScoresDF[['my_score']] = MinMaxScaler().fit_transform(ScoresDF[['my_score']])
        # print(ScoresDF)
        ####

        ## Training dan beri rekomendasi
        reader = Reader(rating_scale=(0,1))
        # if tipe_rekomendasi == "wcf":
        data = Dataset.load_from_df(ScoresDF[['username','anime_id','scoreXstatus']],reader)
        # elif tipe_rekomendasi == "cf":
            # data = Dataset.load_from_df(ScoresDF[['username','anime_id','my_score']],reader)
        trainset, testset = train_test_split(data, test_size=0.2, random_state=50)
        
        sim_options = {'name': 'pearson'}

        # cross_validate(KNNBasic(), data, cv=2)
        
               
        algo_knn = KNNBasic(min_k=min_k,k=max_k, sim_options=sim_options)
        # for trainset, testset in kf.split(data):
            # algo_knn.fit(trainset)
            # prediction_knn = algo_knn.test(testset)

        prediction_knn = algo_knn.fit(trainset).test(testset)
        # test = algo_knn.test(testset)

        pdTest = pd.DataFrame(prediction_knn, columns=['username','anime_id','rating_asli','rating_prediksi', 'details'])
        pdTest.to_csv('hasil_testing.csv', index=False)
        print(pdTest)
        mae = surprise.accuracy.mae(prediction_knn)
        rmse = surprise.accuracy.rmse(prediction_knn)
        
        print(mae)
        print(rmse)

        # print(type(surprise.accuracy.mae(prediction_knn)))
        surprise.accuracy.rmse(prediction_knn)

        ## Mendapatkan list rekomendasi
        # get the list of the movie ids
        unique_ids = ScoresDF['anime_id'].unique()

        # get the list of the ids that the username "user" has rated
        iids = ScoresDF.loc[ScoresDF['username'] == username, 'anime_id']

        # remove the rated anime for the recommendations
        anime_to_predict = np.setdiff1d(unique_ids,iids)

        user_recs = []
        for anime_id in anime_to_predict:
            user_recs.append((username, anime_id, algo_knn.predict(uid=username, iid=anime_id).est))
            # print(algo_knn.predict(uid=username, iid=anime_id))

        user_recommendations = pd.DataFrame(user_recs, columns=['username','anime_id', 'score']).sort_values('score', ascending=False)
        # print(user_recommendations.head(-20))

        # Insert nomor_rekomendasi
        cursor = mysql.connection.cursor()
        cursor.execute('INSERT into nomor_rekomendasi(tipe_rekomendasi,min_k,max_k,mae,rmse,banyak_rating_user) VALUES (%s,%s,%s,%s,%s,%s)', [tipe_rekomendasi,min_k,max_k,mae,rmse,banyak_rating_user])
        mysql.connection.commit()
        
        ## Get id_rekomend
        cursor = mysql.connection.cursor()
        cursor.execute('SELECT MAX(id_rekomendasi) FROM nomor_rekomendasi')
        max_id = cursor.fetchone()
        
        engine = create_engine('mysql+mysqlconnector://{0}:{1}@{2}/{3}'.format(db_username, db_password, db_host, db_name))
        user_recommendations = user_recommendations.head(10)

        # Insert history_rekomendasi
        user_recommendations['id_rekomendasi'] = max_id[0]
        user_recommendations = user_recommendations[['id_rekomendasi', 'username', 'anime_id','score']]
        print(user_recommendations)
        user_recommendations.to_sql("history_rekomendasi", con=engine, if_exists='append',index=False)

        return redirect(url_for("user_rekomendasi"))
    
    else:    
        return redirect("user_rekomendasi")

if __name__ == "__main__":
    app.run(debug=True)