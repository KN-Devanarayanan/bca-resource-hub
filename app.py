from flask import Flask, render_template, send_from_directory, Response, request, redirect, url_for, session, flash
import mysql.connector
import hashlib
import os
import cloudinary
import cloudinary.uploader
import cloudinary.api
import requests
from io import BytesIO
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









@app.route("/uploads/<int:note_id>")
def download_note(note_id):
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT filename, original_filename FROM notes WHERE id = %s", (note_id,))
    result = cursor.fetchone()
    cursor.close()

    if result and result["filename"] and result["original_filename"]:
        file_url = result["filename"]
        original_filename = result["original_filename"]

        # Redirect to the force-download route
        return redirect(url_for('force_download', url=file_url, filename=original_filename))
    else:
        return "File not found", 404




@app.route("/force-download")
def force_download():
    file_url = request.args.get('url')
    filename = request.args.get('filename')

    if not file_url or not filename:
        return "Invalid parameters", 400

    resp = requests.get(file_url)
    if resp.status_code != 200:
        return "File not found on Cloudinary", 404

    return Response(
        resp.content,
        headers={
            'Content-Type': 'application/octet-stream',
            'Content-Disposition': f'attachment; filename="{filename}"'
        }
    )





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



@app.route("/resources/<university>/<material_type>/<semester>")
def view_resources(university, material_type, semester):
    cursor = db.cursor(dictionary=True)

    resources = []
    try:
        if material_type in ["notes", "syllabus", "pyq"]:
            cursor.execute(f"""
                SELECT * FROM {material_type}
                WHERE university=%s AND semester=%s
                ORDER BY uploaded_at DESC
            """, (university, semester))
            resources = cursor.fetchall()
    except Exception as e:
        print(f"Database error: {e}")

    cursor.close()
    return render_template(
        "resources.html",
        resources=resources,
        university=university,
        material_type=material_type,
        semester=semester
    )





@app.route("/resources/search", methods=["GET", "POST"])
def search_resources():
    cursor = db.cursor(dictionary=True)

    university = None
    semester = None

    if request.method == "POST":
        university = request.form.get("university")
        semester = request.form.get("semester")
    else:
        university = request.args.get("university")
        semester = request.args.get("semester")

    query = "SELECT id, university, semester, subject, filename FROM notes WHERE 1=1"
    params = []

    if university:
        query += " AND university = %s"
        params.append(university)
    if semester:
        query += " AND semester = %s"
        params.append(semester)

    query += " ORDER BY uploaded_at DESC"
    cursor.execute(query, params)

    resources = cursor.fetchall()
    cursor.close()

    return render_template(
        "resources.html",
        resources=resources,
        university=university,
        material_type="notes",  # Defaults to notes here
        semester=semester
    )








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

            # Extract the file extension
            file_extension = os.path.splitext(file.filename)[1]  # e.g., ".jpg" or ".pdf"

            # Generate a custom public_id using the original filename without special chars
            safe_filename = file.filename.rsplit('.', 1)[0].replace(' ', '_').replace('/', '_')

            if file.filename == "":
                flash("No file selected.")
                return redirect(url_for("admin_dashboard"))

            # Upload file to Cloudinary as raw WITHOUT forcing format
            upload_result = cloudinary.uploader.upload(
                file,
                folder="notes",
                resource_type="raw",
                public_id=safe_filename  # Use safe filename as ID
            )
            print(upload_result)  # For debugging

            if 'secure_url' in upload_result:
                file_url = upload_result["secure_url"]
                original_filename = file.filename  # Preserve original filename with extension

        

                table = "notes"
                if resource_type == "syllabus":
                    table = "syllabus"
                elif resource_type == "pyq":
                    table = "pyqs"

                cursor.execute(
                f"INSERT INTO {table} (university, semester, subject, filename, original_filename) VALUES (%s, %s, %s, %s, %s)",
                (university, semester, subject, upload_result["secure_url"], file.filename)
                )


                db.commit()

                flash(f"{resource_type.capitalize()} uploaded successfully!")
                return redirect(url_for("admin_dashboard"))
            else:
                flash("Failed to upload file to Cloudinary.", "danger")
                return redirect(url_for("admin_dashboard"))

        elif 'headline' in request.form:
            # Announcement logic remains unchanged
            headline = request.form["headline"]
            description = request.form["description"]

            cursor.execute(
                "INSERT INTO announcements (headline, description) VALUES (%s, %s)",
                (headline, description)
            )
            db.commit()

            flash("Announcement posted successfully!")
            return redirect(url_for("admin_dashboard"))

    # Fetch data for admin dashboard display
    cursor.execute("SELECT id, headline, description FROM announcements ORDER BY posted_at DESC")
    announcements = cursor.fetchall()

    cursor.execute("SELECT id, university, semester, subject, filename FROM notes ORDER BY uploaded_at DESC")
    notes = cursor.fetchall()

    cursor.execute("SELECT id, university, semester, subject, filename FROM syllabus ORDER BY uploaded_at DESC")
    syllabus = cursor.fetchall()

    cursor.execute("SELECT id, university, semester, subject, filename FROM pyqs ORDER BY uploaded_at DESC")
    pyqs = cursor.fetchall()

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
