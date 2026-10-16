import re

from flask import Blueprint, flash, redirect, render_template, request, url_for

from db import get_connection, query_dicts

bp = Blueprint("usuarios", __name__, url_prefix="/usuarios")

IDENT = re.compile(r"^[A-Za-z][A-Za-z0-9_$#]{0,29}$")
SIZE = re.compile(r"^(\d+[KMGkmg]|UNLIMITED|unlimited)$")
LIMITE = re.compile(r"^(\d+|UNLIMITED|DEFAULT|unlimited|default)$")
PRIV = re.compile(r"^[A-Za-z][A-Za-z0-9_ ]{0,60}$")
PROTEGIDOS = {"SYS", "SYSTEM", "PDBADMIN", "ANONYMOUS", "XDB", "DBSNMP"}
LIMITES_PERFIL = [
    "SESSIONS_PER_USER", "FAILED_LOGIN_ATTEMPTS", "PASSWORD_LIFE_TIME",
    "PASSWORD_REUSE_TIME", "PASSWORD_REUSE_MAX", "PASSWORD_LOCK_TIME",
    "PASSWORD_GRACE_TIME", "IDLE_TIME", "CONNECT_TIME",
]


def _ident(valor, campo):
    if not IDENT.match(valor or ""):
        raise ValueError(f"{campo} inválido: use letras, números o _ (máx. 30).")
    return valor.upper()


def _pwd(valor):
    if not valor or '"' in valor or len(valor) < 4:
        raise ValueError("Contraseña inválida (mín. 4 caracteres, sin comillas dobles).")
    return valor


def _ddl(sql):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)


def _run(accion, destino="usuarios.listar", **kw):
    try:
        accion()
        flash("Operación realizada correctamente.", "success")
    except Exception as e:
        flash(f"Error: {e}", "danger")
    return redirect(url_for(destino, **kw))


def _no_protegido(u):
    if u in PROTEGIDOS:
        raise ValueError(f"El usuario {u} está protegido y no se puede modificar desde aquí.")


# ---------------------------------------------------------------- usuarios
@bp.route("/")
def listar():
    try:
        usuarios = query_dicts(
            """
            SELECT username, account_status, default_tablespace,
                   temporary_tablespace, profile,
                   TO_CHAR(created,'YYYY-MM-DD') created,
                   TO_CHAR(lock_date,'YYYY-MM-DD HH24:MI') lock_date,
                   TO_CHAR(expiry_date,'YYYY-MM-DD') expiry_date
            FROM dba_users WHERE oracle_maintained = 'N' ORDER BY username
            """
        )
        tbs = [r["TABLESPACE_NAME"] for r in query_dicts(
            "SELECT tablespace_name FROM dba_tablespaces WHERE contents='PERMANENT' ORDER BY 1")]
        temps = [r["TABLESPACE_NAME"] for r in query_dicts(
            "SELECT tablespace_name FROM dba_tablespaces WHERE contents='TEMPORARY' ORDER BY 1")]
        perfiles = [r["PROFILE"] for r in query_dicts(
            "SELECT DISTINCT profile FROM dba_profiles ORDER BY 1")]
        return render_template("usuarios.html", usuarios=usuarios, tbs=tbs,
                               temps=temps, perfiles=perfiles, error=None)
    except Exception as e:
        return render_template("usuarios.html", usuarios=[], tbs=[], temps=[],
                               perfiles=[], error=str(e))


@bp.route("/crear", methods=["POST"])
def crear():
    def accion():
        u = _ident(request.form["usuario"], "Usuario")
        pwd = _pwd(request.form["password"])
        sql = f'CREATE USER {u} IDENTIFIED BY "{pwd}"'
        if request.form.get("tablespace"):
            sql += f" DEFAULT TABLESPACE {_ident(request.form['tablespace'], 'Tablespace')}"
        if request.form.get("temporal"):
            sql += f" TEMPORARY TABLESPACE {_ident(request.form['temporal'], 'Temporal')}"
        if request.form.get("perfil"):
            sql += f" PROFILE {_ident(request.form['perfil'], 'Perfil')}"
        _ddl(sql)
        if request.form.get("tablespace") and request.form.get("quota"):
            q = request.form["quota"].upper()
            if not SIZE.match(q):
                raise ValueError("Cuota inválida (ej. 100M o UNLIMITED).")
            _ddl(f"ALTER USER {u} QUOTA {q} ON {_ident(request.form['tablespace'], 'Tablespace')}")
        if request.form.get("conectar"):
            _ddl(f"GRANT CREATE SESSION TO {u}")

    return _run(accion)


