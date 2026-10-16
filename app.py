from flask import Flask, render_template

import config
from db import query_dicts

app = Flask(__name__)
app.secret_key = config.SECRET_KEY

from modules.tablespaces import bp as tablespaces_bp  # noqa: E402

from modules.usuarios import bp as usuarios_bp  # noqa: E402

app.register_blueprint(tablespaces_bp)
app.register_blueprint(usuarios_bp)

MODULOS = [
    ("index", "Inicio"),
    ("tablespaces.listar", "Tablespaces"),
    ("usuarios.listar", "Seguridad de usuarios"),
]


@app.context_processor
def inject_menu():
    return {"modulos": MODULOS}


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
