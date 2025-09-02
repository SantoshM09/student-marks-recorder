from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import os
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

app = Flask(__name__)
app.secret_key = "change_this_to_random_secret"  # Change for production

# Use an absolute path for DB to avoid CWD issues in different runners
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE_DIR, 'database.db')
EXPORT_DIR = os.path.join(BASE_DIR, 'exports')
os.makedirs(EXPORT_DIR, exist_ok=True)
STUDENTS_EXPORT = os.path.join(EXPORT_DIR, 'students_data.txt')
USERS_EXPORT = os.path.join(EXPORT_DIR, 'user_accounts.txt')
LOGIN_EVENTS = os.path.join(EXPORT_DIR, 'login_events.txt')

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
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user'
        )
    ''')

    conn.commit()

    # Add email/role columns if they do not exist (for existing DBs)
    try:
        cols = conn.execute('PRAGMA table_info(users)').fetchall()
        col_names = {c['name'] for c in cols}
        if 'email' not in col_names:
            conn.execute('ALTER TABLE users ADD COLUMN email TEXT')
            conn.commit()
        if 'role' not in col_names:
            conn.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'user'")
            conn.commit()
        # Ensure existing 'admin' username keeps admin privileges (idempotent)
        conn.execute("UPDATE users SET role='admin' WHERE username='admin'")
        conn.commit()
    except Exception:
        pass

    # Aggregate statistics table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS stats (
            id INTEGER PRIMARY KEY CHECK(id=1),
            total_students INTEGER NOT NULL DEFAULT 0,
            avg_marks REAL,
            highest_marks INTEGER,
            lowest_marks INTEGER,
            updated_at TEXT
        )
    ''')
    # Ensure single row exists
    conn.execute('INSERT OR IGNORE INTO stats (id) VALUES (1)')

    # Grade distribution table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS grade_stats (
            grade TEXT PRIMARY KEY,
            count INTEGER NOT NULL DEFAULT 0
        )
    ''')

    conn.commit()

    # admin user
    cur = conn.execute("SELECT COUNT(*) as cnt FROM users").fetchone()
    if cur['cnt'] == 0:
        default_user = 'admin'
        default_pass = 'admin123'
        pw_hash = generate_password_hash(default_pass)
        conn.execute("INSERT INTO users (username, password_hash, role) VALUES (?, ?, 'admin')", (default_user, pw_hash))
        conn.commit()
        print("✅ Default admin created: username=admin password=admin123")
    conn.close()

init_db()


def recompute_statistics() -> None:
    """Recalculate aggregate student statistics and persist them.

    - Updates single-row `stats`
    - Rebuilds `grade_stats` from current `students` table
    """
    conn = get_db_connection()
    try:
        # Totals and aggregates
        totals = conn.execute('SELECT COUNT(*) AS total, AVG(marks) AS avg_m, MAX(marks) AS max_m, MIN(marks) AS min_m FROM students').fetchone()
        total_students = int(totals['total'] or 0)
        avg_marks = float(totals['avg_m']) if totals['avg_m'] is not None else None
        highest_marks = int(totals['max_m']) if totals['max_m'] is not None else None
        lowest_marks = int(totals['min_m']) if totals['min_m'] is not None else None

        conn.execute(
            'UPDATE stats SET total_students=?, avg_marks=?, highest_marks=?, lowest_marks=?, updated_at=datetime("now") WHERE id=1',
            (total_students, avg_marks, highest_marks, lowest_marks)
        )

        # Grade distribution (normalize NULL/blank grades to 'Unassigned')
        grade_rows = conn.execute(
            """
            SELECT COALESCE(NULLIF(TRIM(grade), ''), 'Unassigned') AS g, COUNT(*) AS count
            FROM students
            GROUP BY g
            """
        ).fetchall()

        conn.execute('DELETE FROM grade_stats')
        for row in grade_rows:
            conn.execute('INSERT INTO grade_stats (grade, count) VALUES (?, ?)', (row['g'], row['count']))

        conn.commit()
    finally:
        conn.close()

# Compute stats once at startup
recompute_statistics()

# ------------------------
# Text export helpers
# ------------------------
def export_students_to_text() -> None:
    conn = get_db_connection()
    try:
        rows = conn.execute('SELECT id, roll_number, name, email, subject, marks, grade FROM students ORDER BY roll_number').fetchall()
        lines = ["ID\tRoll\tName\tEmail\tSubject\tMarks\tGrade"]
        for r in rows:
            lines.append(f"{r['id']}\t{r['roll_number']}\t{r['name']}\t{r['email'] or ''}\t{r['subject']}\t{r['marks']}\t{r['grade'] or ''}")
        with open(STUDENTS_EXPORT, 'w', encoding='utf-8') as f:
            f.write("\n".join(lines) + "\n")
    finally:
        conn.close()

def export_users_to_text() -> None:
    conn = get_db_connection()
    try:
        rows = conn.execute('SELECT id, username, email, role FROM users ORDER BY id').fetchall()
        lines = ["ID\tUsername\tEmail\tRole"]
        for r in rows:
            lines.append(f"{r['id']}\t{r['username']}\t{r['email'] or ''}\t{r['role']}")
        with open(USERS_EXPORT, 'w', encoding='utf-8') as f:
            f.write("\n".join(lines) + "\n")
    finally:
        conn.close()

def append_login_event(user_id: int, username: str, role: str) -> None:
    from datetime import datetime
    line = f"{datetime.now().isoformat(timespec='seconds')}\tuser_id={user_id}\tusername={username}\trole={role}\n"
    with open(LOGIN_EVENTS, 'a', encoding='utf-8') as f:
        f.write(line)

# Initialize exports at startup
export_students_to_text()
export_users_to_text()
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
        identifier = request.form['username'].strip()
        password = request.form['password']
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username=? OR email=?', (identifier, identifier)).fetchone()
        conn.close()

        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role'] if 'role' in user.keys() else 'user'
            flash('Logged in successfully', 'success')
            try:
                append_login_event(user['id'], user['username'], (user['role'] if 'role' in user.keys() else 'user'))
            except Exception:
                pass
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'danger')
            return render_template('login.html')
    return render_template('login.html')


# Sign Up route
@app.route('/signup', methods=['GET', 'POST'])
@app.route('/register', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        confirm_password = request.form.get('confirm_password')
        email = request.form.get('email', '').strip()

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
        conn.execute("INSERT INTO users (username, password_hash, email, role) VALUES (?, ?, ?, 'user')", (username, pw_hash, email or None))
        conn.commit()
        conn.close()
        try:
            export_users_to_text()
        except Exception:
            pass
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
        new_email = request.form.get('email', '').strip()

        if new_username:
            # Ensure new username is unique
            existing = conn.execute('SELECT id FROM users WHERE username = ? AND id != ?', (new_username, user['id'])).fetchone()
            if existing:
                flash("Username already taken", "danger")
            else:
                conn.execute('UPDATE users SET username = ? WHERE id = ?', (new_username, user['id']))
                session['username'] = new_username
                flash("Username updated successfully", "success")

        if new_password:
            hashed_pw = generate_password_hash(new_password)
            conn.execute('UPDATE users SET password_hash = ? WHERE id = ?', (hashed_pw, user['id']))
            flash("Password updated successfully", "success")

        if new_email:
            conn.execute('UPDATE users SET email = ? WHERE id = ?', (new_email, user['id']))
            flash("Email updated successfully", "success")

        conn.commit()
        conn.close()
        return redirect(url_for('account'))

    conn.close()
    return render_template('account.html', user=user)


# API: Register (JSON)
@app.route('/api/register', methods=['POST'])
def api_register():
    if not request.is_json:
        return jsonify({"success": False, "message": "Expected JSON body"}), 400

    data = request.get_json(silent=True) or {}
    username = (data.get('username') or '').strip()
    password = data.get('password') or ''
    email = (data.get('email') or '').strip() or None

    if not username or not password:
        return jsonify({"success": False, "message": "Username and password are required"}), 400

    conn = get_db_connection()
    existing = conn.execute('SELECT id FROM users WHERE username = ?', (username,)).fetchone()
    if existing:
        conn.close()
        return jsonify({"success": False, "message": "Username already taken"}), 409

    pw_hash = generate_password_hash(password)
    conn.execute('INSERT INTO users (username, password_hash, email) VALUES (?, ?, ?)', (username, pw_hash, email))
    conn.commit()
    conn.close()

    return jsonify({"success": True, "message": "Account created"}), 201


# API: Login (JSON)
@app.route('/api/login', methods=['POST'])
def api_login():
    if not request.is_json:
        return jsonify({"success": False, "message": "Expected JSON body"}), 400

    data = request.get_json(silent=True) or {}
    username = (data.get('username') or '').strip()
    password = data.get('password') or ''

    if not username or not password:
        return jsonify({"success": False, "message": "Username and password are required"}), 400

    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE username=? OR email=?', (username, username)).fetchone()
    conn.close()

    if user and check_password_hash(user['password_hash'], password):
        session['user_id'] = user['id']
        session['username'] = user['username']
        session['role'] = user['role'] if 'role' in user.keys() else 'user'
        return jsonify({
            "success": True,
            "message": "Logged in",
            "user": {"id": user['id'], "username": user['username'], "email": user['email'], "role": (user['role'] if 'role' in user.keys() else 'user')}
        }), 200

    return jsonify({"success": False, "message": "Invalid username or password"}), 401

# Delete current account
@app.route('/account/delete', methods=['POST'])
@login_required
def delete_account():
    conn = get_db_connection()
    conn.execute('DELETE FROM users WHERE id = ?', (session['user_id'],))
    conn.commit()
    conn.close()
    session.clear()
    flash('Your account has been deleted', 'info')
    return redirect(url_for('login'))


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
                     (roll_number, name, email or None, subject, marks_int, grade or None))
        conn.commit()
        conn.close()
        # Update aggregate stats after insert
        recompute_statistics()
        try:
            export_students_to_text()
        except Exception:
            pass
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
                     (roll_number, name, email or None, subject, marks_int, grade or None, id))
        conn.commit()
        conn.close()
        # Update aggregate stats after update
        recompute_statistics()
        try:
            export_students_to_text()
        except Exception:
            pass
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
    # Update aggregate stats after delete
    recompute_statistics()
    try:
        export_students_to_text()
    except Exception:
        pass
    flash('Student record deleted', 'info')
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
@login_required
def dashboard():
    # Always refresh stats when dashboard loads
    recompute_statistics()

    conn = get_db_connection()
    students = conn.execute('SELECT * FROM students ORDER BY roll_number').fetchall()

    # Determine admin privileges robustly from DB (not just session)
    current_user = None
    if 'user_id' in session:
        current_user = conn.execute('SELECT role FROM users WHERE id=?', (session['user_id'],)).fetchone()
    is_admin = bool(current_user and (current_user['role'] == 'admin'))
    if is_admin:
        session['role'] = 'admin'

    s = conn.execute('SELECT total_students, avg_marks, highest_marks, lowest_marks FROM stats WHERE id=1').fetchone()
    total_students = s['total_students'] if s else 0
    avg_marks = s['avg_marks'] if s else None
    highest_marks = s['highest_marks'] if s else None
    lowest_marks = s['lowest_marks'] if s else None

    grade_data = conn.execute('SELECT grade, count FROM grade_stats').fetchall()

    conn.close()

    return render_template(
        'dashboard.html',
        students=students,
        total_students=total_students,
        avg_marks=avg_marks,
        highest_marks=highest_marks,
        lowest_marks=lowest_marks,
        grade_data=grade_data,
        is_admin=is_admin
    )

# Stats API (JSON)
@app.route('/stats', methods=['GET'])
@app.route('/stats/', methods=['GET'])
@app.route('/api/stats', methods=['GET'])
def stats_api():
    conn = get_db_connection()
    s = conn.execute('SELECT total_students, avg_marks, highest_marks, lowest_marks, updated_at FROM stats WHERE id=1').fetchone()
    grade_rows = conn.execute('SELECT grade, count FROM grade_stats').fetchall()
    conn.close()

    payload = {
        'total_students': (s['total_students'] if s and s['total_students'] is not None else 0),
        'avg_marks': (s['avg_marks'] if s and s['avg_marks'] is not None else 0),
        'highest_marks': (s['highest_marks'] if s and s['highest_marks'] is not None else 0),
        'lowest_marks': (s['lowest_marks'] if s and s['lowest_marks'] is not None else 0),
        'updated_at': (s['updated_at'] if s else None),
        'grade_distribution': [
            {'grade': row['grade'], 'count': row['count']} for row in grade_rows
        ]
    }

    return jsonify({'success': True, 'stats': payload}), 200


if __name__ == '__main__':
    app.run(debug=True)