@bp.route("/password", methods=["POST"])
def password():
    def accion():
        u = _ident(request.form["usuario"], "Usuario")
        _no_protegido(u)
        _ddl(f'ALTER USER {u} IDENTIFIED BY "{_pwd(request.form["password"])}"')

    return _run(accion)


@bp.route("/bloqueo", methods=["POST"])
def bloqueo():
    def accion():
        u = _ident(request.form["usuario"], "Usuario")
        _no_protegido(u)
        modo = "LOCK" if request.form["modo"] == "lock" else "UNLOCK"
        _ddl(f"ALTER USER {u} ACCOUNT {modo}")

    return _run(accion)


@bp.route("/perfil-usuario", methods=["POST"])
def perfil_usuario():
    def accion():
        u = _ident(request.form["usuario"], "Usuario")
        _no_protegido(u)
        _ddl(f"ALTER USER {u} PROFILE {_ident(request.form['perfil'], 'Perfil')}")

    return _run(accion)


@bp.route("/quota", methods=["POST"])
def quota():
    def accion():
        u = _ident(request.form["usuario"], "Usuario")
        _no_protegido(u)
        t = _ident(request.form["tablespace"], "Tablespace")
        q = request.form["quota"].upper()
        if not SIZE.match(q):
            raise ValueError("Cuota inválida (ej. 100M o UNLIMITED).")
        _ddl(f"ALTER USER {u} QUOTA {q} ON {t}")

    return _run(accion, "usuarios.detalle", usuario=request.form["usuario"].upper())


@bp.route("/eliminar", methods=["POST"])
def eliminar():
    def accion():
        u = _ident(request.form["usuario"], "Usuario")
        _no_protegido(u)
        if request.form.get("confirmar", "").upper() != u:
            raise ValueError("Escriba el nombre del usuario para confirmar.")
        _ddl(f"DROP USER {u} CASCADE")

    return _run(accion)


# ---------------------------------------------------------------- detalle
@bp.route("/<usuario>")
def detalle(usuario):
    u = _ident(usuario, "Usuario")
    try:
        roles = query_dicts(
            "SELECT granted_role, admin_option FROM dba_role_privs WHERE grantee=:u ORDER BY 1", {"u": u})
        privs = query_dicts(
            "SELECT privilege, admin_option FROM dba_sys_privs WHERE grantee=:u ORDER BY 1", {"u": u})
        objs = query_dicts(
            "SELECT owner, table_name, privilege FROM dba_tab_privs WHERE grantee=:u ORDER BY 1,2,3", {"u": u})
        quotas = query_dicts(
            "SELECT tablespace_name, ROUND(bytes/1048576,1) usado_mb, "
            "CASE WHEN max_bytes=-1 THEN 'UNLIMITED' ELSE TO_CHAR(ROUND(max_bytes/1048576,1)) END max_mb "
            "FROM dba_ts_quotas WHERE username=:u", {"u": u})
        todos_roles = [r["ROLE"] for r in query_dicts("SELECT role FROM dba_roles ORDER BY 1")]
        tbs = [r["TABLESPACE_NAME"] for r in query_dicts(
            "SELECT tablespace_name FROM dba_tablespaces WHERE contents='PERMANENT' ORDER BY 1")]
        existe = query_dicts("SELECT 1 FROM dba_users WHERE username=:u", {"u": u})
        if not existe:
            flash("El usuario no existe.", "danger")
            return redirect(url_for("usuarios.listar"))
        return render_template("usuario_detalle.html", u=u, roles=roles, privs=privs,
                               objs=objs, quotas=quotas, todos_roles=todos_roles, tbs=tbs)
    except Exception as e:
        flash(f"Error: {e}", "danger")
        return redirect(url_for("usuarios.listar"))


