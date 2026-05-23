from flask import Flask, render_template, request, redirect, session, flash
import sqlite3
import os
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'perpustakaan'

UPLOAD_FOLDER = 'static/uploads'
PDF_FOLDER = 'static/pdf'

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['PDF_FOLDER'] = PDF_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PDF_FOLDER, exist_ok=True)

conn = sqlite3.connect('perpustakaan.db', check_same_thread=False)
cursor = conn.cursor()

# =========================
# DATABASE
# =========================

cursor.execute("""
CREATE TABLE IF NOT EXISTS user(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT,
    password TEXT,
    role TEXT,
    nim TEXT,
    whatsapp TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS buku(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nama TEXT,
    penulis TEXT,
    gambar TEXT,
    pdf TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS favorite(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    buku_id INTEGER
)
""")
conn.commit()

cursor.execute("""
CREATE TABLE IF NOT EXISTS pinjam(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    buku_id INTEGER,
    tanggal_pinjam TEXT,
    tanggal_kembali TEXT,
    status TEXT
)
""")

conn.commit()

# =========================
# ADMIN DEFAULT
# =========================

cursor.execute("SELECT * FROM user WHERE username='admin'")
cek = cursor.fetchone()

if not cek:

    password_hash = generate_password_hash('admin123')

    cursor.execute("""
    INSERT INTO user(username,password,role,nim,whatsapp)
    VALUES(?,?,?,?,?)
    """, ('admin', password_hash, 'admin', '-', '-'))

    conn.commit()

# =========================
# HOME
# =========================

@app.route('/')
def home():
    return render_template('index.html')

# =========================
# REGISTER
# =========================

@app.route('/register', methods=['GET','POST'])
def register():

    if request.method == 'POST':

        username = request.form['username']
        password = request.form['password']
        nim = request.form['nim']
        whatsapp = request.form['whatsapp']

        password_hash = generate_password_hash(password)

        cursor.execute("""
        INSERT INTO user(username,password,role,nim,whatsapp)
        VALUES(?,?,?,?,?)
        """, (username,password_hash,'user',nim,whatsapp))

        conn.commit()

        flash('Register berhasil')

        return redirect('/user-login')

    return render_template('register.html')

# =========================
# LOGIN
# =========================

@app.route('/login', methods=['GET','POST'])
def login():

    if request.method == 'POST':

        username = request.form['username']
        password = request.form['password']

        cursor.execute("SELECT * FROM user WHERE username=?", (username,))
        user = cursor.fetchone()

        if user and check_password_hash(user[2], password):

            session['login'] = True
            session['id'] = user[0]
            session['username'] = user[1]
            session['role'] = user[3]

            if user[3] == 'admin':
                return redirect('/dashboard')

            return redirect('/user')

        flash('Username atau password salah')

    return render_template('login.html')
# =========================
# LOGIN USER
# =========================

@app.route('/user-login', methods=['GET', 'POST'])
def user_login():

    if request.method == 'POST':

        username = request.form['username']
        password = request.form['password']

        cursor.execute(
            "SELECT * FROM user WHERE username=? AND role='user'",
            (username,)
        )

        user = cursor.fetchone()

        if user and check_password_hash(user[2], password):

            session['login'] = True
            session['id'] = user[0]
            session['username'] = user[1]
            session['role'] = user[3]

            return redirect('/user')

        flash('Username atau password salah')

    return render_template('user_login.html')
# =========================
# LOGOUT
# =========================

@app.route('/logout')
def logout():

    session.clear()

    return redirect('/login')

# =========================
# DASHBOARD ADMIN
# =========================

@app.route('/dashboard')
def dashboard():

    if 'login' not in session:
        return redirect('/login')

    cursor.execute("SELECT * FROM buku")
    buku = cursor.fetchall()

    cursor.execute("SELECT COUNT(*) FROM buku")
    total_buku = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM user")
    total_user = cursor.fetchone()[0]
    cursor.execute("SELECT id, username, nim, whatsapp FROM user")
    users = cursor.fetchall()
    print(users)
    cursor.execute("SELECT COUNT(*) FROM buku")
    total_buku = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM user")
    total_user = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM favorite")
    total_favorite = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM pinjam")
    total_pinjam = cursor.fetchone()[0]
    return render_template(
    'dashboard.html',
    buku=buku,
    users=users,
    total_buku=total_buku,
    total_user=total_user,
    total_favorite=total_favorite,
    total_pinjam=total_pinjam
)

# =========================
# DASHBOARD USER
# =========================

@app.route('/user')
def user():

    if 'login' not in session:
        return redirect('/login')

    cursor.execute("SELECT * FROM buku")
    buku = cursor.fetchall()

    return render_template(
    'user.html',
    buku_list=buku
)

