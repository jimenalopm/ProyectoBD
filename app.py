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

# (grupo, [(endpoint, nombre, prefijo de blueprint para marcar el menú activo, icono)])
GRUPOS = [
    ("Administración", [
        ("tablespaces.listar", "Tablespaces", "tablespaces", "bi-hdd-stack"),
        ("usuarios.listar", "Seguridad de usuarios", "usuarios", "bi-shield-lock"),
        ("auditoria.politicas", "Auditoría", "auditoria", "bi-journal-check"),
    ]),
    ("Respaldos", [
        ("respaldos.index", "Respaldos", "respaldos", "bi-cloud-arrow-up"),
        ("recuperacion.index", "Recuperación", "recuperacion", "bi-arrow-counterclockwise"),
        ("archivos.index", "Archivos de respaldo", "archivos", "bi-folder2-open"),
    ]),
    ("Rendimiento", [
        ("performance.index", "Performance", "performance", "bi-activity"),
        ("tuning.plan", "Tuning de consultas", "tuning", "bi-sliders"),
    ]),
]


@app.context_processor
def inject_menu():
    actual = (request.endpoint or "").split(".")[0]
    return {"grupos": GRUPOS, "actual": actual}


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
        resumen = query_dicts(
            """SELECT (SELECT COUNT(*) FROM dba_tablespaces) tablespaces,
                      (SELECT COUNT(*) FROM dba_users WHERE oracle_maintained='N') usuarios,
                      (SELECT COUNT(*) FROM v$session WHERE type='USER' AND username IS NOT NULL) sesiones
               FROM dual""")[0]
        try:
            ultimo = query_dicts(
                "SELECT tipo, estado, TO_CHAR(inicio,'YYYY-MM-DD HH24:MI') inicio "
                "FROM system.bkp_historial WHERE operacion='EXPORT' "
                "ORDER BY id DESC FETCH FIRST 1 ROWS ONLY")
            resumen["ULTIMO_RESPALDO"] = ultimo[0] if ultimo else None
        except Exception:  # noqa: BLE001  (la tabla aún no existe)
            resumen["ULTIMO_RESPALDO"] = None
        grafica = query_dicts(
            """SELECT t.tablespace_name nombre,
                      ROUND(NVL(d.total_mb,0) - NVL(f.free_mb,0),1) usado,
                      ROUND(NVL(f.free_mb,0),1) libre
               FROM dba_tablespaces t
               LEFT JOIN (SELECT tablespace_name, SUM(bytes)/1048576 total_mb FROM dba_data_files
                          GROUP BY tablespace_name) d ON d.tablespace_name = t.tablespace_name
               LEFT JOIN (SELECT tablespace_name, SUM(bytes)/1048576 free_mb FROM dba_free_space
                          GROUP BY tablespace_name) f ON f.tablespace_name = t.tablespace_name
               WHERE t.contents = 'PERMANENT' ORDER BY 2 DESC""")
        return render_template("index.html", inst=inst, db=db, espacio=espacio,
                               resumen=resumen, grafica=grafica, error=None)
    except Exception as e:
        return render_template("index.html", inst=None, db=None, espacio=None,
                               resumen=None, grafica=[], error=str(e))


if __name__ == "__main__":
    app.run(debug=True, port=5000)
