import os
import re

from flask import Blueprint, flash, redirect, render_template, request, url_for

from db import get_connection, query_dicts

bp = Blueprint("tablespaces", __name__, url_prefix="/tablespaces")

IDENT = re.compile(r"^[A-Za-z][A-Za-z0-9_$#]{0,29}$")
SIZE = re.compile(r"^\d+[KMGkmg]$")


def _ident(valor, campo):
    if not IDENT.match(valor or ""):
        raise ValueError(f"{campo} inválido: use letras, números o _ (máx. 30).")
    return valor.upper()


def _size(valor, campo):
    if not SIZE.match(valor or ""):
        raise ValueError(f"{campo} inválido: use formato como 100M o 2G.")
    return valor.upper()


def _ddl(sql):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)


def _default_dir():
    rows = query_dicts(
        "SELECT file_name FROM dba_data_files WHERE tablespace_name='USERS' "
        "AND ROWNUM=1"
    ) or query_dicts("SELECT file_name FROM dba_data_files WHERE ROWNUM=1")
    return os.path.dirname(rows[0]["FILE_NAME"])


def _ruta(nombre, ruta, ts):
    if ruta:
        return ruta.replace("'", "")
    return os.path.join(_default_dir(), f"{ts}_{nombre}.DBF")


def _run(accion):
    try:
        accion()
        flash("Operación realizada correctamente.", "success")
    except Exception as e:
        flash(f"Error: {e}", "danger")
    return redirect(url_for("tablespaces.listar"))


@bp.route("/")
def listar():
    try:
        tablespaces = query_dicts(
            """
            SELECT t.tablespace_name, t.status, t.contents, t.bigfile,
                   ROUND(NVL(d.total_mb,0),1) total_mb,
                   ROUND(NVL(d.total_mb,0) - NVL(f.free_mb,0),1) used_mb,
                   ROUND(NVL(f.free_mb,0),1) free_mb,
                   ROUND((NVL(d.total_mb,0) - NVL(f.free_mb,0))
                         / NULLIF(d.total_mb,0) * 100,1) pct_used
            FROM dba_tablespaces t
            LEFT JOIN (SELECT tablespace_name, SUM(bytes)/1048576 total_mb
                       FROM dba_data_files GROUP BY tablespace_name) d
                   ON d.tablespace_name = t.tablespace_name
            LEFT JOIN (SELECT tablespace_name, SUM(bytes)/1048576 free_mb
                       FROM dba_free_space GROUP BY tablespace_name) f
                   ON f.tablespace_name = t.tablespace_name
            ORDER BY t.tablespace_name
            """
        )
        archivos = query_dicts(
            """
            SELECT tablespace_name, file_name, ROUND(bytes/1048576,1) size_mb,
                   autoextensible, ROUND(maxbytes/1048576,1) max_mb, status
            FROM dba_data_files ORDER BY tablespace_name, file_id
            """
        )
        return render_template(
            "tablespaces.html", tablespaces=tablespaces, archivos=archivos, error=None
        )
    except Exception as e:
        return render_template("tablespaces.html", tablespaces=[], archivos=[], error=str(e))


@bp.route("/crear", methods=["POST"])
def crear():
    def accion():
        nombre = _ident(request.form["nombre"], "Nombre")
        tam = _size(request.form["tamano"], "Tamaño")
        ruta = _ruta(nombre, request.form.get("ruta", "").strip(), nombre)
        sql = f"CREATE TABLESPACE {nombre} DATAFILE '{ruta}' SIZE {tam}"
        if request.form.get("autoextend"):
            sql += " AUTOEXTEND ON NEXT 10M MAXSIZE UNLIMITED"
        _ddl(sql)

    return _run(accion)


@bp.route("/datafile", methods=["POST"])
def agregar_datafile():
    def accion():
        ts = _ident(request.form["tablespace"], "Tablespace")
        tam = _size(request.form["tamano"], "Tamaño")
        n = len([a for a in query_dicts(
            "SELECT 1 FROM dba_data_files WHERE tablespace_name=:t", {"t": ts})]) + 1
        ruta = _ruta(f"{n:02d}", request.form.get("ruta", "").strip(), ts)
        _ddl(f"ALTER TABLESPACE {ts} ADD DATAFILE '{ruta}' SIZE {tam}")

    return _run(accion)


@bp.route("/redimensionar", methods=["POST"])
def redimensionar():
    def accion():
        archivo = request.form["archivo"].replace("'", "")
        tam = _size(request.form["tamano"], "Tamaño")
        _ddl(f"ALTER DATABASE DATAFILE '{archivo}' RESIZE {tam}")

    return _run(accion)


@bp.route("/autoextend", methods=["POST"])
def autoextend():
    def accion():
        archivo = request.form["archivo"].replace("'", "")
        if request.form["modo"] == "on":
            _ddl(f"ALTER DATABASE DATAFILE '{archivo}' AUTOEXTEND ON NEXT 10M MAXSIZE UNLIMITED")
        else:
            _ddl(f"ALTER DATABASE DATAFILE '{archivo}' AUTOEXTEND OFF")

    return _run(accion)


@bp.route("/estado", methods=["POST"])
def estado():
    def accion():
        ts = _ident(request.form["tablespace"], "Tablespace")
        modo = "ONLINE" if request.form["modo"] == "online" else "OFFLINE"
        _ddl(f"ALTER TABLESPACE {ts} {modo}")

    return _run(accion)


@bp.route("/eliminar", methods=["POST"])
def eliminar():
    def accion():
        ts = _ident(request.form["tablespace"], "Tablespace")
        if ts in ("SYSTEM", "SYSAUX", "UNDOTBS1", "TEMP", "USERS"):
            raise ValueError("No se permite eliminar tablespaces del sistema.")
        if request.form.get("confirmar", "").upper() != ts:
            raise ValueError("Escriba el nombre del tablespace para confirmar.")
        _ddl(f"DROP TABLESPACE {ts} INCLUDING CONTENTS AND DATAFILES")

    return _run(accion)
