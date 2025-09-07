from flask import Flask, render_template, send_from_directory, request, redirect, url_for, session, flash
import mysql.connector
import hashlib
import os
import cloudinary
import cloudinary.uploader
import cloudinary.api

from dotenv import load_dotenv 
if os.getenv('RENDER') is None:
    load_dotenv("keys.env")

from flask import Flask, render_template

app = Flask(__name__)




app.secret_key = os.getenv("FLASK_SECRET_KEY")

UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

print("DB_HOST:", os.getenv("DB_HOST"))
print("DB_PORT:", os.getenv("DB_PORT"))
print("DB_USER:", os.getenv("DB_USER"))
print("DB_NAME:", os.getenv("DB_NAME"))


db = mysql.connector.connect(
    host=os.getenv("DB_HOST"),
    port=int(os.getenv("DB_PORT", "3306")),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    database=os.getenv("DB_NAME")
)


cursor = db.cursor(dictionary=True)





@app.route("/", methods=["GET", "POST"])
def home():
    cursor = db.cursor(dictionary=True)

    if request.method == "POST":
        university = request.form.get("university", "").strip()
        semester = request.form.get("semester", "").strip()
        cursor.close()
        return redirect(url_for("search_results", university=university, semester=semester))

    cursor.execute("SELECT * FROM announcements ORDER BY posted_at DESC")
    announcements = cursor.fetchall()
    cursor.close()

    return render_template(
        "index.html",
        announcements=announcements
    )





