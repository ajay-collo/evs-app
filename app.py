from flask import Flask, request, jsonify

app = Flask(__name__)

# Fake database (later use real DB)
users = {
    "student": {
        "STU2024001": "1234"
    }
}

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    role = data['role']
    identifier = data['identifier']
    password = data['password']

    if role in users and identifier in users[role]:
        if users[role][identifier] == password:
            return jsonify({"success": True, "redirect": f"/{role}_dashboard"})
    
    return jsonify({"success": False, "message": "Invalid credentials"})

if __name__ == '__main__':
    app.run(debug=True)


    @app.route('/login', methods=['POST'])
def login():
    ...
    return jsonify({"success": False, "message": "Invalid credentials"})


    @app.route('/login', methods=['POST'])
def login():
    data = request.json
    role = data['role']
    identifier = data['identifier']
    password = data['password']

    if role in users and identifier in users[role]:
        if users[role][identifier] == password:
            return jsonify({"success": True, "redirect": f"/{role}_dashboard"})
    
    return jsonify({"success": False, "message": "Invalid credentials"})


# ✅ ADD HERE ↓↓↓

@app.route('/student_dashboard')
def student_dashboard():
    return "Welcome Student Dashboard"

@app.route('/teacher_dashboard')
def teacher_dashboard():
    return "Welcome Teacher Dashboard"

@app.route('/admin_dashboard')
def admin_dashboard():
    return "Welcome Admin Dashboard"


#  KEEP THIS ALWAYS AT LAST
if __name__ == '__main__':
    app.run(debug=True)

    # ============================================================
#  app.py  —  Complete Flask Auth System
#  Covers: Login (3 roles), Session storage, Forgot Password
#  Database: MySQL   Backend: Python Flask
# ============================================================

from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_mysqldb import MySQL
import bcrypt
import secrets
import datetime
from functools import wraps

app = Flask(__name__)

# ─────────────────────────────────────────────
#  1. CONFIGURATION  (change these values)
# ─────────────────────────────────────────────
app.secret_key = 'change-this-to-a-long-random-string-123!'  # CHANGE THIS!

# MySQL connection settings — update with your college server details
app.config['MYSQL_HOST']     = 'localhost'        # or your server IP
app.config['MYSQL_USER']     = 'root'             # your MySQL username
app.config['MYSQL_PASSWORD'] = 'your_password'    # your MySQL password
app.config['MYSQL_DB']       = 'env_education'    # your database name
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'    # returns rows as dicts

mysql = MySQL(app)


# ─────────────────────────────────────────────
#  2. HELPER — login_required decorator
#  Use @login_required on any route that needs
#  the student/teacher/admin to be logged in
# ─────────────────────────────────────────────
def login_required(role=None):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash('Please log in first.', 'warning')
                return redirect(url_for('login'))
            if role and session.get('role') != role:
                flash('You do not have permission to access that page.', 'danger')
                return redirect(url_for('login'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator


# ─────────────────────────────────────────────
#  3. HOME PAGE
# ─────────────────────────────────────────────
@app.route('/')
def home():
    return render_template('index.html')


# ─────────────────────────────────────────────
#  4. LOGIN
#  POST /login  — receives { role, email/identifier, password }
#  Checks MySQL, verifies bcrypt hash, stores session
# ─────────────────────────────────────────────
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')

    # Read form data sent from login.html via fetch()
    data       = request.get_json()
    role       = data.get('role')          # 'student', 'teacher', or 'admin'
    identifier = data.get('identifier')    # email or student ID
    password   = data.get('password')

    if not role or not identifier or not password:
        return jsonify({'success': False, 'message': 'All fields are required.'})

    cur = mysql.connection.cursor()

    # Query the users table
    cur.execute(
        "SELECT * FROM users WHERE (email = %s OR student_id = %s) AND role = %s",
        (identifier, identifier, role)
    )
    user = cur.fetchone()
    cur.close()

    if not user:
        return jsonify({'success': False, 'message': 'User not found. Check your ID or email.'})

    # Check password using bcrypt
    password_correct = bcrypt.checkpw(
        password.encode('utf-8'),
        user['password_hash'].encode('utf-8')
    )

    if not password_correct:
        return jsonify({'success': False, 'message': 'Wrong password. Please try again.'})

    # ✅ Login successful — store in session
    session['user_id']   = user['id']
    session['user_name'] = user['name']
    session['role']      = user['role']
    session['email']     = user['email']
    session.permanent    = True  # keeps session alive after browser close

    # Redirect based on role
    redirects = {
        'student': '/student/dashboard',
        'teacher': '/teacher/dashboard',
        'admin':   '/admin/dashboard',
    }
    return jsonify({'success': True, 'redirect': redirects.get(role, '/')})


# ─────────────────────────────────────────────
#  5. LOGOUT
# ─────────────────────────────────────────────
@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))


# ─────────────────────────────────────────────
#  6. DASHBOARDS (protected routes)
#  Each dashboard checks login AND correct role
# ─────────────────────────────────────────────
@app.route('/student/dashboard')
@login_required(role='student')
def student_dashboard():
    return render_template('student_dashboard.html', user=session)


@app.route('/teacher/dashboard')
@login_required(role='teacher')
def teacher_dashboard():
    return render_template('teacher_dashboard.html', user=session)


