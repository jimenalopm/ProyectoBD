import os
import re
import shutil
import time
from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, send_from_directory, url_for

from db import get_connection, query_dicts
from modules import datapump as dp

bp = Blueprint("archivos", __name__, url_prefix="/archivos")

NOMBRE = re.compile(r"^[A-Za-z0-9_\-\.]{1,200}\.(dmp|log)$", re.I)
PROTEGIDOS = {dp.DIR_NAME, "DATA_PUMP_DIR"}


def _ruta():
    ruta = dp.dir_path()
    if not ruta or not os.path.isdir(ruta):
        raise ValueError("Configure primero el directorio de respaldos (módulo Respaldos).")
    return ruta


def _seguro(nombre):
    """Valida el nombre y devuelve la ruta absoluta dentro del directorio de respaldos."""
    if not NOMBRE.match(nombre or ""):
        raise ValueError("Nombre de archivo inválido (solo .dmp o .log).")
    base = os.path.realpath(_ruta())
    completa = os.path.realpath(os.path.join(base, nombre))
    if os.path.dirname(completa) != base:
        raise ValueError("Ruta fuera del directorio de respaldos.")
    return completa


def _listar(ruta):
    filas = []
    for n in os.listdir(ruta):
        p = os.path.join(ruta, n)
        if os.path.isfile(p) and NOMBRE.match(n):
            st = os.stat(p)
            filas.append(dict(nombre=n, tipo=n.rsplit(".", 1)[1].lower(),
                              mb=round(st.st_size / 1048576, 2),
                              mtime=st.st_mtime,
                              fecha=datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M"),
                              dias=int((time.time() - st.st_mtime) // 86400)))
    return sorted(filas, key=lambda f: f["mtime"], reverse=True)


def _run(accion):
    try:
        msg = accion()
        flash(msg or "Operación realizada correctamente.", "success")
    except Exception as e:
        flash(f"Error: {e}", "danger")
    return redirect(url_for("archivos.index"))


@bp.route("/")
def index():
    try:
        dp.ensure_historial()
        ruta = _ruta()
        archivos = _listar(ruta)
        try:
            dias = int(request.args.get("dias", 0))
        except ValueError:
            dias = 0
        candidatos = [a for a in archivos if dias and a["dias"] >= dias]
        uso = shutil.disk_usage(ruta)
        disco = dict(total=round(uso.total / 1073741824, 1), libre=round(uso.free / 1073741824, 1),
                     pct=round((uso.total - uso.free) / uso.total * 100),
                     respaldos=round(sum(a["mb"] for a in archivos), 1))
        dirs = query_dicts(
            """SELECT d.directory_name, d.directory_path,
                      CASE WHEN o.oracle_maintained='N' THEN 'N' ELSE 'Y' END sistema
               FROM dba_directories d
               LEFT JOIN dba_objects o ON o.object_name=d.directory_name
                                      AND o.object_type='DIRECTORY'
               ORDER BY d.directory_name""")
        return render_template("archivos.html", ruta=ruta, archivos=archivos, dias=dias,
                               candidatos=candidatos, disco=disco, dirs=dirs,
                               protegidos=PROTEGIDOS, error=None)
    except Exception as e:
        return render_template("archivos.html", ruta=None, archivos=[], dias=0, candidatos=[],
                               disco=None, dirs=[], protegidos=PROTEGIDOS, error=str(e))


@bp.route("/descargar/<nombre>")
def descargar(nombre):
    try:
        _seguro(nombre)
        return send_from_directory(_ruta(), nombre, as_attachment=True)
    except Exception as e:
        flash(f"Error: {e}", "danger")
        return redirect(url_for("archivos.index"))


@bp.route("/eliminar", methods=["POST"])
def eliminar():
    def accion():
        nombre = request.form["nombre"]
        p = _seguro(nombre)
        os.remove(p)
        n = 1
        if request.form.get("con_log") and nombre.lower().endswith(".dmp"):
            log = p[:-4] + ".log"
            if os.path.exists(log):
                os.remove(log)
                n += 1
        return f"Se eliminaron {n} archivo(s)."

    return _run(accion)


@bp.route("/renombrar", methods=["POST"])
def renombrar():
    def accion():
        origen = _seguro(request.form["nombre"])
        nuevo = request.form["nuevo"].strip()
        destino = _seguro(nuevo)
        if os.path.splitext(origen)[1].lower() != os.path.splitext(destino)[1].lower():
            raise ValueError("La extensión debe mantenerse.")
        if os.path.exists(destino):
            raise ValueError("Ya existe un archivo con ese nombre.")
        os.rename(origen, destino)

    return _run(accion)


@bp.route("/retencion", methods=["POST"])
def retencion():
    def accion():
        dias = int(request.form["dias"])
        if dias < 1:
            raise ValueError("Indique un número de días mayor a 0.")
        borrados = 0
        for a in _listar(_ruta()):
            if a["dias"] >= dias:
                os.remove(_seguro(a["nombre"]))
                borrados += 1
        return f"Política de retención aplicada: {borrados} archivo(s) eliminado(s)."

    return _run(accion)


# ---------------------------------------------------------------- DIRECTORY de Oracle
@bp.route("/directorio/crear", methods=["POST"])
def dir_crear():
    def accion():
        nombre = dp.ident(request.form["nombre"], "Nombre")
        ruta = request.form["ruta"].strip().rstrip("\\/")
        if not ruta or "'" in ruta or '"' in ruta:
            raise ValueError("Ruta inválida.")
        os.makedirs(ruta, exist_ok=True)
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(f"CREATE DIRECTORY {nombre} AS '{ruta}'")

    return _run(accion)


@bp.route("/directorio/eliminar", methods=["POST"])
def dir_eliminar():
    def accion():
        nombre = dp.ident(request.form["nombre"], "Nombre")
        if nombre in PROTEGIDOS:
            raise ValueError("Este directorio lo usa la aplicación y no se puede eliminar.")
        r = query_dicts(
            "SELECT 1 FROM dba_objects WHERE object_type='DIRECTORY' AND object_name=:n "
            "AND oracle_maintained='N'", {"n": nombre})
        if not r:
            raise ValueError("No se puede eliminar un directorio mantenido por Oracle.")
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(f"DROP DIRECTORY {nombre}")

    return _run(accion)
