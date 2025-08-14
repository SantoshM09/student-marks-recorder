from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

app = Flask(__name__)
app.secret_key = "change_this_to_random_secret"  # Change for production

DB = 'database.db'

# Database connection
def get_db_connection():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

# Initialize database
def init_db():
    conn = get_db_connection()

    # Students table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            roll_number TEXT NOT NULL,
            name TEXT NOT NULL,
            email TEXT,
            subject TEXT NOT NULL,
            marks INTEGER NOT NULL,
            grade TEXT
        )
    ''')

    # Admin users table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        )
    ''')

    conn.commit()

    # Default admin user
    cur = conn.execute("SELECT COUNT(*) as cnt FROM users").fetchone()
    if cur['cnt'] == 0:
        default_user = 'admin'
        default_pass = 'admin123'
        pw_hash = generate_password_hash(default_pass)
        conn.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (default_user, pw_hash))
        conn.commit()
        print("✅ Default admin created: username=admin password=admin123")
    conn.close()

init_db()

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Routes
@app.route('/')
def home():
    return redirect(url_for('login'))

# Login route
@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username=?', (username,)).fetchone()
        conn.close()

        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            flash('Logged in successfully', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'danger')
            return render_template('login.html')
    return render_template('login.html')


# Sign Up route
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        confirm_password = request.form.get('confirm_password')

        if not username or not password:
            flash('Username and password are required', 'warning')
            return render_template('signup.html')

        if confirm_password is not None and password != confirm_password:
            flash('Passwords do not match', 'danger')
            return render_template('signup.html')

        conn = get_db_connection()
        existing = conn.execute('SELECT id FROM users WHERE username = ?', (username,)).fetchone()
        if existing:
            conn.close()
            flash('Username already taken', 'danger')
            return render_template('signup.html')

        pw_hash = generate_password_hash(password)
        conn.execute('INSERT INTO users (username, password_hash) VALUES (?, ?)', (username, pw_hash))
        conn.commit()
        conn.close()
        flash('Account created successfully. Please log in.', 'success')
        return redirect(url_for('login'))

    return render_template('signup.html')


@app.route('/account', methods=['GET', 'POST'])
@login_required
def account():
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()

    if request.method == 'POST':
        new_username = request.form.get('username')
        new_password = request.form.get('password')

        if new_username:
            conn.execute('UPDATE users SET username = ? WHERE id = ?', (new_username, user['id']))
            flash("Username updated successfully", "success")

        if new_password:
            hashed_pw = generate_password_hash(new_password)
            conn.execute('UPDATE users SET password_hash = ? WHERE id = ?', (hashed_pw, user['id']))
            flash("Password updated successfully", "success")

        conn.commit()
        conn.close()
        return redirect(url_for('account'))

    conn.close()
    return render_template('account.html', user=user)


# Logout
@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('login'))

# Dashboard (with stats)

# Add student
@app.route('/add', methods=['GET','POST'])
@login_required
def add_student():
    if request.method == 'POST':
        roll_number = request.form['roll_number'].strip()
        name = request.form['name'].strip()
        email = request.form['email'].strip()
        subject = request.form['subject'].strip()
        marks = request.form['marks'].strip()
        grade = request.form['grade'].strip()

        if not (roll_number and name and subject and marks):
            flash('Please fill required fields', 'warning')
            return render_template('add.html')

        try:
            marks_int = int(marks)
        except ValueError:
            flash('Marks must be an integer', 'warning')
            return render_template('add.html')

        conn = get_db_connection()
        conn.execute('INSERT INTO students (roll_number, name, email, subject, marks, grade) VALUES (?, ?, ?, ?, ?, ?)',
                     (roll_number, name, email, subject, marks_int, grade))
        conn.commit()
        conn.close()
        flash('Student added successfully', 'success')
        return redirect(url_for('dashboard'))

    return render_template('add.html')

# Edit student
@app.route('/edit/<int:id>', methods=['GET','POST'])
@login_required
def edit_student(id):
    conn = get_db_connection()
    student = conn.execute('SELECT * FROM students WHERE id=?', (id,)).fetchone()
    if not student:
        conn.close()
        flash('Record not found', 'danger')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        roll_number = request.form['roll_number'].strip()
        name = request.form['name'].strip()
        email = request.form['email'].strip()
        subject = request.form['subject'].strip()
        marks = request.form['marks'].strip()
        grade = request.form['grade'].strip()

        if not (roll_number and name and subject and marks):
            flash('Please fill required fields', 'warning')
            return render_template('edit.html', student=student)

        try:
            marks_int = int(marks)
        except ValueError:
            flash('Marks must be an integer', 'warning')
            return render_template('edit.html', student=student)

        conn.execute('UPDATE students SET roll_number=?, name=?, email=?, subject=?, marks=?, grade=? WHERE id=?',
                     (roll_number, name, email, subject, marks_int, grade, id))
        conn.commit()
        conn.close()
        flash('Student updated successfully', 'success')
        return redirect(url_for('dashboard'))

    conn.close()
    return render_template('edit.html', student=student)

# Delete student
@app.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete_student(id):
    conn = get_db_connection()
    conn.execute('DELETE FROM students WHERE id=?', (id,))
    conn.commit()
    conn.close()
    flash('Student record deleted', 'info')
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
@login_required
def dashboard():
    conn = get_db_connection()
    students = conn.execute('SELECT * FROM students ORDER BY roll_number').fetchall()

    # Stats
    total_students = len(students)
    avg_marks = conn.execute('SELECT AVG(marks) as avg FROM students').fetchone()['avg']
    highest_marks = conn.execute('SELECT MAX(marks) as max FROM students').fetchone()['max']
    lowest_marks = conn.execute('SELECT MIN(marks) as min FROM students').fetchone()['min']

    # Grade distribution
    grade_data = conn.execute(
        'SELECT grade, COUNT(*) as count FROM students GROUP BY grade'
    ).fetchall()

    conn.close()

    return render_template(
        'dashboard.html',
        students=students,
        total_students=total_students,
        avg_marks=avg_marks,
        highest_marks=highest_marks,
        lowest_marks=lowest_marks,
        grade_data=grade_data
    )


if __name__ == '__main__':
    app.run(debug=True)
