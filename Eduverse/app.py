from flask import Flask, render_template, request, redirect, session
import sqlite3
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "eduverse_secret"

UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs("static/materials", exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


# ---------------- DATABASE SETUP ----------------
def init_db():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    # Users
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT,
            password TEXT,
            role TEXT
        )
    ''')

    # Courses
    c.execute('''
        CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_name TEXT,
            teacher TEXT
        )
    ''')

    # Enrollments
    c.execute('''
        CREATE TABLE IF NOT EXISTS enrollments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student TEXT,
            course_id INTEGER
        )
    ''')

    # Videos (FIXED with course_id)
    c.execute('''
        CREATE TABLE IF NOT EXISTS videos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            video_type TEXT,
            link TEXT,
            teacher TEXT,
            course_id INTEGER
        )
    ''')

    # Materials
    c.execute('''
        CREATE TABLE IF NOT EXISTS materials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            file_path TEXT,
            teacher TEXT,
            course_id INTEGER
        )
    ''')

    conn.commit()
    conn.close()

init_db()


# ---------------- HOME ----------------
@app.route('/')
def home():
    return redirect('/login')


# ---------------- REGISTER ----------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == "POST":
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']

        conn = sqlite3.connect("database.db")
        c = conn.cursor()
        c.execute("INSERT INTO users (name,email,password,role) VALUES (?,?,?,?)",
                  (name,email,password,role))
        conn.commit()
        conn.close()

        return redirect('/login')

    return render_template("register.html")


# ---------------- LOGIN ----------------
@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == "POST":
        email = request.form['email']
        password = request.form['password']

        conn = sqlite3.connect("database.db")
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE email=? AND password=?",
                  (email,password))
        user = c.fetchone()
        conn.close()

        if user:
            session['user'] = user[1]
            session['role'] = user[4]

            if user[4] == "student":
                return redirect('/student')
            elif user[4] == "teacher":
                return redirect('/teacher')
            elif user[4] == "admin":
                return redirect('/admin')

        return "Invalid Credentials"

    return render_template("login.html")


# ---------------- STUDENT DASHBOARD ----------------
@app.route('/student')
def student_dashboard():
    if 'user' not in session or session['role'] != 'student':
        return redirect('/login')

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("SELECT * FROM courses")
    courses = c.fetchall()

    c.execute("""
        SELECT videos.* FROM videos
        JOIN enrollments 
        ON videos.course_id = enrollments.course_id
        WHERE enrollments.student = ?
    """, (session['user'],))
    videos = c.fetchall()

    c.execute("""
        SELECT materials.* FROM materials
        JOIN enrollments
        ON materials.course_id = enrollments.course_id
        WHERE enrollments.student = ?
    """, (session['user'],))
    materials = c.fetchall()

    conn.close()

    return render_template("student_home.html",
                           name=session['user'],
                           courses=courses,
                           videos=videos,
                           materials=materials)


# ---------------- TEACHER DASHBOARD ----------------
@app.route('/teacher')
def teacher_dashboard():
    if 'user' not in session or session['role'] != 'teacher':
        return redirect('/login')

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("SELECT * FROM courses WHERE teacher=?", (session['user'],))
    courses = c.fetchall()

    conn.close()

    return render_template("teacher_home.html",
                           name=session['user'],
                           courses=courses)


# ---------------- ADD COURSE ----------------
@app.route('/add_course', methods=['POST'])
def add_course():
    course_name = request.form['course_name']

    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("INSERT INTO courses (course_name, teacher) VALUES (?,?)",
              (course_name, session['user']))
    conn.commit()
    conn.close()

    return redirect('/teacher')


# ---------------- ADD YOUTUBE VIDEO ----------------
@app.route('/add_youtube', methods=['POST'])
def add_youtube():
    title = request.form['title']
    link = request.form['link']
    course_id = request.form['course_id']

    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("""
        INSERT INTO videos (title, video_type, link, teacher, course_id)
        VALUES (?, ?, ?, ?, ?)
    """, (title, "youtube", link, session['user'], course_id))
    conn.commit()
    conn.close()

    return redirect('/teacher')


# ---------------- UPLOAD VIDEO FILE ----------------
@app.route('/upload_video', methods=['POST'])
def upload_video():
    title = request.form['title']
    course_id = request.form['course_id']
    file = request.files['video']

    if file:
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        conn = sqlite3.connect("database.db")
        c = conn.cursor()
        c.execute("""
            INSERT INTO videos (title, video_type, link, teacher, course_id)
            VALUES (?, ?, ?, ?, ?)
        """, (title, "file", filepath, session['user'], course_id))
        conn.commit()
        conn.close()

    return redirect('/teacher')


# ---------------- UPLOAD MATERIAL ----------------
@app.route('/upload_material', methods=['POST'])
def upload_material():
    title = request.form['title']
    course_id = request.form['course_id']
    file = request.files['material']

    if file:
        filename = secure_filename(file.filename)
        filepath = os.path.join("static/materials", filename)
        file.save(filepath)

        conn = sqlite3.connect("database.db")
        c = conn.cursor()
        c.execute("""
            INSERT INTO materials (title, file_path, teacher, course_id)
            VALUES (?, ?, ?, ?)
        """, (title, filepath, session['user'], course_id))
        conn.commit()
        conn.close()

    return redirect('/teacher')


# ---------------- ADMIN ----------------
@app.route('/admin')
def admin_dashboard():
    if 'user' not in session or session['role'] != 'admin':
        return redirect('/login')

    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("SELECT * FROM users")
    users = c.fetchall()
    conn.close()

    return render_template("admin_home.html",
                           name=session['user'],
                           users=users)


# ---------------- LOGOUT ----------------
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')


if __name__ == "__main__":
    app.run(debug=True)