from flask import Flask, render_template, request, redirect, url_for, jsonify, session
from datetime import datetime
import json
import os

app = Flask(__name__)
app.secret_key = 'clave-secreta-luis'

# Correos y colores asignados a las 3 personas (pueden modificarse después)
personas = {
    "Juan": {"email": "juan@email.com", "color": "#007bff"},
    "Marta": {"email": "marta@email.com", "color": "#28a745"},
    "Pedro": {"email": "pedro@email.com", "color": "#dc3545"}
}

# Cargar eventos desde archivo JSON
EVENTOS_FILE = "eventos.json"
if os.path.exists(EVENTOS_FILE):
    with open(EVENTOS_FILE, "r") as f:
        eventos = json.load(f)
else:
    eventos = []

@app.route("/")
def calendario_publico():
    return render_template("calendario.html", eventos=json.dumps(eventos))

@app.route("/admin", methods=["GET", "POST"])
def admin():
    if request.method == "POST":
        if request.form.get("password") == "admin123":
            session['admin'] = True
            return redirect(url_for("panel_admin"))
        else:
            return render_template("login.html", error="Contraseña incorrecta")
    return render_template("login.html")

@app.route("/panel")
def panel_admin():
    if not session.get('admin'):
        return redirect(url_for("admin"))
    return render_template("admin.html", eventos=json.dumps(eventos), personas=personas)

@app.route("/agregar_evento", methods=["POST"])
def agregar_evento():
    if not session.get('admin'):
        return "No autorizado", 403

    data = request.json
    nuevo_evento = {
        "title": data['persona'],
        "start": data['fecha_inicio'],
        "end": data['fecha_fin'],
        "color": personas[data['persona']]['color']
    }
    eventos.append(nuevo_evento)
    with open(EVENTOS_FILE, "w") as f:
        json.dump(eventos, f)
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    app.run(debug=True)
