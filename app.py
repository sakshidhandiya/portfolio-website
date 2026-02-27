from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory
from flask_login import LoginManager, login_user, login_required, logout_user
from models import db, User, Project, ProjectFile, Internship, Skill
import os
from collections import defaultdict

# -----------------------------
# APP CONFIG
# -----------------------------
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")

app = Flask(
    __name__,
    template_folder="Template",
    static_folder="static"
)

app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "DATABASE_URL",
    "sqlite:///database.db"
)
# Fix for Render PostgreSQL URL format
if app.config["SQLALCHEMY_DATABASE_URI"].startswith("postgres://"):
    app.config["SQLALCHEMY_DATABASE_URI"] = app.config[
        "SQLALCHEMY_DATABASE_URI"
    ].replace("postgres://", "postgresql://", 1)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

db.init_app(app)

# -----------------------------
# LOGIN MANAGER
# -----------------------------
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "admin_login"


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# -----------------------------
# PUBLIC ROUTES
# -----------------------------
@app.route("/")
def home():
    return render_template(
        "home.html",
        projects=Project.query.all(),
        internships=Internship.query.all(),
        skills=Skill.query.all()
    )


@app.route("/project/<int:project_id>")
def project_detail(project_id):
    project = Project.query.get_or_404(project_id)
    return render_template("project_detail.html", project=project)


@app.route("/download/<filename>")
def download_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename, as_attachment=True)


# -----------------------------
# ADMIN AUTH
# -----------------------------
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        user = User.query.filter_by(username=request.form["username"]).first()
        if user and user.password == request.form["password"]:
            login_user(user)
            return redirect(url_for("admin_dashboard"))
        flash("Invalid username or password")
    return render_template("admin_login.html")


@app.route("/admin/logout")
@login_required
def admin_logout():
    logout_user()
    return redirect(url_for("home"))


# -----------------------------
# ADMIN DASHBOARD
# -----------------------------
@app.route("/admin/dashboard")
@login_required
def admin_dashboard():
    skills_by_category = defaultdict(list)
    for skill in Skill.query.all():
        skills_by_category[skill.category].append(skill)

    return render_template(
        "admin_dashboard.html",
        projects=Project.query.all(),
        internships=Internship.query.all(),
        skills_by_category=skills_by_category
    )


# -----------------------------
# PROJECT ROUTES
# -----------------------------
@app.route("/admin/project/add", methods=["POST"])
@login_required
def add_project():
    project = Project(
        title=request.form["title"],
        description=request.form["description"],
        tools=request.form["tools"]
    )
    db.session.add(project)
    db.session.commit()

    for file in request.files.getlist("files"):
        if file and file.filename:
            file.save(os.path.join(app.config["UPLOAD_FOLDER"], file.filename))
            db.session.add(ProjectFile(filename=file.filename, project_id=project.id))

    db.session.commit()
    flash("Project added successfully")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/edit/<int:project_id>", methods=["GET", "POST"])
@login_required
def edit_project(project_id):
    project = Project.query.get_or_404(project_id)

    if request.method == "POST":
        project.title = request.form["title"]
        project.description = request.form["description"]
        project.tools = request.form["tools"]
        db.session.commit()
        flash("Project updated")
        return redirect(url_for("admin_dashboard"))

    return render_template("edit_project.html", project=project)


# -----------------------------
# INTERNSHIP ROUTES
# -----------------------------
@app.route("/admin/internship/add", methods=["POST"])
@login_required
def add_internship():
    db.session.add(Internship(**request.form))
    db.session.commit()
    flash("Internship added")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/internship/edit/<int:id>", methods=["GET", "POST"])
@login_required
def edit_internship(id):
    internship = Internship.query.get_or_404(id)

    if request.method == "POST":
        for field in ["company", "duration", "role", "description"]:
            setattr(internship, field, request.form[field])
        db.session.commit()
        flash("Internship updated")
        return redirect(url_for("admin_dashboard"))

    return render_template("edit_internship.html", internship=internship)


@app.route("/admin/internship/delete/<int:id>")
@login_required
def delete_internship(id):
    db.session.delete(Internship.query.get_or_404(id))
    db.session.commit()
    flash("Internship deleted")
    return redirect(url_for("admin_dashboard"))


# -----------------------------
# SKILL ROUTES
# -----------------------------
@app.route("/admin/skill/add", methods=["POST"])
@login_required
def add_skill():
    category = request.form["category"]
    raw_skills = request.form["name"]

    for name in [s.strip() for s in raw_skills.split("\n") if s.strip()]:
        db.session.add(Skill(category=category, name=name))

    db.session.commit()
    flash("Skill(s) added")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/skill/edit/<int:id>", methods=["GET", "POST"])
@login_required
def edit_skill(id):
    skill = Skill.query.get_or_404(id)

    if request.method == "POST":
        skill.category = request.form["category"]
        skill.name = request.form["name"]
        db.session.commit()
        flash("Skill updated")
        return redirect(url_for("admin_dashboard"))

    return render_template("edit_skill.html", skill=skill)


@app.route("/admin/skill/delete/<int:id>")
@login_required
def delete_skill(id):
    db.session.delete(Skill.query.get_or_404(id))
    db.session.commit()
    flash("Skill deleted")
    return redirect(url_for("admin_dashboard"))


# -----------------------------
# RUN APP
# -----------------------------
@app.route("/create-admin")
def create_admin():
    from models import User
    existing = User.query.filter_by(username="admin").first()
    if existing:
        return "Admin already exists!"

    new_admin = User(username="admin", password="admin123")
    db.session.add(new_admin)
    db.session.commit()
    return "Admin created successfully!"
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", port=5000)