@app.route('/admin/dashboard')
@login_required(role='admin')
def admin_dashboard():
    return render_template('admin_dashboard.html', user=session)


# ─────────────────────────────────────────────
#  7. FORGOT PASSWORD — Step 1
#  User submits their email
#  We generate a token, save it to DB, send email link
# ─────────────────────────────────────────────
@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'GET':
        return render_template('forgot_password.html')

    email = request.form.get('email', '').strip()
    if not email:
        flash('Please enter your email address.', 'danger')
        return redirect(url_for('forgot_password'))

    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM users WHERE email = %s", (email,))
    user = cur.fetchone()

    if not user:
        # Don't reveal whether email exists — security best practice
        flash('If that email exists, a reset link has been sent.', 'info')
        return redirect(url_for('forgot_password'))

    # Generate a secure random token (64 hex characters)
    token = secrets.token_hex(32)

    # Token expires in 1 hour
    expires_at = datetime.datetime.now() + datetime.timedelta(hours=1)

    # Save token to database
    cur.execute(
        "INSERT INTO password_resets (user_id, token, expires_at) VALUES (%s, %s, %s)",
        (user['id'], token, expires_at)
    )
    mysql.connection.commit()
    cur.close()

    # Build the reset link
    reset_link = url_for('reset_password', token=token, _external=True)

    # ── Send email ──────────────────────────────
    # Option A: Use Flask-Mail (recommended for college server)
    # Install: pip install Flask-Mail
    # Then uncomment and configure below:
    #
    # from flask_mail import Mail, Message
    # app.config['MAIL_SERVER']   = 'smtp.gmail.com'
    # app.config['MAIL_PORT']     = 587
    # app.config['MAIL_USE_TLS']  = True
    # app.config['MAIL_USERNAME'] = 'your_email@gmail.com'
    # app.config['MAIL_PASSWORD'] = 'your_app_password'  # Gmail App Password
    # mail = Mail(app)
    #
    # msg = Message(
    #     subject  = 'Reset your password – Environmental Education System',
    #     sender   = 'your_email@gmail.com',
    #     recipients = [email]
    # )
    # msg.body = f"""
    # Hello {user['name']},
    #
    # Click the link below to reset your password. This link expires in 1 hour.
    #
    # {reset_link}
    #
    # If you did not request this, ignore this email.
    # """
    # mail.send(msg)
    #
    # Option B: For testing — just print the link to terminal
    print(f"\n[DEV] Password reset link for {email}:\n{reset_link}\n")

    flash('If that email exists, a reset link has been sent.', 'info')
    return redirect(url_for('forgot_password'))


# ─────────────────────────────────────────────
#  8. RESET PASSWORD — Step 2
#  User clicks the link from email
#  We verify token, let them set new password
# ─────────────────────────────────────────────
@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    cur = mysql.connection.cursor()

    # Check token exists and has not expired
    cur.execute(
        "SELECT * FROM password_resets WHERE token = %s AND expires_at > NOW() AND used = 0",
        (token,)
    )
    reset_record = cur.fetchone()

    if not reset_record:
        flash('This reset link is invalid or has expired. Please request a new one.', 'danger')
        cur.close()
        return redirect(url_for('forgot_password'))

    if request.method == 'GET':
        cur.close()
        return render_template('reset_password.html', token=token)

    # POST — user submitted new password
    new_password = request.form.get('password', '')
    confirm      = request.form.get('confirm_password', '')

    if len(new_password) < 8:
        flash('Password must be at least 8 characters.', 'danger')
        return render_template('reset_password.html', token=token)

    if new_password != confirm:
        flash('Passwords do not match.', 'danger')
        return render_template('reset_password.html', token=token)

    # Hash the new password
    hashed = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    # Update user's password in the database
    cur.execute(
        "UPDATE users SET password_hash = %s WHERE id = %s",
        (hashed, reset_record['user_id'])
    )

    # Mark token as used so it can't be reused
    cur.execute(
        "UPDATE password_resets SET used = 1 WHERE token = %s",
        (token,)
    )

    mysql.connection.commit()
    cur.close()

    flash('Your password has been reset successfully. Please log in.', 'success')
    return redirect(url_for('login'))


# ─────────────────────────────────────────────
#  9. REGISTER A NEW USER (for admin use)
#  Call this once to create teacher/admin accounts
#  Or build an admin UI later
# ─────────────────────────────────────────────
@app.route('/register', methods=['POST'])
def register():
    data       = request.get_json()
    name       = data.get('name')
    email      = data.get('email')
    password   = data.get('password')
    role       = data.get('role')        # 'student', 'teacher', 'admin'
    student_id = data.get('student_id')  # only for students
    class_id   = data.get('class_id')    # only for students

    if not all([name, email, password, role]):
        return jsonify({'success': False, 'message': 'Missing required fields.'})

    # Hash the password — NEVER store plain text passwords!
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    cur = mysql.connection.cursor()
    try:
        cur.execute(
            """INSERT INTO users (name, email, password_hash, role, student_id, class_id)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            (name, email, hashed, role, student_id, class_id)
        )
        mysql.connection.commit()
        cur.close()
        return jsonify({'success': True, 'message': f'{role.capitalize()} registered successfully.'})
    except Exception as e:
        cur.close()
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})


# ─────────────────────────────────────────────
#  RUN
# ─────────────────────────────────────────────
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)