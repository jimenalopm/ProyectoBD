import re

from flask import Blueprint, flash, redirect, render_template, request, url_for

from db import get_connection, query_dicts

bp = Blueprint("auditoria", __name__, url_prefix="/auditoria")

IDENT = re.compile(r"^[A-Za-z][A-Za-z0-9_$#]{0,29}$")
OBJ = re.compile(r"^[A-Za-z][A-Za-z0-9_$#]{0,29}\.[A-Za-z][A-Za-z0-9_$#]{0,29}$")

# Acciones de sistema permitidas (lista blanca) y de objeto
ACCIONES_SISTEMA = [
    "LOGON", "LOGOFF", "CREATE USER", "ALTER USER", "DROP USER",
    "CREATE TABLE", "ALTER TABLE", "DROP TABLE", "TRUNCATE TABLE",
    "CREATE INDEX", "DROP INDEX", "CREATE TABLESPACE", "DROP TABLESPACE",
    "GRANT", "REVOKE", "CREATE ROLE", "DROP ROLE", "ALTER SYSTEM",
]
ACCIONES_OBJETO = ["SELECT", "INSERT", "UPDATE", "DELETE", "EXECUTE"]


def _ident(valor, campo):
    if not IDENT.match(valor or ""):
        raise ValueError(f"{campo} inválido: use letras, números o _ (máx. 30).")
    return valor.upper()


def _ddl(sql):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)


def _run(accion):
    try:
        accion()
        flash("Operación realizada correctamente.", "success")
    except Exception as e:
        flash(f"Error: {e}", "danger")
    return redirect(url_for("auditoria.politicas"))


def _unificada():
    r = query_dicts("SELECT value FROM v$option WHERE parameter='Unified Auditing'")
    return bool(r) and r[0]["VALUE"] == "TRUE"


# ---------------------------------------------------------------- políticas
@bp.route("/")
def politicas():
    try:
        pols = query_dicts(
            """
            SELECT p.policy_name, COUNT(*) acciones,
                   LISTAGG(DISTINCT p.audit_option, ', ')
                       WITHIN GROUP (ORDER BY p.audit_option) detalle,
                   MAX(p.object_schema || CASE WHEN p.object_name IS NOT NULL
                                               THEN '.' || p.object_name END) objeto,
                   (SELECT LISTAGG(e.entity_name || ' (' || e.entity_type || ')', ', ')
                           WITHIN GROUP (ORDER BY e.entity_name)
                      FROM audit_unified_enabled_policies e
                     WHERE e.policy_name = p.policy_name) habilitada
            FROM audit_unified_policies p
            GROUP BY p.policy_name ORDER BY p.policy_name
            """
        )
        usuarios = [r["USERNAME"] for r in query_dicts(
            "SELECT username FROM dba_users WHERE oracle_maintained='N' ORDER BY 1")]
        info = {
            "unificada": _unificada(),
            "audit_trail": (query_dicts(
                "SELECT value FROM v$parameter WHERE name='audit_trail'") or [{"VALUE": "-"}])[0]["VALUE"],
            "registros": query_dicts("SELECT COUNT(*) n FROM unified_audit_trail")[0]["N"],
        }
        return render_template("auditoria.html", pols=pols, usuarios=usuarios, info=info,
                               sistema=ACCIONES_SISTEMA, objeto=ACCIONES_OBJETO, error=None)
    except Exception as e:
        return render_template("auditoria.html", pols=[], usuarios=[], info=None,
                               sistema=ACCIONES_SISTEMA, objeto=ACCIONES_OBJETO, error=str(e))


@bp.route("/crear", methods=["POST"])
def crear():
    def accion():
        nombre = _ident(request.form["nombre"], "Nombre")
        if nombre.startswith("ORA_"):
            raise ValueError("El prefijo ORA_ está reservado.")
        sis = [a for a in request.form.getlist("sistema") if a in ACCIONES_SISTEMA]
        obj = [a for a in request.form.getlist("objeto") if a in ACCIONES_OBJETO]
        objeto = request.form.get("objeto_nombre", "").strip()
        if obj and not OBJ.match(objeto):
            raise ValueError("Para acciones de objeto indique ESQUEMA.OBJETO.")
        if not sis and not obj:
            raise ValueError("Seleccione al menos una acción.")
        partes = list(sis)
        if obj:
            partes.append(", ".join(obj) + f" ON {objeto.upper()}")
        _ddl(f"CREATE AUDIT POLICY {nombre} ACTIONS {', '.join(partes)}")
        if request.form.get("habilitar"):
            usuario = request.form.get("usuario", "")
            sql = f"AUDIT POLICY {nombre}"
            if usuario:
                sql += f" BY {_ident(usuario, 'Usuario')}"
            _ddl(sql)

    return _run(accion)