@bp.route("/<usuario>/otorgar", methods=["POST"])
def otorgar(usuario):
    def accion():
        u = _ident(usuario, "Usuario")
        _no_protegido(u)
        p = request.form["privilegio"].strip().upper()
        if not PRIV.match(p):
            raise ValueError("Privilegio o rol inválido.")
        sql = f"GRANT {p} TO {u}"
        if request.form.get("admin"):
            sql += " WITH ADMIN OPTION"
        _ddl(sql)

    return _run(accion, "usuarios.detalle", usuario=usuario)


@bp.route("/<usuario>/revocar", methods=["POST"])
def revocar(usuario):
    def accion():
        u = _ident(usuario, "Usuario")
        _no_protegido(u)
        p = request.form["privilegio"].strip().upper()
        if not PRIV.match(p):
            raise ValueError("Privilegio o rol inválido.")
        _ddl(f"REVOKE {p} FROM {u}")

    return _run(accion, "usuarios.detalle", usuario=usuario)


# ---------------------------------------------------------------- perfiles
@bp.route("/perfiles")
def perfiles():
    try:
        filas = query_dicts(
            "SELECT profile, resource_name, limit FROM dba_profiles "
            "WHERE resource_name IN ('" + "','".join(LIMITES_PERFIL) + "') ORDER BY profile")
        datos = {}
        for f in filas:
            datos.setdefault(f["PROFILE"], {})[f["RESOURCE_NAME"]] = f["LIMIT"]
        return render_template("perfiles.html", datos=datos, limites=LIMITES_PERFIL, error=None)
    except Exception as e:
        return render_template("perfiles.html", datos={}, limites=LIMITES_PERFIL, error=str(e))


@bp.route("/perfiles/crear", methods=["POST"])
def perfil_crear():
    def accion():
        _ddl(f"CREATE PROFILE {_ident(request.form['perfil'], 'Perfil')} LIMIT "
             "SESSIONS_PER_USER UNLIMITED")

    return _run(accion, "usuarios.perfiles")


@bp.route("/perfiles/limite", methods=["POST"])
def perfil_limite():
    def accion():
        p = _ident(request.form["perfil"], "Perfil")
        r = request.form["recurso"].upper()
        v = request.form["valor"].upper()
        if r not in LIMITES_PERFIL:
            raise ValueError("Recurso no permitido.")
        if not LIMITE.match(v):
            raise ValueError("Valor inválido (número, UNLIMITED o DEFAULT).")
        _ddl(f"ALTER PROFILE {p} LIMIT {r} {v}")

    return _run(accion, "usuarios.perfiles")


@bp.route("/perfiles/eliminar", methods=["POST"])
def perfil_eliminar():
    def accion():
        p = _ident(request.form["perfil"], "Perfil")
        if p == "DEFAULT":
            raise ValueError("No se puede eliminar el perfil DEFAULT.")
        _ddl(f"DROP PROFILE {p} CASCADE")

    return _run(accion, "usuarios.perfiles")


# ---------------------------------------------------------------- sesiones
@bp.route("/sesiones")
def sesiones():
    try:
        filas = query_dicts(
            """
            SELECT sid, serial# serial, username, status, osuser, machine, program,
                   TO_CHAR(logon_time,'YYYY-MM-DD HH24:MI:SS') logon_time
            FROM v$session WHERE type='USER' AND username IS NOT NULL
            ORDER BY logon_time DESC
            """
        )
        return render_template("sesiones.html", sesiones=filas, error=None)
    except Exception as e:
        return render_template("sesiones.html", sesiones=[], error=str(e))


@bp.route("/sesiones/matar", methods=["POST"])
def matar():
    def accion():
        sid = int(request.form["sid"])
        serial = int(request.form["serial"])
        _ddl(f"ALTER SYSTEM KILL SESSION '{sid},{serial}' IMMEDIATE")

    return _run(accion, "usuarios.sesiones")
