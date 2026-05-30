from urllib import response

from supabase import create_client

SUPABASE_URL = "https://ougnllblbwrzewqgskle.supabase.co"
SUPABASE_KEY = "sb_publishable_4HOP2wck9O7MoKdOjkYAsw_uR9kIOgf"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

from flask import Flask, render_template, request, redirect, session, flash, send_from_directory
import sqlite3
import os
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'perpustakaan'

@app.route('/baca/<filename>')
def baca(filename):
    return send_from_directory('/tmp/pdf', filename)

@app.route('/gambar/<filename>')
def gambar(filename):
    return send_from_directory('/tmp/uploads', filename)

UPLOAD_FOLDER = '/tmp/uploads'
PDF_FOLDER = '/tmp/pdf'

app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['PDF_FOLDER'] = 'pdf'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['PDF_FOLDER'] = PDF_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PDF_FOLDER, exist_ok=True)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

db_path = '/tmp/perpustakaan.db'

if not os.path.exists(db_path):
    import shutil
    shutil.copy('perpustakaan.db', db_path)

conn = sqlite3.connect(db_path, check_same_thread=False)
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

    return redirect('/user-login')

@app.route('/logout_admin')
def logout_admin():
    session.clear()
    return redirect('/login')

# =========================
# DASHBOARD ADMIN
# =========================

@app.route('/dashboard')
def dashboard():

    if 'login' not in session:
        return redirect('/login')

    buku_res = supabase.table("buku").select("*").execute()
    buku = buku_res.data

    total_buku = len(buku)

    cursor.execute("SELECT COUNT(*) FROM user")
    total_user = cursor.fetchone()[0]

    cursor.execute("SELECT id, username, nim, whatsapp FROM user")
    users = cursor.fetchall()

    cursor.execute("SELECT COUNT(*) FROM favorite")
    total_favorite = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM pinjam")
    total_pinjam = cursor.fetchone()[0]

    return render_template(
        "dashboard.html",
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

    response = supabase.table("buku").select("*").execute()
    buku = response.data

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

        from datetime import datetime

        gambar_name = f"{int(datetime.now().timestamp())}_{secure_filename(gambar.filename)}"
        pdf_name = f"{int(datetime.now().timestamp())}_{secure_filename(pdf.filename)}"

        supabase.storage.from_("books").upload(
        f"gambar/{gambar_name}",
        gambar.read(),
        {"content-type": gambar.content_type}
        )

        supabase.storage.from_("books").upload(
        f"pdf/{pdf_name}",
        pdf.read(),
        {"content-type": "application/pdf"}
        )

        supabase.table("buku").insert({
            "nama": nama,
            "penulis": penulis,
            "gambar": gambar_name,
            "pdf": pdf_name
        }).execute()
    
        flash('Buku berhasil ditambahkan')

        return redirect('/dashboard')

    return render_template('tambah.html')

# =========================
# EDIT
# =========================

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit(id):

    if request.method == 'POST':

        nama = request.form['nama']
        penulis = request.form['penulis']

        supabase.table("buku").update({
            "nama": nama,
            "penulis": penulis
        }).eq("id", id).execute()

        flash("Buku berhasil diupdate")

        return redirect('/dashboard')

    res = supabase.table("buku").select("*").eq("id", id).execute()

    buku = res.data[0]

    return render_template(
        "edit.html",
        buku=buku
    )
# =========================
# HAPUS
# =========================

@app.route('/hapus/<int:id>')
def hapus(id):

    hasil = supabase.table("buku").delete().eq("id", id).execute()

    print(hasil)

    flash("Buku berhasil dihapus")

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

    cursor.execute(
        "SELECT buku_id FROM pinjam WHERE user_id=?",
        (user_id,)
    )

    ids = [x[0] for x in cursor.fetchall()]

    pinjam_buku = []

    if ids:
        res = supabase.table("buku").select("*").execute()

        for b in res.data:
            if b["id"] in ids:
                pinjam_buku.append(b)

    return render_template(
        "pinjam.html",
        pinjam_buku=pinjam_buku
    )
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

    cursor.execute(
        "SELECT buku_id FROM favorite WHERE user_id=?",
        (user_id,)
    )

    ids = [x[0] for x in cursor.fetchall()]

    favorit = []

    if ids:
        res = supabase.table("buku").select("*").execute()

        for b in res.data:
            if b["id"] in ids:
                favorit.append(b)

    return render_template(
        "favorite.html",
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

if __name__ == "__main__":
    app.run(debug=True)