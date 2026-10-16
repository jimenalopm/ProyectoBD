from flask import Flask, render_template, request

import config
from db import query_dicts
from modules import (archivos, auditoria, performance, recuperacion, respaldos,
                     tablespaces, tuning, usuarios)

app = Flask(__name__)
app.secret_key = config.SECRET_KEY

for modulo in (tablespaces, usuarios, auditoria, respaldos, recuperacion,
               archivos, performance, tuning):
    app.register_blueprint(modulo.bp)

# (endpoint, nombre, prefijo de blueprint para marcar el menú activo)
MODULOS = [
    ("index", "Inicio", None),
    ("tablespaces.listar", "Tablespaces", "tablespaces"),
    ("usuarios.listar", "Seguridad de usuarios", "usuarios"),
    ("auditoria.politicas", "Auditoría", "auditoria"),
    ("respaldos.index", "Respaldos", "respaldos"),
    ("recuperacion.index", "Recuperación", "recuperacion"),
    ("archivos.index", "Archivos de respaldo", "archivos"),
    ("performance.index", "Performance", "performance"),
    ("tuning.plan", "Tuning de consultas", "tuning"),
]


@app.context_processor
def inject_menu():
    actual = (request.endpoint or "").split(".")[0]
    return {"modulos": MODULOS, "actual": actual}


@app.errorhandler(404)
def no_encontrado(_e):
    return render_template("error.html", titulo="Página no encontrada", detalle=request.path), 404


@app.errorhandler(Exception)
def error_general(e):
    code = getattr(e, "code", 500)
    return render_template("error.html", titulo="Ocurrió un error", detalle=str(e)), code


@app.route("/")
def index():
    try:
        inst = query_dicts(
            "SELECT instance_name, host_name, version_full, status, "
            "TO_CHAR(startup_time,'YYYY-MM-DD HH24:MI:SS') startup_time "
            "FROM v$instance"
        )[0]
        db = query_dicts(
            "SELECT name, open_mode, log_mode, "
            "SYS_CONTEXT('USERENV','CON_NAME') con_name FROM v$database"
        )[0]
        espacio = query_dicts(
            "SELECT ROUND(SUM(bytes)/1024/1024) mb_datafiles FROM dba_data_files"
        )[0]
        return render_template("index.html", inst=inst, db=db, espacio=espacio, error=None)
    except Exception as e:
        return render_template("index.html", inst=None, db=None, espacio=None, error=str(e))


if __name__ == "__main__":
    app.run(debug=True, port=5000)
