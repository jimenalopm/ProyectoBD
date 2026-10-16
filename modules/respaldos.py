import os

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for

from db import query_dicts
from modules import datapump as dp

bp = Blueprint("respaldos", __name__, url_prefix="/respaldos")

CONTENIDOS = {"ALL", "METADATA_ONLY", "DATA_ONLY"}


@bp.route("/")
def index():
    try:
        dp.ensure_historial()
        ruta = dp.dir_path()
        historial = query_dicts(
            """SELECT id, operacion, tipo, objetos, archivo, estado,
                      TO_CHAR(inicio,'YYYY-MM-DD HH24:MI:SS') inicio,
                      ROUND((NVL(fin,SYSDATE)-inicio)*86400) segundos, tamano_mb, mensaje
               FROM system.bkp_historial ORDER BY id DESC FETCH FIRST 50 ROWS ONLY""")
        esquemas = [r["USERNAME"] for r in query_dicts(
            "SELECT username FROM dba_users WHERE oracle_maintained='N' ORDER BY 1")]
        return render_template("respaldos.html", ruta=ruta, sugerida=dp.default_path(),
                               historial=historial, esquemas=esquemas,
                               en_curso=any(h["ESTADO"] == "EN CURSO" for h in historial),
                               error=None)
    except Exception as e:
        return render_template("respaldos.html", ruta=None, sugerida=None, historial=[],
                               esquemas=[], en_curso=False, error=str(e))


@bp.route("/directorio", methods=["POST"])
def directorio():
    try:
        dp.set_directory(request.form["ruta"])
        flash("Directorio de respaldos configurado.", "success")
    except Exception as e:
        flash(f"Error: {e}", "danger")
    return redirect(url_for("respaldos.index"))


@bp.route("/tablas")
def tablas():
    owner = dp.ident(request.args.get("owner", ""), "Esquema")
    filas = query_dicts("SELECT table_name FROM dba_tables WHERE owner=:o ORDER BY 1", {"o": owner})
    return jsonify([f["TABLE_NAME"] for f in filas])


@bp.route("/crear", methods=["POST"])
def crear():
    try:
        tipo = request.form["tipo"]
        contenido = request.form.get("contenido", "ALL")
        if contenido not in CONTENIDOS:
            raise ValueError("Contenido inválido.")
        m = dp.marca()
        params = [f"content={contenido}"]
        if tipo == "FULL":
            base, objetos = f"FULL_{m}", "FULL"
            params.append("full=y")
        elif tipo == "SCHEMA":
            esquemas = [dp.ident(e, "Esquema") for e in request.form.getlist("esquemas")]
            if not esquemas:
                raise ValueError("Seleccione al menos un esquema.")
            base = f"SCHEMA_{'_'.join(esquemas)[:60]}_{m}"
            objetos = ", ".join(esquemas)
            params.append("schemas=" + ",".join(esquemas))
        elif tipo == "TABLE":
            owner = dp.ident(request.form["owner"], "Esquema")
            tablas = [dp.ident(t, "Tabla") for t in request.form.getlist("tablas")]
            if not tablas:
                raise ValueError("Seleccione al menos una tabla.")
            base = f"TABLE_{owner}_{m}"
            objetos = ", ".join(f"{owner}.{t}" for t in tablas)
            params.append("tables=" + ",".join(f"{owner}.{t}" for t in tablas))
        else:
            raise ValueError("Tipo de respaldo inválido.")
        archivo, logfile = f"{base}.dmp", f"{base}.log"
        params += [f"dumpfile={archivo}", f"logfile={logfile}"]
        dp.lanzar("EXPORT", tipo, objetos, archivo, logfile, params, es_export=True)
        flash(f"Respaldo iniciado: {archivo}", "success")
    except Exception as e:
        flash(f"Error: {e}", "danger")
    return redirect(url_for("respaldos.index"))


@bp.route("/log/<int:registro>")
def log(registro):
    r = query_dicts("SELECT logfile, mensaje FROM system.bkp_historial WHERE id=:i", {"i": registro})
    if not r:
        return "No existe el registro.", 404
    ruta = os.path.join(dp.dir_path() or "", r[0]["LOGFILE"] or "")
    try:
        with open(ruta, "r", encoding="utf-8", errors="replace") as f:
            texto = f.read()
    except OSError:
        texto = (r[0]["MENSAJE"] or "El log aún no está disponible.")
    return texto, 200, {"Content-Type": "text/plain; charset=utf-8"}