@bp.route("/habilitar", methods=["POST"])
def habilitar():
    def accion():
        nombre = _ident(request.form["politica"], "Política")
        usuario = request.form.get("usuario", "")
        sql = f"AUDIT POLICY {nombre}"
        if usuario:
            sql += f" BY {_ident(usuario, 'Usuario')}"
        _ddl(sql)

    return _run(accion)


@bp.route("/deshabilitar", methods=["POST"])
def deshabilitar():
    def accion():
        nombre = _ident(request.form["politica"], "Política")
        # Una política puede estar activada para todos y/o para usuarios concretos
        for e in query_dicts(
            "SELECT entity_name, entity_type FROM audit_unified_enabled_policies "
            "WHERE policy_name=:p", {"p": nombre}):
            if e["ENTITY_NAME"] == "ALL USERS":
                _ddl(f"NOAUDIT POLICY {nombre}")
            else:
                _ddl(f"NOAUDIT POLICY {nombre} BY {_ident(e['ENTITY_NAME'], 'Usuario')}")

    return _run(accion)


@bp.route("/eliminar", methods=["POST"])
def eliminar():
    def accion():
        nombre = _ident(request.form["politica"], "Política")
        if nombre.startswith("ORA_"):
            raise ValueError("No se pueden eliminar políticas predefinidas de Oracle.")
        for e in query_dicts(
            "SELECT entity_name FROM audit_unified_enabled_policies WHERE policy_name=:p",
            {"p": nombre}):
            _ddl(f"NOAUDIT POLICY {nombre}" if e["ENTITY_NAME"] == "ALL USERS"
                 else f"NOAUDIT POLICY {nombre} BY {_ident(e['ENTITY_NAME'], 'Usuario')}")
        _ddl(f"DROP AUDIT POLICY {nombre}")

    return _run(accion)


# ---------------------------------------------------------------- registros
@bp.route("/registros")
def registros():
    usuario = request.args.get("usuario", "").strip().upper()
    accion = request.args.get("accion", "").strip().upper()
    desde = request.args.get("desde", "")
    hasta = request.args.get("hasta", "")
    exito = request.args.get("resultado", "")
    try:
        limite = max(1, min(int(request.args.get("limite", 100)), 1000))
    except ValueError:
        limite = 100

    where, p = ["1=1"], {}
    if usuario:
        where.append("dbusername LIKE :u")
        p["u"] = f"%{usuario}%"
    if accion:
        where.append("action_name LIKE :a")
        p["a"] = f"%{accion}%"
    if desde:
        where.append("event_timestamp >= TO_TIMESTAMP(:d,'YYYY-MM-DD')")
        p["d"] = desde
    if hasta:
        where.append("event_timestamp < TO_TIMESTAMP(:h,'YYYY-MM-DD') + 1")
        p["h"] = hasta
    if exito == "ok":
        where.append("return_code = 0")
    elif exito == "error":
        where.append("return_code <> 0")
    p["lim"] = limite
    try:
        filas = query_dicts(
            f"""
            SELECT TO_CHAR(event_timestamp,'YYYY-MM-DD HH24:MI:SS') fecha, dbusername,
                   action_name, object_schema, object_name, return_code,
                   unified_audit_policies politicas, DBMS_LOB.SUBSTR(sql_text, 300, 1) sql_text
            FROM unified_audit_trail WHERE {' AND '.join(where)}
            ORDER BY event_timestamp DESC FETCH FIRST :lim ROWS ONLY
            """, p)
        acciones = [r["ACTION_NAME"] for r in query_dicts(
            "SELECT DISTINCT action_name FROM unified_audit_trail ORDER BY 1")]
        return render_template("auditoria_registros.html", filas=filas, acciones=acciones,
                               f=dict(usuario=usuario, accion=accion, desde=desde,
                                      hasta=hasta, resultado=exito, limite=limite), error=None)
    except Exception as e:
        return render_template("auditoria_registros.html", filas=[], acciones=[],
                               f=dict(usuario=usuario, accion=accion, desde=desde,
                                      hasta=hasta, resultado=exito, limite=limite), error=str(e))


@bp.route("/limpiar", methods=["POST"])
def limpiar():
    try:
        if request.form.get("confirmar", "").upper() != "LIMPIAR":
            raise ValueError("Escriba LIMPIAR para confirmar.")
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    BEGIN
                      DBMS_AUDIT_MGMT.CLEAN_AUDIT_TRAIL(
                        audit_trail_type         => DBMS_AUDIT_MGMT.AUDIT_TRAIL_UNIFIED,
                        use_last_arch_timestamp  => FALSE);
                    END;""")
        flash("Registros de auditoría eliminados.", "success")
    except Exception as e:
        flash(f"Error: {e}", "danger")
    return redirect(url_for("auditoria.registros"))
