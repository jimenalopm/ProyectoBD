import re
import time
import uuid

from flask import Blueprint, flash, redirect, render_template, request, url_for

from db import get_connection, query_dicts

bp = Blueprint("tuning", __name__, url_prefix="/tuning")

IDENT = re.compile(r"^[A-Za-z][A-Za-z0-9_$#]{0,29}$")
EXPLICABLE = re.compile(r"^\s*(select|with|insert|update|delete|merge)\b", re.I)
SOLO_SELECT = re.compile(r"^\s*(select|with)\b", re.I)

# Último plan por consulta (aplicación de un solo usuario): sirve para comparar antes/después
_ultimo = {}


def _ident(valor, campo):
    if not IDENT.match(valor or ""):
        raise ValueError(f"{campo} inválido: use letras, números o _ (máx. 30).")
    return valor.upper()


def _limpiar_sql(sql):
    sql = (sql or "").strip().rstrip(";").strip()
    if not sql:
        raise ValueError("Escriba una sentencia SQL.")
    if ";" in sql:
        raise ValueError("Solo se permite una sentencia a la vez.")
    return sql


def _esquemas():
    return [r["USERNAME"] for r in query_dicts(
        "SELECT username FROM dba_users WHERE oracle_maintained='N' ORDER BY 1")]


def _ddl(sql):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)


# ---------------------------------------------------------------- planes de ejecución
@bp.route("/", methods=["GET", "POST"])
def plan():
    ctx = dict(sql="", esquema="", plan=None, costo=None, anterior=None, ejecucion=None,
               esquemas=[], error=None)
    try:
        ctx["esquemas"] = _esquemas()
    except Exception as e:
        ctx["error"] = str(e)
        return render_template("tuning_plan.html", **ctx)
    if request.method == "POST":
        ctx["sql"] = request.form.get("sql", "")
        ctx["esquema"] = request.form.get("esquema", "")
        try:
            sql = _limpiar_sql(ctx["sql"])
            ejecutar = request.form.get("accion") == "ejecutar"
            if not EXPLICABLE.match(sql):
                raise ValueError("Solo SELECT, INSERT, UPDATE, DELETE o MERGE.")
            if ejecutar and not SOLO_SELECT.match(sql):
                raise ValueError("Solo se pueden ejecutar consultas SELECT.")
            with get_connection() as conn:
                with conn.cursor() as cur:
                    if ctx["esquema"]:
                        cur.execute(f"ALTER SESSION SET CURRENT_SCHEMA = {_ident(ctx['esquema'], 'Esquema')}")
                    sid = "T" + uuid.uuid4().hex[:12]
                    cur.execute(f"EXPLAIN PLAN SET STATEMENT_ID = '{sid}' FOR {sql}")
                    cur.execute("SELECT plan_table_output FROM TABLE("
                                "DBMS_XPLAN.DISPLAY('PLAN_TABLE', :s, 'TYPICAL'))", s=sid)
                    ctx["plan"] = "\n".join(r[0] for r in cur.fetchall())
                    cur.execute("SELECT cost FROM plan_table WHERE statement_id=:s AND id=0", s=sid)
                    fila = cur.fetchone()
                    ctx["costo"] = fila[0] if fila else None
                    cur.execute("DELETE FROM plan_table WHERE statement_id=:s", s=sid)
                    conn.commit()
                    if ejecutar:
                        t0 = time.perf_counter()
                        cur.execute("SELECT /*+ gather_plan_statistics */ * FROM ("
                                    f"{sql}) WHERE ROWNUM <= 1000")
                        cols = [c[0] for c in cur.description]
                        filas = cur.fetchall()
                        ms = round((time.perf_counter() - t0) * 1000, 1)
                        cur.execute("SELECT plan_table_output FROM TABLE("
                                    "DBMS_XPLAN.DISPLAY_CURSOR(NULL, NULL, 'ALLSTATS LAST'))")
                        real = "\n".join(r[0] for r in cur.fetchall())
                        ctx["ejecucion"] = dict(cols=cols, filas=filas[:50], total=len(filas),
                                                ms=ms, plan_real=real)
            clave = (ctx["esquema"], " ".join(sql.split()))
            ctx["anterior"] = _ultimo.get(clave)
            _ultimo[clave] = dict(plan=ctx["plan"], costo=ctx["costo"],
                                  hora=time.strftime("%H:%M:%S"))
        except Exception as e:
            ctx["error"] = str(e)
    return render_template("tuning_plan.html", **ctx)


# ---------------------------------------------------------------- estadísticas
@bp.route("/estadisticas")
def estadisticas():
    esquema = request.args.get("esquema", "")
    try:
        esquemas = _esquemas()
        tablas = []
        if esquema:
            tablas = query_dicts(
                """SELECT t.table_name, t.num_rows, t.blocks, t.avg_row_len,
                          TO_CHAR(t.last_analyzed,'YYYY-MM-DD HH24:MI') analizada,
                          s.stale_stats, s.global_stats
                   FROM dba_tables t
                   LEFT JOIN dba_tab_statistics s ON s.owner=t.owner AND s.table_name=t.table_name
                                                  AND s.object_type='TABLE'
                   WHERE t.owner=:o ORDER BY t.table_name""", {"o": _ident(esquema, "Esquema")})
        return render_template("tuning_estadisticas.html", esquemas=esquemas, esquema=esquema,
                               tablas=tablas, error=None)
    except Exception as e:
        return render_template("tuning_estadisticas.html", esquemas=[], esquema=esquema,
                               tablas=[], error=str(e))