@app.route("/search-results", methods=["POST"])
def search_results():
    keyword = request.form.get("keyword", "").strip()

    cursor = db.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT * FROM notes
        WHERE filename LIKE %s OR subject LIKE %s
        ORDER BY university ASC, semester ASC, uploaded_at DESC
        """,
        (f"%{keyword}%", f"%{keyword}%")
    )
    notes = cursor.fetchall()
    cursor.close()

    # Group notes by university and semester
    grouped_notes = {}
    for note in notes:
        uni = note['university']
        sem = note['semester']
        grouped_notes.setdefault(uni, {}).setdefault(sem, []).append(note)

    return render_template(
        "search-results.html",
        keyword=keyword,
        grouped_notes=grouped_notes
    )







@app.route("/select-material/<university>")
def select_material(university):
    return render_template("select-material.html", university=university)






@app.route("/semester/<university>/<material_type>")
def select_semester(university, material_type):
    semesters = [
        "Semester 1", "Semester 2", "Semester 3",
        "Semester 4", "Semester 5", "Semester 6"
    ]
    return render_template(
        "select-semester.html",
        university=university,
        material_type=material_type,
        semesters=semesters
    )





@app.route("/resources/<university>/<material_type>/<semester>")
def view_resources(university, material_type, semester):
    cursor = db.cursor(dictionary=True)

    if material_type == "notes":
        cursor.execute("""
            SELECT * FROM notes
            WHERE university=%s AND semester=%s
            ORDER BY uploaded_at DESC
        """, (university, semester))
        resources = cursor.fetchall()

    elif material_type == "syllabus":
        cursor.execute("""
            SELECT * FROM syllabus
            WHERE university=%s AND semester=%s
            ORDER BY uploaded_at DESC
        """, (university, semester))
        resources = cursor.fetchall()

    elif material_type == "pyq":
        cursor.execute("""
            SELECT * FROM pyqs
            WHERE university=%s AND semester=%s
            ORDER BY uploaded_at DESC
        """, (university, semester))
        resources = cursor.fetchall()
    
    else:
        resources = []

    cursor.close()
    return render_template(
        "resources.html",
        resources=resources,
        university=university,
        material_type=material_type,
        semester=semester
    )





@app.route('/upload-note', methods=['POST'])
def upload_note():
    try:
        if 'admin' not in session:
            flash('Please login as admin.', 'danger')
            return redirect(url_for('admin_login'))

        university = request.form['university']
        semester = request.form['semester']
        subject = request.form['subject']
        file = request.files['file']

        print(f"DEBUG: Received file - {file.filename if file else 'No file'}")

        if file:
            # Upload to Cloudinary directly
            result = cloudinary.uploader.upload(
                file,
                folder="notes"
            )
            print(f"DEBUG: Cloudinary upload result - {result}")

            file_url = result.get('secure_url')
            if not file_url:
                raise Exception("Cloudinary did not return a file URL")

            # Save only the Cloudinary URL in DB
            cursor = db.cursor()
            cursor.execute("""
                INSERT INTO notes (university, semester, subject, filename) 
                VALUES (%s, %s, %s, %s)
            """, (university, semester, subject, file_url))
            db.commit()
            cursor.close()

            flash('Note uploaded successfully!', 'success')
        else:
            flash('No file uploaded.', 'danger')

    except Exception as e:
        print(f"ERROR during file upload: {str(e)}")
        flash(f"Error uploading note: {str(e)}", 'danger')

    return redirect(url_for('admin_dashboard'))






@app.route("/uploads/<int:note_id>")
def download_note(note_id):
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT filename FROM notes WHERE id = %s", (note_id,))
    result = cursor.fetchone()
    cursor.close()

    if result and result["filename"]:
        file_url = result["filename"]  # This holds the Cloudinary file URL
        return redirect(file_url)
    else:
        return "File not found", 404






@app.route('/admin-login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        password_hash = hashlib.sha256(password.encode()).hexdigest()

        cursor = db.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM admins WHERE username=%s AND password_hash=%s",
            (username, password_hash)
        )
        admin = cursor.fetchone()
        cursor.close()

        if admin:
            session['admin'] = admin['username']
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid credentials', 'error')
            # render login page again, with flash message
            return render_template('admin-login.html')

    # GET method: just show login page
    return render_template('admin-login.html')







@app.route("/semester")
def semester():
    return render_template("semester.html")





@app.route("/resources", methods=["GET", "POST"])
def resources():
    cursor = db.cursor(dictionary=True)

    university = None
    semester = None

    if request.method == "POST":
        university = request.form.get("university")
        semester = request.form.get("semester")
    else:
        university = request.args.get("university")
        semester = request.args.get("semester")

    query = "SELECT * FROM notes WHERE 1=1"
    params = []

    if university:
        query += " AND university = %s"
        params.append(university)
    if semester:
        query += " AND semester = %s"
        params.append(semester)

    query += " ORDER BY uploaded_at DESC"
    cursor.execute(query, params)

    notes = cursor.fetchall()
    cursor.close()
    return render_template("resources.html", notes=notes, university=university, semester=semester)








@app.route("/delete-announcement/<int:id>", methods=["POST"])
def delete_announcement(id):
    cursor = db.cursor()
    cursor.execute("DELETE FROM announcements WHERE id = %s", (id,))
    db.commit()
    cursor.close()
    flash("Announcement deleted successfully!", "success")
    return redirect(url_for("admin_dashboard"))





@app.route("/delete-syllabus/<int:id>", methods=["POST"])
def delete_syllabus(id):
    cursor = db.cursor()
    cursor.execute("DELETE FROM syllabus WHERE id = %s", (id,))
    db.commit()
    cursor.close()
    flash("Syllabus deleted successfully!", "success")
    return redirect(url_for("admin_dashboard"))




@app.route("/delete-pyq/<int:id>", methods=["POST"])
def delete_pyq(id):
    cursor = db.cursor()
    cursor.execute("DELETE FROM pyqs WHERE id = %s", (id,))
    db.commit()
    cursor.close()
    flash("PYQ deleted successfully!", "success")
    return redirect(url_for("admin_dashboard"))




@app.route("/delete-note/<int:id>", methods=["POST"])
def delete_note(id):
    cursor = db.cursor()
    cursor.execute("DELETE FROM notes WHERE id = %s", (id,))
    db.commit()
    cursor.close()
    flash("Note deleted successfully!", "success")
    return redirect(url_for("admin_dashboard"))






@app.route("/contribute", methods=["GET", "POST"])
def contribute():
    if request.method == "POST":
        university = request.form["university"]
        semester = request.form["semester"]
        subject = request.form["subject"]
        file = request.files["file"]

        # If no file selected
        if file.filename == "":
            flash("No file selected.", "error")
            return redirect(url_for("contribute"))

        try:
            # Save the file
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(filepath)

            # Insert into database
            cursor = db.cursor()
            cursor.execute(
                "INSERT INTO pending_notes (university, semester, subject, filename) VALUES (%s, %s, %s, %s)",
                (university, semester, subject, file.filename)
            )
            db.commit()
            cursor.close()

            # Success message
            flash("Thank you! Your note has been submitted for admin review.", "success")

        except Exception as e:
            print(f"Error: {e}")  # For debugging
            flash("There was an error uploading your notes. Please try again.", "error")

        return redirect(url_for("contribute"))

    return render_template("contribute.html")






@app.route("/approve-pending-note/<int:id>", methods=["POST"])
def approve_pending_note(id):
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM pending_notes WHERE id=%s", (id,))
    note = cursor.fetchone()
    if note:
        cursor.execute(
            "INSERT INTO notes (university, semester, subject, filename) VALUES (%s, %s, %s, %s)",
            (note["university"], note["semester"], note["subject"], note["filename"])
        )
        cursor.execute("DELETE FROM pending_notes WHERE id=%s", (id,))
        db.commit()
    cursor.close()
    flash("Note approved and published!", "success")
    return redirect(url_for("admin_dashboard"))




@app.route("/delete-pending-note/<int:id>", methods=["POST"])
def delete_pending_note(id):
    cursor = db.cursor()
    cursor.execute("DELETE FROM pending_notes WHERE id=%s", (id,))
    db.commit()
    cursor.close()
    flash("Pending note deleted.", "info")
    return redirect(url_for("admin_dashboard"))




@app.route("/about-developer")
def about_developer():
    return render_template("about-developer.html")



@app.route("/admin-dashboard", methods=["GET", "POST"])
def admin_dashboard():
    cursor = db.cursor(dictionary=True)

    if request.method == "POST":
        if 'file' in request.files:
            resource_type = request.form.get("resource_type", "notes")
            university = request.form["university"]
            semester = request.form["semester"]
            subject = request.form["subject"]
            file = request.files["file"]

            if file.filename == "":
                flash("No file selected.")
                return redirect(url_for("admin_dashboard"))

            # Upload file to Cloudinary
            result = cloudinary.uploader.upload(
                file,
                folder="notes"
            )
            file_url = result.get('secure_url')

            # Decide which table to insert into
            table = "notes"
            if resource_type == "syllabus":
                table = "syllabus"
            elif resource_type == "pyq":
                table = "pyqs"

            cursor.execute(
                f"INSERT INTO {table} (university, semester, subject, filename) VALUES (%s, %s, %s, %s)",
                (university, semester, subject, file_url)
            )
            db.commit()
            flash(f"{resource_type.capitalize()} uploaded successfully!")
            return redirect(url_for("admin_dashboard"))

        elif 'headline' in request.form:
            # 📰 Announcement Form
            headline = request.form["headline"]
            description = request.form["description"]

            cursor.execute(
                "INSERT INTO announcements (headline, description) VALUES (%s, %s)",
                (headline, description)
            )
            db.commit()
            flash("Announcement posted successfully!")
            return redirect(url_for("admin_dashboard"))

    # 📝 Fetch existing data
    cursor.execute("SELECT id, headline, description FROM announcements ORDER BY posted_at DESC")
    announcements = cursor.fetchall()

    cursor.execute("SELECT id, university, semester, subject, filename FROM notes ORDER BY uploaded_at DESC")
    notes = cursor.fetchall()

    cursor.execute("SELECT id, university, semester, subject, filename FROM syllabus ORDER BY uploaded_at DESC")
    syllabus = cursor.fetchall()

    cursor.execute("SELECT id, university, semester, subject, filename FROM pyqs ORDER BY uploaded_at DESC")
    pyqs = cursor.fetchall()

    # 📝 Fetch pending contributed notes
    cursor.execute("SELECT id, university, semester, subject, filename, uploaded_at FROM pending_notes ORDER BY uploaded_at DESC")
    pending_notes = cursor.fetchall()

    cursor.close()

    return render_template(
        "admin-dashboard.html",
        announcements=announcements,
        notes=notes,
        syllabus=syllabus,
        pyqs=pyqs,
        pending_notes=pending_notes
    )





if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
