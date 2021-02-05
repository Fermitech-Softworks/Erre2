from flask import Flask, session, url_for, redirect, request, render_template, abort, send_file
from flask_sqlalchemy import SQLAlchemy
import bcrypt
import os
import datetime
import functools
from werkzeug.utils import secure_filename
import requests
import pathlib
import werkzeug.middleware.proxy_fix

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ["SQLALCHEMY_DATABASE_URI"]
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = os.environ["COOKIE_SECRET_KEY"]
UPLOAD_FOLDER = pathlib.Path(os.environ["UPLOAD_FOLDER"]).resolve()
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = set(['txt', 'md', 'pdf', 'doc', 'docx'])
db = SQLAlchemy(app)
telegram_token = os.environ["TELEGRAM_BOT_TOKEN"]
group_chat_id = os.environ["TARGET_CHAT_ID"]
reverse_proxy_app = werkzeug.middleware.proxy_fix.ProxyFix(app=app, x_for=1, x_proto=0, x_host=1, x_port=0, x_prefix=0)

# DB classes go beyond this point

class Author(db.Model):
    __tablename__ = 'author'
    aid = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String, nullable=False)
    cognome = db.Column(db.String, nullable=False)
    email = db.Column(db.String, nullable=False)
    password = db.Column(db.LargeBinary, nullable=False)
    riassunti = db.relationship("Summary", back_populates="autore")

    def __init__(self, nome, cognome, email, password):
        self.nome = nome
        self.cognome = cognome
        self.email = email
        p = bytes(password, encoding="utf-8")
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
    documenti = db.relationship("Summary", back_populates="corso")

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
    autore_id = db.Column(db.Integer, db.ForeignKey('author.aid'))
    autore = db.relationship("Author", back_populates="riassunti")
    corso_id = db.Column(db.Integer, db.ForeignKey('course.cid'))
    corso = db.relationship("Course", back_populates="documenti")
    commit = db.relationship("Commit", back_populates="summary")
    downloads = db.Column(db.Integer)
    filename = db.Column(db.String, nullable=False)

    def __init__(self, nome, descrizione, author_id, course_id, filename):
        self.nome = nome
        self.descrizione = descrizione
        self.autore_id = author_id
        self.corso_id = course_id
        self.downloads = 0
        self.filename = filename

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
        self.data = datetime.datetime.now()
        self.summary_id = summary_id
        self.descrizione = descrizione


nuovoutente = Author("", "", "", "")


# UTILITIES

def login(email, password):
    user = Author.query.filter_by(email=email).first()
    try:
        return bcrypt.checkpw(bytes(password, encoding="utf-8"), user.password)
    except AttributeError:
        # Se non esiste l'Utente
        return False


def find_user(username):
    return Author.query.filter_by(email=username).first()


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


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
            return redirect(url_for('page_dashboard'))
        return f(*args, **kwargs)

    return func


# Error pages with cats


@app.errorhandler(400)
def page_400(_):
    return render_template('error.htm', e=400), 400


@app.errorhandler(403)
def page_403(_):
    return render_template('error.htm', e=403), 403


@app.errorhandler(404)
def page_404(_):
    return render_template('error.htm', e=404), 404


@app.errorhandler(500)
def page_500(_):
    return render_template('error.htm', e=500), 500


# Pages for the guests


@app.route('/')
@login_or_redirect
def page_home():
    del session['username']
    return redirect(url_for('page_dashboard'))


@app.route('/dashboard')
def page_dashboard():
    latest_changes = Commit.query.join(Summary).order_by(Commit.cid.desc()).limit(10)
    materie = Course.query.all()
    return render_template("dashboard.htm", changes=latest_changes, materie=materie)


@app.route('/dashboard/course/<int:cid>')
def page_filter_course(cid):
    riassunti = Summary.query.filter_by(corso_id=cid).join(Author).join(Commit).order_by(Commit.cid.desc()).all()
    return render_template("/riassunti_list.htm", riassunti=riassunti)


@app.route('/dashboard/author/<int:aid>')
def page_filter_author(aid):
    riassunti = Summary.query.filter_by(autore_id=aid).join(Author).join(Commit).order_by(Commit.cid.desc()).all()
    return render_template("/riassunti_list.htm", riassunti=riassunti)


@app.route('/dashboard/summaries')
def page_riassunti_list():
    riassunti = Summary.query.join(Author).join(Commit).order_by(Commit.cid.desc()).all()
    return render_template("/riassunti_list.htm", riassunti=riassunti)


@app.route("/dashboard/summaries/summary/<int:sid>")
def page_inspect_riassunto(sid):
    riassunto = Summary.query.filter_by(sid=sid).first()
    riassunto.downloads += 1
    db.session.commit()

    # Trova il percorso del file
    path = UPLOAD_FOLDER.joinpath(riassunto.filename).resolve()
    return send_file(path, as_attachment=True, attachment_filename=path.name)


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
    riassunti = Summary.query.join(Author).all()
    utente = find_user(session['username'])
    return render_template("/administration/dashboard.htm", materie=materie, riassunti=riassunti, utente=utente)


@app.route("/add_materia", methods=['GET', 'POST'])
@login_or_403
def page_add_materia():
    utente = find_user(session['username'])
    if request.method == 'GET':
        nuovocorso = Course("", "", "", 0, 0)
        return render_template("/administration/materia.htm", utente=utente, corso=nuovocorso, mode=0)

    nuovamateria = Course(request.form.get("nome"), request.form.get("docente"), request.form.get("ramo"),
                          request.form.get("anno"), request.form.get("semestre"))
    db.session.add(nuovamateria)
    db.session.commit()
    return redirect(url_for('page_administration'))