@bp.route("/estadisticas/accion", methods=["POST"])
def estadisticas_accion():
    esquema = request.form.get("esquema", "")
    try:
        o = _ident(esquema, "Esquema")
        accion = request.form["accion"]
        with get_connection() as conn:
            with conn.cursor() as cur:
                if accion == "tabla":
                    t = _ident(request.form["tabla"], "Tabla")
                    cur.execute("BEGIN DBMS_STATS.GATHER_TABLE_STATS(ownname=>:o, tabname=>:t, "
                                "cascade=>TRUE); END;", o=o, t=t)
                elif accion == "esquema":
                    cur.execute("BEGIN DBMS_STATS.GATHER_SCHEMA_STATS(ownname=>:o, cascade=>TRUE); END;", o=o)
                elif accion == "borrar":
                    t = _ident(request.form["tabla"], "Tabla")
                    cur.execute("BEGIN DBMS_STATS.DELETE_TABLE_STATS(ownname=>:o, tabname=>:t); END;", o=o, t=t)
                else:
                    raise ValueError("Acción inválida.")
        flash("Operación realizada correctamente.", "success")
    except Exception as e:
        flash(f"Error: {e}", "danger")
    return redirect(url_for("tuning.estadisticas", esquema=esquema))


# ---------------------------------------------------------------- índices
@bp.route("/indices")
def indices():
    esquema = request.args.get("esquema", "")
    try:
        esquemas = _esquemas()
        filas = []
        if esquema:
            o = _ident(esquema, "Esquema")
            filas = query_dicts(
                """SELECT i.index_name, i.table_name, i.uniqueness, i.status, i.index_type,
                          (SELECT LISTAGG(c.column_name, ', ') WITHIN GROUP (ORDER BY c.column_position)
                             FROM dba_ind_columns c WHERE c.index_owner=i.owner
                              AND c.index_name=i.index_name) columnas,
                          i.leaf_blocks, i.distinct_keys,
                          TO_CHAR(i.last_analyzed,'YYYY-MM-DD HH24:MI') analizado,
                          (SELECT COUNT(*) FROM dba_constraints k WHERE k.owner=i.owner
                              AND k.index_name=i.index_name) es_restriccion
                   FROM dba_indexes i WHERE i.owner=:o ORDER BY i.table_name, i.index_name""",
                {"o": o})
            try:
                uso = {u["NAME"]: u for u in query_dicts(
                    "SELECT name, total_access_count accesos, "
                    "TO_CHAR(last_used,'YYYY-MM-DD HH24:MI') ultimo "
                    "FROM dba_index_usage WHERE owner=:o", {"o": o})}
            except Exception:  # noqa: BLE001
                uso = {}
            for f in filas:
                u = uso.get(f["INDEX_NAME"])
                f["ACCESOS"] = u["ACCESOS"] if u else None
                f["ULTIMO"] = u["ULTIMO"] if u else None
        tablas = [r["TABLE_NAME"] for r in query_dicts(
            "SELECT table_name FROM dba_tables WHERE owner=:o ORDER BY 1", {"o": esquema.upper()})] if esquema else []
        return render_template("tuning_indices.html", esquemas=esquemas, esquema=esquema,
                               indices=filas, tablas=tablas, error=None)
    except Exception as e:
        return render_template("tuning_indices.html", esquemas=[], esquema=esquema,
                               indices=[], tablas=[], error=str(e))


@bp.route("/indices/accion", methods=["POST"])
def indices_accion():
    esquema = request.form.get("esquema", "")
    try:
        o = _ident(esquema, "Esquema")
        accion = request.form["accion"]
        if accion == "crear":
            nombre = _ident(request.form["nombre"], "Nombre del índice")
            tabla = _ident(request.form["tabla"], "Tabla")
            cols = [_ident(c.strip(), "Columna") for c in request.form["columnas"].split(",") if c.strip()]
            if not cols:
                raise ValueError("Indique al menos una columna.")
            unico = "UNIQUE " if request.form.get("unico") else ""
            _ddl(f"CREATE {unico}INDEX {o}.{nombre} ON {o}.{tabla} ({', '.join(cols)})")
        else:
            nombre = _ident(request.form["indice"], "Índice")
            if accion == "eliminar":
                _ddl(f"DROP INDEX {o}.{nombre}")
            elif accion == "reconstruir":
                _ddl(f"ALTER INDEX {o}.{nombre} REBUILD")
            else:
                raise ValueError("Acción inválida.")
        flash("Operación realizada correctamente.", "success")
    except Exception as e:
        flash(f"Error: {e}", "danger")
    return redirect(url_for("tuning.indices", esquema=esquema))
