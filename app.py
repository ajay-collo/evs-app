from flask import Flask, render_template, request, redirect, session, jsonify, url_for
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg2
import psycopg2.extras
import qrcode
import os
import secrets

app = Flask(__name__, template_folder='templates')
app.secret_key = "super_secret_session_key_synopsis_compliant_v21"

# ========================================================
# OPTIMIZED POSTGRESQL DATABASE CONNECTION POOL PATTERN
# ========================================================
def get_db_connection():
    return psycopg2.connect(
        dbname="env_education",
        user="postgres",
        password="@anu_0809", 
        host="localhost"
    )

# ========================================================
# AUTO-RECOVERABLE TRANSACTIONS INITIALIZATION
# ========================================================
def init_db():
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255),
                email VARCHAR(255) UNIQUE,
                password VARCHAR(255),
                role VARCHAR(50),
                student_id VARCHAR(100),
                gender VARCHAR(50),
                department VARCHAR(100)
            )
            ''')
            
            cur.execute('''
            CREATE TABLE IF NOT EXISTS activities (
                id SERIAL PRIMARY KEY,
                teacher_id INTEGER,
                title VARCHAR(255),
                description TEXT,
                token VARCHAR(100) UNIQUE,
                task_url TEXT,
                qr_code_path TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')

            cur.execute('''
            CREATE TABLE IF NOT EXISTS submissions (
                id SERIAL PRIMARY KEY,
                activity_id INTEGER,
                student_id INTEGER,
                photo_path TEXT,
                video_path TEXT,
                pdf_path TEXT,
                status VARCHAR(50) DEFAULT 'Pending',
                submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')

            cur.execute('''
            CREATE TABLE IF NOT EXISTS activity_attendance (
                id SERIAL PRIMARY KEY,
                activity_id INTEGER,
                student_id INTEGER,
                is_present BOOLEAN DEFAULT TRUE,
                UNIQUE(activity_id, student_id)
            )
            ''')

            cur.execute('''
            CREATE TABLE IF NOT EXISTS course_enrollments (
                id SERIAL PRIMARY KEY,
                student_id INTEGER,
                teacher_id INTEGER,
                enrolled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(student_id, teacher_id)
            )
            ''')
            conn.commit()

    for col_name in ["video_path", "pdf_path"]:
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(f"ALTER TABLE submissions ADD COLUMN {col_name} TEXT;")
                    conn.commit()
        except Exception:
            pass

    admin_hashed_password = generate_password_hash('admin123')
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('''
                INSERT INTO users (name, email, password, role, department) 
                VALUES ('College Admin', 'admin@college.com', %s, 'admin', 'Management') 
                ON CONFLICT (email) DO UPDATE SET password = EXCLUDED.password;
            ''', (admin_hashed_password,))
            conn.commit()
            
    os.makedirs('static/qrcodes', exist_ok=True)
    os.makedirs('static/uploads', exist_ok=True)

init_db()

# ========================================================
# SECURITY GATED AUTHENTICATION ROUTINES
# ========================================================
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')
        
    data = request.get_json()
    identifier = data.get('identifier')
    password = data.get('password')
    role = data.get('role')

    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute(
                "SELECT * FROM users WHERE (email=%s OR student_id=%s) AND role=%s",
                (identifier, identifier, role)
            )
            user = cur.fetchone()

    if user and (check_password_hash(user['password'], password) or user['password'] == password):
        session['id'] = user['id']
        session['user'] = user['name']
        session['role'] = user['role']
        session['student_id'] = user.get('student_id', 'N/A')

        if 'next_task_url' in session:
            return jsonify({"success": True, "redirect": session.pop('next_task_url')})
            
        redirects = {'student': '/dashboard/student', 'teacher': '/dashboard/teacher', 'admin': '/dashboard/admin'}
        return jsonify({"success": True, "redirect": redirects.get(role, '/login')})

    return jsonify({"success": False, "message": "Invalid credentials provided."}), 401

@app.route('/student_register')
def student_register_page():
    invite = request.args.get('invite', '')
    if invite:
        session['invite_teacher_id'] = invite
    return render_template('student_register.html')

@app.route('/register/student', methods=['POST'])
def student_register():
    data = request.get_json()
    hashed_password = generate_password_hash(data.get('password'))
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO users(name, email, password, role, student_id, gender, department) VALUES(%s, %s, %s, %s, %s, %s, %s) RETURNING id",
                    (data.get('full_name'), data.get('email'), hashed_password, 'student', data.get('s_id'), data.get('gender'), data.get('department'))
                )
                new_student_id = cur.fetchone()[0]
                
                session['id'] = new_student_id
                session['user'] = data.get('full_name')
                session['role'] = 'student'
                session['student_id'] = data.get('s_id')

                invite_teacher_id = session.pop('invite_teacher_id', None)
                if invite_teacher_id:
                    cur.execute(
                        "INSERT INTO course_enrollments (student_id, teacher_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                        (new_student_id, int(invite_teacher_id))
                    )

                if 'next_task_url' in session:
                    target_url = session.pop('next_task_url')
                    token = target_url.split('/')[-1]
                    
                    cur.execute("SELECT id FROM activities WHERE token = %s", (token,))
                    act_data = cur.fetchone()
                    if act_data:
                        cur.execute(
                            "INSERT INTO activity_attendance (activity_id, student_id, is_present) VALUES (%s, %s, TRUE) ON CONFLICT DO NOTHING",
                            (act_data[0], new_student_id)
                        )
                    return jsonify({"success": True, "redirect": target_url})
                    
        return jsonify({"success": True, "redirect": "/login"})
    except Exception:
        return jsonify({"success": False, "message": "Email or Roll Number already exists!"}), 400

@app.route('/teacher_register')
def teacher_register_page():
    return render_template('teacher_register.html')

@app.route('/register/teacher', methods=['POST'])
def teacher_register():
    data = request.get_json()
    hashed_password = generate_password_hash(data.get('password'))
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO users(name, email, password, role, gender, department) VALUES(%s, %s, %s, %s, %s, %s) RETURNING id",
                    (data.get('full_name'), data.get('email'), hashed_password, 'teacher', data.get('gender'), data.get('department'))
                )
                new_teacher_id = cur.fetchone()[0]
                
                session['id'] = new_teacher_id
                session['user'] = data.get('full_name')
                session['role'] = 'teacher'
                session['student_id'] = 'N/A'
                
        return jsonify({"success": True, "redirect": "/dashboard/teacher"})
    except Exception:
        return jsonify({"success": False, "message": "Official Faculty Email already registered in console!"}), 400

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

# ========================================================
# CENTRAL ADMIN MANAGEMENT CONSOLE
# ========================================================
@app.route('/dashboard/admin')
def admin_dashboard():
    if 'user' not in session or session.get('role') != 'admin':
        return redirect('/login')
        
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute("SELECT COUNT(*) FROM users WHERE role = 'student'")
            total_students = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM users WHERE role = 'teacher'")
            total_teachers = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM activities")
            total_activities = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM submissions")
            total_submissions = cur.fetchone()[0]
            
            cur.execute("SELECT id, name, email, department, gender FROM users WHERE role = 'teacher' ORDER BY name")
            teachers_list = cur.fetchall()
            
            cur.execute("SELECT id, name, email, student_id, department, gender FROM users WHERE role = 'student' ORDER BY name")
            students_list = cur.fetchall()
            
    teacher_rows = ""
    for t in teachers_list:
        teacher_rows += f"""
        <tr>
            <td class="fw-semibold ps-3 text-dark">{t['name']}</td>
            <td>{t['email']}</td>
            <td><span class="badge bg-success">{t['department'] if t['department'] else 'General'}</span></td>
            <td>{str(t['gender']).capitalize() if t['gender'] else 'N/A'}</td>
            <td><span class="text-success fw-bold">Active ✓</span></td>
        </tr>
        """
        
    student_rows = ""
    for s in students_list:
        student_rows += f"""
        <tr>
            <td class="fw-semibold ps-3 text-dark">{s['name']}</td>
            <td><code>{s['student_id'] if s['student_id'] else 'N/A'}</code></td>
            <td>{s['email']}</td>
            <td><span class="badge bg-secondary">{s['department'] if s['department'] else 'General'}</span></td>
            <td>{str(s['gender']).capitalize() if s['gender'] else 'N/A'}</td>
        </tr>
        """
            
    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Admin Infrastructure Dashboard | Central Control</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    </head>
    <body>
        <nav class="navbar navbar-expand-lg navbar-dark bg-dark mb-4 shadow-sm">
            <div class="container">
                <a class="navbar-brand fw-bold" href="#">⚙️ Central Admin Management System</a>
                <div class="navbar-nav ms-auto">
                    <a class="btn btn-sm btn-outline-light px-3" href="/logout">Logout</a>
                </div>
            </div>
        </nav>
        <div class="container mb-5">
            <h2 class="fw-bold text-dark mb-4">⚡ Central Infrastructure Control Overview</h2>
            <div class="table-container mb-4">
                <button onclick="exportTableToCSV('teacherTable', 'Faculty_Registry_Report.csv')" class="btn btn-sm btn-primary fw-bold px-3 mb-2">📥 Export Faculty Registry (CSV)</button>
                <table id="teacherTable" class="table table-hover align-middle mb-0">
                    <thead class="table-dark"><tr><th>Teacher Name</th><th>Email</th><th>Department</th><th>Gender</th><th>Status</th></tr></thead>
                    <tbody>{teacher_rows}</tbody>
                </table>
            </div>
            <div class="table-container">
                <button onclick="exportTableToCSV('studentTable', 'Student_Registry_Report.csv')" class="btn btn-sm btn-success fw-bold px-3 mb-2">📥 Export Student Registry (CSV)</button>
                <table id="studentTable" class="table table-hover align-middle mb-0">
                    <thead class="table-dark"><tr><th>Student Full Name</th><th>ID</th><th>Email</th><th>Department</th><th>Gender</th></tr></thead>
                    <tbody>{student_rows}</tbody>
                </table>
            </div>
        </div>
        <script>
        function exportTableToCSV(tableId, filename) {{
            let csv = [];
            let rows = document.querySelectorAll("#" + tableId + " tr");
            for (let i = 0; i < rows.length; i++) {{
                let row = [], cols = rows[i].querySelectorAll("td, th");
                for (let j = 0; j < cols.length; j++) row.push(cols[j].innerText.replace(/,/g, "").trim());
                csv.push(row.join(","));
            }}
            let csvFile = new Blob([csv.join("\\n")], {{ type: "text/csv;charset=utf-8;" }});
            let downloadLink = document.createElement("a");
            downloadLink.download = filename;
            downloadLink.href = window.URL.createObjectURL(csvFile);
            downloadLink.click();
        }}
        </script>
    </body>
    </html>
    """

# ========================================================
# STUDENT DASHBOARD ROUTINE
# ========================================================
@app.route('/dashboard/student')
def student_dashboard():
    if 'user' not in session or session.get('role') != 'student':
        return redirect('/login')
        
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute('''
                SELECT s.photo_path, s.video_path, s.pdf_path, s.status, s.submitted_at, a.title as activity_title
                FROM submissions s JOIN activities a ON s.activity_id = a.id
                WHERE s.student_id = %s ORDER BY s.submitted_at DESC;
            ''', (session['id'],))
            my_submissions = cur.fetchall()
    
    total = len(my_submissions)
    approved = sum(1 for s in my_submissions if s['status'] and str(s['status']).strip().lower() == 'approved')
    pending = sum(1 for s in my_submissions if s['status'] and str(s['status']).strip().lower() == 'pending')
    rejected = sum(1 for s in my_submissions if s['status'] and str(s['status']).strip().lower() == 'rejected')
    
    raw_rate = (approved / total * 100) if total > 0 else 0.0
    approval_rate = f"{round(raw_rate, 1)}%"
    hours_logged = round(approved * 1.5, 1)

    return render_template(
        'student_dashboard.html', 
        user={"user_name": session['user']}, 
        submissions=my_submissions, 
        total=total, 
        approved=approved, 
        pending=pending, 
        rejected=rejected,
        approval_rate=approval_rate,
        hours_logged=hours_logged
    )

# ========================================================
# TEACHER DASHBOARD ROUTINE
# ========================================================
@app.route('/dashboard/teacher')
def teacher_dashboard():
    if 'user' not in session or session.get('role') != 'teacher':
        return redirect('/login')
        
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute("SELECT * FROM activities WHERE teacher_id = %s ORDER BY id DESC", (session['id'],))
            activities = cur.fetchall()
            
            cur.execute('''
                SELECT u.id, u.name, u.student_id, u.department, 
                       COUNT(s.id) AS total_submissions
                FROM users u
                JOIN course_enrollments ce ON u.id = ce.student_id AND ce.teacher_id = %s
                LEFT JOIN submissions s ON u.id = s.student_id 
                     AND s.activity_id IN (SELECT id FROM activities WHERE teacher_id = %s)
                WHERE u.role = 'student'
                GROUP BY u.id, u.name, u.student_id, u.department
                ORDER BY u.name;
            ''', (session['id'], session['id']))
            students = cur.fetchall()
            
            cur.execute('''
                SELECT s.id as submission_id, s.status, s.photo_path, s.video_path, s.pdf_path, s.submitted_at,
                       u.name as student_name, u.student_id as roll_no, a.title as activity_title
                FROM submissions s
                JOIN users u ON s.student_id = u.id
                JOIN activities a ON s.activity_id = a.id
                WHERE a.teacher_id = %s
                ORDER BY s.submitted_at DESC
            ''', (session['id'],))
            field_submissions = cur.fetchall()
            
            cur.execute("SELECT COUNT(*) FROM course_enrollments WHERE teacher_id = %s", (session['id'],))
            total_students = cur.fetchone()[0] or 1
            total_submissions = len(field_submissions)
            
            cur.execute('''
                SELECT COUNT(*) FROM activity_attendance aa
                JOIN activities a ON aa.activity_id = a.id
                WHERE a.teacher_id = %s AND aa.is_present = TRUE
            ''', (session['id'],))
            present_count = cur.fetchone()[0]
            
    attendance_rate = round((present_count / (total_students * (len(activities) or 1))) * 100, 1)
    if attendance_rate > 100: attendance_rate = 100
    growth_rate = round((total_submissions / (len(activities) or 1)) * 10, 1)

    chart_labels = []
    chart_values = []
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute('''
                SELECT a.title, COUNT(s.id) as sub_count FROM activities a 
                LEFT JOIN submissions s ON a.id = s.activity_id 
                WHERE a.teacher_id = %s GROUP BY a.id, a.title ORDER BY a.id DESC LIMIT 5
            ''', (session['id'],))
            chart_rows = cur.fetchall()
            chart_labels = [row['title'] for row in chart_rows][::-1]
            chart_values = [row['sub_count'] for row in chart_rows][::-1]
    
    stats = {
        "total_students": total_students,
        "total_submissions": total_submissions,
        "attendance_rate": f"{attendance_rate}%",
        "growth_rate": f"+{growth_rate}%",
        "chart_labels": chart_labels,
        "chart_values": chart_values
    }
    
    invite_link = f"{request.host_url}student_register?invite={session['id']}"
    return render_template('teacher_dashboard.html', user={"user_name": session['user']}, activities=activities, students=students, field_submissions=field_submissions, stats=stats, invite_link=invite_link)

@app.route('/approve_submission/<int:submission_id>', methods=['POST'])
def approve_submission(submission_id):
    if 'user' not in session or session.get('role') != 'teacher':
        return jsonify({"success": False, "message": "Unauthorized Access"}), 401
    
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE submissions SET status = 'Approved' WHERE id = %s", (submission_id,))
    return jsonify({"success": True, "message": "Student submission verified successfully!"})

@app.route('/teacher/student/<int:student_id>/analytics')
def teacher_view_student_analytics(student_id):
    if 'user' not in session or session.get('role') != 'teacher':
        return redirect('/login')
        
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute("SELECT id, name, email, role FROM users WHERE id = %s AND role = 'student'", (student_id,))
            student_user = cur.fetchone()
            if not student_user: return "❌ Student Not Found!", 404
                
            cur.execute('''
                SELECT s.photo_path, s.video_path, s.pdf_path, s.status, s.submitted_at, a.title as activity_title, a.description
                FROM submissions s JOIN activities a ON s.activity_id = a.id
                WHERE s.student_id = %s ORDER BY s.submitted_at DESC;
            ''', (student_id,))
            student_submissions = cur.fetchall()
            
    total = len(student_submissions)
    approved = sum(1 for s in student_submissions if s['status'] and str(s['status']).strip().lower() == 'approved')
    pending = sum(1 for s in student_submissions if s['status'] and str(s['status']).strip().lower() == 'pending')
    rejected = sum(1 for s in student_submissions if s['status'] and str(s['status']).strip().lower() == 'rejected')
    
    raw_rate = (approved / total * 100) if total > 0 else 0.0
    approval_rate = f"{round(raw_rate, 1)}%"
    hours_logged = round(approved * 1.5, 1)
            
    return render_template(
        'student_dashboard.html', 
        user={"user_name": student_user['name']}, 
        submissions=student_submissions, 
        total=total, 
        approved=approved, 
        pending=pending, 
        rejected=rejected,
        approval_rate=approval_rate,
        hours_logged=hours_logged
    )

@app.route('/create_activity', methods=['POST'])
def create_activity():
    if 'user' not in session or session.get('role') != 'teacher':
        return jsonify({"success": False, "message": "Unauthorized Access"}), 401
    
    data = request.get_json()
    token = secrets.token_hex(6)
    task_url = f"{request.host_url}task/{token}"
    qr_filename = f"qr_{token}.png"
    qr_path = os.path.join('static', 'qrcodes', qr_filename)
    qrcode.make(task_url).save(qr_path)
    
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO activities (teacher_id, title, description, token, task_url, qr_code_path) VALUES (%s, %s, %s, %s, %s, %s) RETURNING id",
                (session['id'], data.get('title'), data.get('description'), token, task_url, f"/static/qrcodes/{qr_filename}")
            )
            activity_id = cur.fetchone()[0]
            for s_id in data.get('present_students', []):
                cur.execute("INSERT INTO activity_attendance (activity_id, student_id, is_present) VALUES (%s, %s, TRUE)", (activity_id, int(s_id)))
                
    return jsonify({"success": True, "message": "Activity created and attendance matrix locked!"})

@app.route('/task/<token>', methods=['GET', 'POST'])
def task_page(token):
    if 'user' not in session:
        session['next_task_url'] = f"/task/{token}"
        return redirect('/login')
        
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute("SELECT * FROM activities WHERE token = %s", (token,))
            activity = cur.fetchone()
            if not activity: return "❌ Invalid QR Code!", 404

            if session.get('role') == 'teacher':
                user_data = {"user_name": "Test Student", "student_id": "STU-TEST-999"}
                submission = None
            else:
                cur.execute("SELECT * FROM activity_attendance WHERE activity_id = %s AND student_id = %s AND is_present = TRUE", (activity['id'], session['id']))
                if not cur.fetchone():
                    return "<h3>❌ ACCESS DENIED: You are marked ABSENT for this field activity.</h3>", 403
                
                user_data = {"user_name": session['user'], "student_id": session.get('student_id', 'N/A')}
                cur.execute("SELECT * FROM submissions WHERE activity_id = %s AND student_id = %s", (activity['id'], session['id']))
                submission = cur.fetchone()

    if request.method == 'GET':
        return render_template('task.html', activity=activity, user=user_data, submission=submission)
        
    file_photo = request.files.get('proof_photo')
    file_video = request.files.get('proof_video')
    file_pdf = request.files.get('proof_pdf')
    photo_path, video_path, pdf_path = None, None, None
    
    if file_photo and file_photo.filename != '':
        photo_filename = f"photo_{session['id']}_{activity['id']}.jpg"
        photo_path = f"/static/uploads/{photo_filename}"
        file_photo.save(os.path.join('static/uploads', photo_filename))
    if file_video and file_video.filename != '':
        video_filename = f"video_{session['id']}_{activity['id']}.mp4"
        video_path = f"/static/uploads/{video_filename}"
        file_video.save(os.path.join('static/uploads', video_filename))
    if file_pdf and file_pdf.filename != '':
        pdf_filename = f"doc_{session['id']}_{activity['id']}.pdf"
        pdf_path = f"/static/uploads/{pdf_filename}"
        file_pdf.save(os.path.join('static/uploads', pdf_filename))
        
    if photo_path or video_path or pdf_path:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("INSERT INTO submissions (activity_id, student_id, photo_path, video_path, pdf_path) VALUES (%s, %s, %s, %s, %s)", (activity['id'], session['id'], photo_path, video_path, pdf_path))
                
    return redirect(f'/task/{token}')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)