@app.route("/edit_materia/<int:cid>", methods=['GET', 'POST'])
@login_or_403
def page_edit_materia(cid):
    utente = find_user(session['username'])
    corso = Course.query.get_or_404(cid)
    if request.method == 'GET':
        return render_template("/administration/materia.htm", utente=utente, corso=corso, mode=1)
    corso.nome = request.form.get("nome")
    corso.docente = request.form.get("docente")
    corso.ramo = request.form.get("ramo")
    corso.anno = request.form.get("anno")
    corso.semestre = request.form.get("semestre")
    db.session.commit()
    return redirect(url_for('page_administration'))


@app.route("/add_riassunto", methods=['GET', 'POST'])
@login_or_403
def page_add_riassunto():
    utente = find_user(session['username'])
    if request.method == 'GET':
        corsi = Course.query.all()
        return render_template("/administration/riassunto.htm", utente=utente, corsi=corsi)
    if 'file' not in request.files:
        return redirect(request.url)
    file = request.files['file']
    if file.filename == '':
        return redirect(request.url)
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(UPLOAD_FOLDER.joinpath(filename).resolve())
    nuovoriassunto = Summary(request.form.get("nome"), request.form.get("descrizione"), int(utente.aid),
                             int(request.form["listamaterie"]), file.filename)
    db.session.add(nuovoriassunto)
    riassunto = Summary.query.filter_by(filename=file.filename).first()
    nuovocommit = Commit("Riassunto aggiunto a Erre2.", int(riassunto.sid))
    db.session.add(nuovocommit)
    db.session.commit()
    testo = "Il riassunto \"{}\" e' stato caricato su Erre2.\n<a href=\"{}\">Clicca qui per visitare Erre2.</a>".format(
        nuovoriassunto.nome, url_for("page_filter_course", cid=nuovoriassunto.corso_id, _external=True))
    param = {"chat_id": group_chat_id, "text": testo, "parse_mode": "html"}
    requests.get("https://api.telegram.org/bot" + telegram_token + "/sendMessage", params=param)
    return redirect(url_for('page_administration'))


@app.route("/update_riassunto/<int:sid>", methods=['GET', 'POST'])
@login_or_403
def page_update_riassunto(sid):
    utente = find_user('username')
    riassunto = Summary.query.get_or_404(sid)
    if request.method == 'GET':
        return render_template("/administration/update.htm", riassunto=riassunto, utente=utente)
    try:
        os.remove("./static/" + riassunto.filename)
    except FileNotFoundError:
        pass
    if 'file' not in request.files:
        return redirect(request.url)
    file = request.files['file']
    if file.filename == '':
        return redirect(request.url)
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(UPLOAD_FOLDER.joinpath(filename).resolve())
    riassunto.filename = file.filename
    nuovocommit = Commit(request.form.get('descrizione'), riassunto.sid)
    db.session.add(nuovocommit)
    db.session.commit()
    testo = "Il riassunto \"{}\" e' stato aggiornato.\nModifiche: {}\n<a href=\"{}\">Clicca qui per visitare Erre2.</a>".format(
        riassunto.nome, nuovocommit.descrizione, url_for("page_filter_course", cid=riassunto.corso_id, _external=True))
    param = {"chat_id": group_chat_id, "text": testo, "parse_mode": "html"}
    requests.get("https://api.telegram.org/bot" + telegram_token + "/sendMessage", params=param)
    return redirect(url_for('page_administration'))


@app.route("/delete_riassunto/<int:sid>")
@login_or_403
def func_delete_riassunto(sid):
    riassunto = Summary.query.get_or_404(sid)
    commits = Commit.query.filter_by(summary_id=sid)
    for committ in commits:
        db.session.delete(committ)
    try:
        os.remove(UPLOAD_FOLDER.joinpath(riassunto.filename).resolve())
    except FileNotFoundError:
        pass
    db.session.delete(riassunto)
    db.session.commit()
    return redirect(url_for('page_administration'))


@app.route("/delete_materia/<int:cid>")
@login_or_403
def func_delete_materia(cid):
    materia = Course.query.get_or_404(cid)
    riassunti = Summary.query.filter_by(corso_id=cid)
    for riassunto in riassunti:
        commits = Commit.query.filter_by(summary_id=riassunto.sid)
        for committ in commits:
            db.session.delete(committ)
        try:
            os.remove(UPLOAD_FOLDER.joinpath(riassunto.filename).resolve())
        except FileNotFoundError:
            pass
        db.session.delete(riassunto)
    db.session.delete(materia)
    db.session.commit()
    return redirect(url_for('page_administration'))


@app.route("/edit_account", methods=['POST'])
@login_or_403
def func_edit_account():
    utente = find_user(session['username'])
    utente.nome = request.form.get("nome")
    utente.cognome = request.form.get("cognome")
    utente.email = request.form.get("email")
    p = bytes(request.form.get("password"), encoding="utf-8")
    utente.password = bcrypt.hashpw(p, bcrypt.gensalt())
    db.session.commit()
    return redirect(url_for("page_administration"))


if __name__ == "__main__":
    # Assicurati che la cartella ./uploads esista
    os.makedirs(UPLOAD_FOLDER.resolve(), exist_ok=True)

    # Aggiungi sempre le tabelle non esistenti al database, senza cancellare quelle vecchie
    print("Ciao")
    db.create_all()
    autore = Author.query.all()
    if len(autore) == 0:
        nuovoutente = Author("Dummy", "Foo", "foo.dummy@test.com", "password")
        db.session.add(nuovoutente)
        db.session.commit()
    app.run()