# =========================
# TAMBAH BUKU
# =========================

@app.route('/tambah', methods=['GET','POST'])
def tambah():

    if request.method == 'POST':

        nama = request.form['nama']
        penulis = request.form['penulis']

        gambar = request.files['gambar']
        pdf = request.files['pdf']

        gambar_name = secure_filename(gambar.filename)
        pdf_name = secure_filename(pdf.filename)

        gambar.save(os.path.join(app.config['UPLOAD_FOLDER'], gambar_name))
        pdf.save(os.path.join(app.config['PDF_FOLDER'], pdf_name))

        cursor.execute("""
        INSERT INTO buku(nama,penulis,gambar,pdf)
        VALUES(?,?,?,?)
        """, (nama,penulis,gambar_name,pdf_name))

        conn.commit()

        flash('Buku berhasil ditambahkan')

        return redirect('/dashboard')

    return render_template('tambah.html')

# =========================
# EDIT
# =========================

@app.route('/edit/<int:id>', methods=['GET','POST'])
def edit(id):

    if request.method == 'POST':

        nama = request.form['nama']
        penulis = request.form['penulis']

        cursor.execute("""
        UPDATE buku
        SET nama=?, penulis=?
        WHERE id=?
        """, (nama,penulis,id))

        conn.commit()

        return redirect('/dashboard')

    cursor.execute("SELECT * FROM buku WHERE id=?", (id,))
    buku = cursor.fetchone()

    return render_template('edit.html', buku=buku)

# =========================
# HAPUS
# =========================

@app.route('/hapus/<int:id>')
def hapus(id):

    cursor.execute("DELETE FROM buku WHERE id=?", (id,))
    conn.commit()

    return redirect('/dashboard')

# =========================
# FAVORITE
# =========================

@app.route('/favorite/<int:id>')
def favorite(id):

    user_id = session['id']

    cursor.execute("""
    SELECT * FROM favorite
    WHERE user_id=? AND buku_id=?
    """, (user_id, id))

    cek = cursor.fetchone()

    if cek:
        flash('Buku sudah ada di favorite')
        return redirect('/user')

    cursor.execute("""
    INSERT INTO favorite(user_id,buku_id)
    VALUES(?,?)
    """, (user_id, id))

    conn.commit()

    flash('Ditambahkan ke favorite')

    return redirect('/user')

# =========================
# PINJAM
# =========================

@app.route('/pinjam/<int:id>')
def pinjam(id):

    user_id = session['id']

    tanggal_pinjam = datetime.now().strftime('%d-%m-%Y')

    tanggal_kembali = (
        datetime.now() + timedelta(days=7)
    ).strftime('%d-%m-%Y')

    cursor.execute("""
    INSERT INTO pinjam(user_id,buku_id,tanggal_pinjam,tanggal_kembali,status)
    VALUES(?,?,?,?,?)
    """, (
        user_id,
        id,
        tanggal_pinjam,
        tanggal_kembali,
        'Dipinjam'
    ))

    conn.commit()

    flash('Buku berhasil dipinjam')

    return redirect('/user')

# =========================
# RIWAYAT PINJAM
# =========================

@app.route('/pinjam-list')
def pinjam_list():

    user_id = session['id']

    cursor.execute("""
    SELECT buku.*
    FROM pinjam
    JOIN buku ON pinjam.buku_id = buku.id
    WHERE pinjam.user_id=?
    """, (user_id,))

    pinjam_buku = cursor.fetchall()

    return render_template(
        'pinjam.html',
        pinjam_buku=pinjam_buku
    )

# =========================
# BACA PDF
# =========================

@app.route('/baca/<int:id>')
def baca(id):

    cursor.execute("SELECT * FROM buku WHERE id=?", (id,))
    buku = cursor.fetchone()

    return redirect('/static/pdf/' + buku[4])

# =========================
# RUN
# =========================

# =========================
# FAVORITE LIST
# =========================

@app.route('/favorite-list')
def favorite_list():

    if 'login' not in session:
        return redirect('/login')

    user_id = session['id']

    cursor.execute("""
        SELECT buku.*
        FROM favorite
        JOIN buku ON favorite.buku_id = buku.id
        WHERE favorite.user_id=?
    """, (user_id,))

    favorit = cursor.fetchall()

    return render_template(
        'favorite.html',
        favorit=favorit
    )
# =========================
# HAPUS FAVORITE
# =========================

@app.route('/hapus-favorite/<int:id>')
def hapus_favorite(id):

    user_id = session['id']

    cursor.execute("""
    DELETE FROM favorite
    WHERE user_id=? AND buku_id=?
    """, (user_id, id))

    conn.commit()

    flash('Favorite dihapus')

    return redirect('/favorite-list')

app.run(debug=True)