from flask import Flask, session, url_for, redirect, request, render_template, abort
from flask_sqlalchemy import SQLAlchemy
import bcrypt
import os
from datetime import datetime
import functools

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


# DB classes go beyond this point

class Author(db.Model):
    __tablename__ = 'author'
    aid = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String, nullable=False)
    cognome = db.Column(db.String, nullable=False)
    email = db.Column(db.String, nullable=False)
    password = db.Column(db.LargeBinary, nullable=False)
    riassunti = db.relationship("Summary", backref="author")

    def __init__(self, nome, cognome, email, password):
        self.nome = nome
        self.cognome = cognome
        self.email = email
        p = bytes(request.form["password"], encoding="utf-8")
        self.password = bcrypt.hashpw(p, bcrypt.gensalt())

    def __repr__(self):
        return "{} - {} {}".format(self.aid, self.nome, self.cognome)


class Course(db.Model):
    __tablename__ = 'course'
    cid = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String, nullable=False)
    docente = db.Column(db.String, nullable=False)
    ramo = db.Column(db.String, nullable=False)
    anno = db.Column(db.Integer, nullable=False)
    semestre = db.Column(db.Integer, nullable=False)
    riassunti = db.relationship("Summary", backref="course")

    def __init__(self, nome, docente, ramo, anno, semestre):
        self.nome = nome
        self.docente = docente
        self.ramo = ramo
        self.anno = anno
        self.semestre = semestre

    def __repr__(self):
        return "Corso di {}".format(self.nome)


class Summary(db.Model):
    __tablename__ = 'summary'
    sid = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String, nullable=False)
    descrizione = db.Column(db.String, nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('author.aid'))
    author = db.relationship("Author", back_populates="riassunti")
    course_id = db.Column(db.Integer, db.ForeignKey('corso.cid'))
    course = db.relationship("Course", back_populates="riassunti")
    commit = db.relationship("Commit", backref="summary")

    def __init__(self, nome, descrizione, author_id, course_id):
        self.nome = nome
        self.descrizione = descrizione
        self.author_id = author_id
        self.course_id = course_id

    def __repr__(self):
        return "Riassunto {}".format(self.nome)


class Commit(db.Model):
    __tablename__ = 'commit'
    cid = db.Column(db.Integer, primary_key=True)
    descrizione = db.Column(db.String, nullable=False)
    data = db.Column(db.DateTime, nullable=False)
    summary_id = db.Column(db.Integer, db.ForeignKey('summary.sid'))
    summary = db.relationship("Summary", back_populates="commit")

    def __init__(self, descrizione, summary_id):
        self.data = datetime.now()
        self.summary_id = summary_id
        self.descrizione = descrizione


# UTILITIES

def login(username, password):
    user = Author.query.filter_by(email=username).first()
    try:
        return bcrypt.checkpw(bytes(password, encoding="utf-8"), user.passwd)
    except AttributeError:
        # Se non esiste l'Utente
        return False


def find_user(username):
    return Author.query.filter_by(email=username).first()


# Decorators


def login_or_403(f):
    @functools.wraps(f)
    def func(*args, **kwargs):
        if not session.get("username"):
            abort(403)
            return
        return f(*args, **kwargs)

    return func


def login_or_redirect(f):
    @functools.wraps(f)
    def func(*args, **kwargs):
        if not session.get("username"):
            return redirect(url_for('page_login'))
        return f(*args, **kwargs)

    return func


# Pages for the guests


@app.route('/')
@login_or_redirect
def page_home():
    del session['username']
    return redirect(url_for('page_dashboard'))


@app.route('/dashboard')
def page_dashboard():
    latest_changes = Commit.query.order_by(Commit.data.desc()).Join(Summary).limit(10)
    materie = Course.query.all()
    return render_template("dashboard.htm", latest_changes=latest_changes, materie=materie)


@app.route('/dashboard/course/<int:cid>')
def page_filter_course(cid):
    riassunti = Summary.query.filter_by(course_id=cid).join(Author).all()
    return render_template("/riassunti_list.htm", riassunti=riassunti)


@app.route('/dashboard/author/<int:aid>')
def page_filter_author(aid):
    riassunti = Summary.query.filter_by(author_id=aid).join(Author).all()
    return render_template("/riassunti_list.htm", riassunti=riassunti)


@app.route('/dashboard/summaries')
def page_riassunti_list():
    riassunti = Summary.query.join(Author).all()
    return render_template("/riassunti_list.htm", riassunti=riassunti)


@app.route('/dashboard/summary/<int:sid>')
def page_riassunto(sid):
    riassunto = Summary.query.get_or_404(sid)
    changelog = Commit.query.filter_by(summary_id=sid).order_by(Commit.data.desc()).all()

# Pages and functions for the administrator

@app.route('/login', methods=['POST'])
def func_login():
    username = request.form.get("username")
    password = request.form.get("password")
    if not username or not password:
        abort(400)
        return
    if login(username, password):
        session['username'] = username
        return redirect(url_for('page_administration'))
    else:
        abort(403)


@app.route("/administration")
@login_or_403
def page_administration():
    materie = Course.query.all()
    riassunti = Summary.query.all()
    return render_template("/administration/dashboard.htm", materie=materie, riassunti=riassunti)


# TODO: add a way to upload and update summaries and to add courses


if __name__ == "__main__":
    # Aggiungi sempre le tabelle non esistenti al database, senza cancellare quelle vecchie
    db.create_all()
    app.run()
