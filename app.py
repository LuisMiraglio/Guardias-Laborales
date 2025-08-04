from flask import Flask, render_template, request, redirect, url_for, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from flask_mail import Mail, Message
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = 'clave-secreta-luis'

# Configuración de correo
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'miraglioluis1@gmail.com'
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = 'miraglioluis1@gmail.com'

mail = Mail(app)

# Configuración de base de datos SQLite con ruta absoluta
basedir = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(basedir, 'instance', 'guardias.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Personas que hacen guardia
personas = {
    "Luis Miraglio": {"email": "miraglioluis1@gmail.com", "color": "#007bff"},
    "Gabriel Peña": {"email": "gabi.2018.p@gmail.com", "color": "#28a745"},
    "Alejo Orellano": {"email": "alejo.orellano.ices@gmail.com", "color": "#dc3545"}
}

# Modelos
class Evento(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    persona = db.Column(db.String(100), nullable=False)
    fecha_inicio = db.Column(db.String(10), nullable=False)
    fecha_fin = db.Column(db.String(10), nullable=False)
    color = db.Column(db.String(20), nullable=False)

class Historial(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)
    descripcion = db.Column(db.Text, nullable=False)

# Función para registrar historial
def registrar_historial(mensaje):
    h = Historial(descripcion=mensaje)
    db.session.add(h)
    db.session.commit()

with app.app_context():
    db.create_all()

@app.route("/")
def calendario_publico():
    eventos = Evento.query.all()
    eventos_json = [
        {
            "title": e.persona,
            "start": e.fecha_inicio,
            "end": e.fecha_fin,
            "color": e.color
        } for e in eventos
    ]
    return render_template("calendario.html", eventos=eventos_json)

@app.route("/admin", methods=["GET", "POST"])
def admin():
    if request.method == "POST":
        if request.form.get("password") == os.getenv("ADMIN_PASSWORD"):
            session['admin'] = True
            return redirect(url_for("panel_admin"))
        else:
            return render_template("login.html", error="Contraseña incorrecta")
    return render_template("login.html")

@app.route("/panel")
def panel_admin():
    if not session.get('admin'):
        return redirect(url_for("admin"))
    eventos = Evento.query.all()
    eventos_json = [
        {
            "title": e.persona,
            "start": e.fecha_inicio,
            "end": e.fecha_fin,
            "color": e.color
        } for e in eventos
    ]
    return render_template("admin.html", eventos=eventos_json, personas=personas)

@app.route("/historial")
def ver_historial():
    if not session.get('admin'):
        return redirect(url_for("admin"))
    lineas = Historial.query.order_by(Historial.fecha.desc()).all()
    return render_template("historial.html", lineas=lineas)

@app.route("/agregar_evento", methods=["POST"])
def agregar_evento():
    if not session.get('admin'):
        return "No autorizado", 403

    data = request.json
    nuevo_evento = Evento(
        persona=data['persona'],
        fecha_inicio=data['fecha_inicio'],
        fecha_fin=data['fecha_fin'],
        color=personas[data['persona']]['color']
    )
    db.session.add(nuevo_evento)
    db.session.commit()
    registrar_historial(f"Guardia asignada a {data['persona']} del {data['fecha_inicio']} al {data['fecha_fin']}")
    return jsonify({"status": "ok"})

@app.route("/editar_evento", methods=["POST"])
def editar_evento():
    if not session.get('admin'):
        return "No autorizado", 403

    data = request.json
    evento = Evento.query.filter_by(fecha_inicio=data['fecha_inicio'], fecha_fin=data['fecha_fin']).first()
    if evento:
        evento.persona = data['persona']
        evento.color = personas[data['persona']]['color']
        db.session.commit()
        registrar_historial(f"Guardia editada: ahora es {data['persona']} del {data['fecha_inicio']} al {data['fecha_fin']}")
    return jsonify({"status": "editado"})

@app.route("/eliminar_evento", methods=["POST"])
def eliminar_evento():
    if not session.get('admin'):
        return "No autorizado", 403

    data = request.json
    evento = Evento.query.filter_by(fecha_inicio=data['fecha_inicio'], fecha_fin=data['fecha_fin']).first()
    if evento:
        db.session.delete(evento)
        db.session.commit()
        registrar_historial(f"Guardia eliminada del {data['fecha_inicio']} al {data['fecha_fin']}")
    return jsonify({"status": "eliminado"})

def enviar_correos_guardias():
    hoy = datetime.today().date()
    sabado = hoy + timedelta((5 - hoy.weekday()) % 7)
    evento = Evento.query.filter_by(fecha_inicio=sabado.isoformat()).first()
    if evento and evento.persona in personas:
        email_destino = personas[evento.persona]['email']
        mensaje = Message(
            subject=f"Recordatorio de guardia: {evento.fecha_inicio} al {evento.fecha_fin}",
            recipients=[email_destino],
            body=f"Hola {evento.persona},\n\nTe recordamos que tenés una guardia asignada para este fin de semana ({evento.fecha_inicio} al {evento.fecha_fin}).\n\nSaludos,\nSistema de Guardias"
        )
        try:
            mail.send(mensaje)
            registrar_historial(f"Correo enviado a {evento.persona} para guardia del {evento.fecha_inicio} al {evento.fecha_fin}")
        except Exception as e:
            registrar_historial(f"Error al enviar correo a {evento.persona}: {e}")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("admin"))

@app.route("/enviar_recordatorio")
def enviar_recordatorio_manual():
    if not session.get('admin'):
        return redirect(url_for("admin"))
    enviar_correos_guardias()
    return "Correo enviado manualmente."

if __name__ == "__main__":
    app.run(debug=True)
