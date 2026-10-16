import os
import re

from flask import Blueprint, flash, redirect, render_template, request, url_for

from db import query_dicts
from modules import datapump as dp

bp = Blueprint("recuperacion", __name__, url_prefix="/recuperacion")

DUMP = re.compile(r"^[A-Za-z0-9_\-\.]+\.dmp$", re.I)
ACCIONES = {"SKIP", "APPEND", "TRUNCATE", "REPLACE"}
CONTENIDOS = {"ALL", "METADATA_ONLY", "DATA_ONLY"}


def _dumps():
    """Archivos .dmp del directorio, enlazados con su historial de exportación."""
    ruta = dp.dir_path()
    if not ruta or not os.path.isdir(ruta):
        return ruta, []
    hist = {h["ARCHIVO"]: h for h in query_dicts(
        "SELECT archivo, tipo, objetos FROM system.bkp_historial WHERE operacion='EXPORT'")}
    archivos = []
    for nombre in sorted(os.listdir(ruta), reverse=True):
        if nombre.lower().endswith(".dmp"):
            st = os.stat(os.path.join(ruta, nombre))
            h = hist.get(nombre, {})
            archivos.append(dict(nombre=nombre, mb=round(st.st_size / 1048576, 2),
                                 tipo=h.get("TIPO", ""), objetos=h.get("OBJETOS", "")))
    return ruta, archivos


@bp.route("/")
def index():
    try:
        dp.ensure_historial()
        ruta, dumps = _dumps()
        historial = query_dicts(
            """SELECT id, tipo, objetos, archivo, estado,
                      TO_CHAR(inicio,'YYYY-MM-DD HH24:MI:SS') inicio,
                      ROUND((NVL(fin,SYSDATE)-inicio)*86400) segundos, mensaje
               FROM system.bkp_historial WHERE operacion='IMPORT'
               ORDER BY id DESC FETCH FIRST 30 ROWS ONLY""")
        return render_template("recuperacion.html", ruta=ruta, dumps=dumps, historial=historial,
                               en_curso=any(h["ESTADO"] == "EN CURSO" for h in historial),
                               error=None)
    except Exception as e:
        return render_template("recuperacion.html", ruta=None, dumps=[], historial=[],
                               en_curso=False, error=str(e))


@bp.route("/restaurar", methods=["POST"])
def restaurar():
    try:
        archivo = request.form["archivo"]
        ruta = dp.dir_path()
        if not DUMP.match(archivo) or not ruta or not os.path.exists(os.path.join(ruta, archivo)):
            raise ValueError("Archivo de respaldo inválido o inexistente.")
        modo = request.form["modo"]
        accion = request.form.get("accion", "SKIP")
        contenido = request.form.get("contenido", "ALL")
        if accion not in ACCIONES or contenido not in CONTENIDOS:
            raise ValueError("Opciones inválidas.")
        base = archivo[:-4]
        logfile = f"IMP_{base}_{dp.marca()}.log"
        params = [f"dumpfile={archivo}", f"logfile={logfile}", f"content={contenido}",
                  f"table_exists_action={accion}"]

        if modo == "FULL":
            if request.form.get("confirmar", "").upper() != "FULL":
                raise ValueError("Para restaurar FULL escriba FULL en el campo de confirmación.")
            params.append("full=y")
            objetos = "FULL"
        elif modo == "SCHEMA":
            esquemas = [dp.ident(e.strip(), "Esquema")
                        for e in request.form["esquemas"].split(",") if e.strip()]
            if not esquemas:
                raise ValueError("Indique al menos un esquema.")
            params.append("schemas=" + ",".join(esquemas))
            objetos = ", ".join(esquemas)
            origen = request.form.get("remap_origen", "").strip()
            destino = request.form.get("remap_destino", "").strip()
            if origen or destino:
                o, d = dp.ident(origen, "Esquema origen"), dp.ident(destino, "Esquema destino")
                params.append(f"remap_schema={o}:{d}")
                objetos += f" ({o}→{d})"
        elif modo == "TABLE":
            tablas = [t.strip().upper() for t in request.form["tablas"].split(",") if t.strip()]
            if not tablas:
                raise ValueError("Indique al menos una tabla (ESQUEMA.TABLA).")
            for t in tablas:
                dueno, _, nombre = t.partition(".")
                dp.ident(dueno, "Esquema")
                dp.ident(nombre, "Tabla")
            params.append("tables=" + ",".join(tablas))
            objetos = ", ".join(tablas)
            origen = request.form.get("remap_origen", "").strip()
            destino = request.form.get("remap_destino", "").strip()
            if origen or destino:
                o, d = dp.ident(origen, "Esquema origen"), dp.ident(destino, "Esquema destino")
                params.append(f"remap_schema={o}:{d}")
                objetos += f" ({o}→{d})"
        else:
            raise ValueError("Modo inválido.")

        dp.lanzar("IMPORT", modo, objetos, archivo, logfile, params, es_export=False)
        flash(f"Recuperación iniciada desde {archivo}", "success")
    except Exception as e:
        flash(f"Error: {e}", "danger")
    return redirect(url_for("recuperacion.index"))
