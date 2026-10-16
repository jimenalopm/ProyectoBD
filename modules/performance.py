from flask import Blueprint, render_template, request

from db import query_dicts

bp = Blueprint("performance", __name__, url_prefix="/performance")

METRICAS = [
    "Host CPU Utilization (%)", "Average Active Sessions", "Buffer Cache Hit Ratio",
    "Library Cache Hit Ratio", "Soft Parse Ratio", "Database Wait Time Ratio",
    "User Transaction Per Sec", "Logical Reads Per Sec", "Physical Reads Per Sec",
    "Executions Per Sec", "Current Logons Count",
]
ORDENES = {
    "elapsed": "elapsed_time", "cpu": "cpu_time", "reads": "disk_reads",
    "gets": "buffer_gets", "execs": "executions",
}


def _safe(sql, params=None):
    """Cada sección es independiente: un error en una no rompe la página."""
    try:
        return query_dicts(sql, params), None
    except Exception as e:  # noqa: BLE001
        return [], str(e)


@bp.route("/")
def index():
    orden = request.args.get("orden", "elapsed")
    if orden not in ORDENES:
        orden = "elapsed"
    ocultar_sys = request.args.get("sys", "1") == "1"
    auto = request.args.get("auto") == "1"
    errores = {}

    def sec(nombre, sql, params=None):
        filas, err = _safe(sql, params)
        if err:
            errores[nombre] = err
        return filas

    placeholders = ",".join(f":m{i}" for i in range(len(METRICAS)))
    binds = {f"m{i}": m for i, m in enumerate(METRICAS)}
    metricas = sec("metricas", f"""
        SELECT metric_name, ROUND(MAX(value) KEEP (DENSE_RANK LAST ORDER BY intsize_csec),2) value,
               MAX(metric_unit) unit
        FROM v$sysmetric WHERE metric_name IN ({placeholders}) GROUP BY metric_name
        ORDER BY metric_name""", binds)

    resumen = sec("resumen", """
        SELECT (SELECT COUNT(*) FROM v$session WHERE type='USER') sesiones,
               (SELECT COUNT(*) FROM v$session WHERE type='USER' AND status='ACTIVE'
                  AND username IS NOT NULL AND sid <> SYS_CONTEXT('USERENV','SID')) activas,
               (SELECT COUNT(*) FROM v$session WHERE blocking_session IS NOT NULL) bloqueadas,
               (SELECT ROUND(value/1048576) FROM v$pgastat WHERE name='total PGA allocated') pga_mb,
               (SELECT ROUND(SUM(bytes)/1048576) FROM v$sgainfo WHERE name='Maximum SGA Size') sga_mb
        FROM dual""")

    ratios = sec("ratios", """
        SELECT 'Buffer cache hit ratio' nombre,
               ROUND((1 - phy.value / NULLIF(db.value + cons.value, 0)) * 100, 2) valor
        FROM v$sysstat phy, v$sysstat db, v$sysstat cons
        WHERE phy.name='physical reads cache' AND db.name='db block gets from cache'
          AND cons.name='consistent gets from cache'
        UNION ALL
        SELECT 'Library cache hit ratio', ROUND(SUM(pinhits) / NULLIF(SUM(pins),0) * 100, 2)
        FROM v$librarycache
        UNION ALL
        SELECT 'Row cache hit ratio', ROUND((1 - SUM(getmisses) / NULLIF(SUM(gets),0)) * 100, 2)
        FROM v$rowcache
        UNION ALL
        SELECT 'Parse: soft / total', ROUND((1 - h.value / NULLIF(t.value,0)) * 100, 2)
        FROM v$sysstat t, v$sysstat h
        WHERE t.name='parse count (total)' AND h.name='parse count (hard)'""")

    sga = sec("sga", """
        SELECT name, ROUND(bytes/1048576,1) mb FROM v$sgainfo
        WHERE name IN ('Fixed SGA Size','Redo Buffers','Buffer Cache Size','Shared Pool Size',
                       'Large Pool Size','Java Pool Size','Streams Pool Size','Maximum SGA Size')
        ORDER BY bytes DESC""")
    pga = sec("pga", """
        SELECT name, ROUND(value/1048576,1) mb FROM v$pgastat
        WHERE name IN ('aggregate PGA target parameter','total PGA allocated',
                       'total PGA inuse','maximum PGA allocated')""")

    esperas = sec("esperas", """
        SELECT event, wait_class, total_waits, ROUND(time_waited_micro/1000000,2) segundos,
               ROUND(time_waited_micro/NULLIF(total_waits,0)/1000,2) ms_prom
        FROM v$system_event WHERE wait_class <> 'Idle'
        ORDER BY time_waited_micro DESC FETCH FIRST 10 ROWS ONLY""")

    filtro = "AND parsing_schema_name NOT IN ('SYS','SYSTEM')" if ocultar_sys else ""
    topsql = sec("topsql", f"""
        SELECT sql_id, parsing_schema_name usuario, executions,
               ROUND(elapsed_time/1000,1) elapsed_ms, ROUND(cpu_time/1000,1) cpu_ms,
               buffer_gets, disk_reads, rows_processed filas,
               ROUND(elapsed_time/1000/NULLIF(executions,0),2) ms_por_exec,
               SUBSTR(sql_text,1,160) sql_text
        FROM v$sql WHERE sql_text NOT LIKE '%v$%' AND executions > 0 {filtro}
        ORDER BY {ORDENES[orden]} DESC FETCH FIRST 10 ROWS ONLY""")

    activas = sec("activas", """
        SELECT s.sid, s.serial# serial, s.username, s.status, s.event, s.wait_class,
               s.last_call_et segundos, s.sql_id, SUBSTR(q.sql_text,1,120) sql_text
        FROM v$session s LEFT JOIN v$sql q ON q.sql_id = s.sql_id AND q.child_number = 0
        WHERE s.type='USER' AND s.status='ACTIVE' AND s.username IS NOT NULL
          AND s.sid <> SYS_CONTEXT('USERENV','SID')
        ORDER BY s.last_call_et DESC""")

    bloqueos = sec("bloqueos", """
        SELECT w.sid espera_sid, w.username espera_usuario, w.blocking_session bloquea_sid,
               b.username bloquea_usuario, w.event, w.seconds_in_wait segundos
        FROM v$session w LEFT JOIN v$session b ON b.sid = w.blocking_session
        WHERE w.blocking_session IS NOT NULL ORDER BY w.seconds_in_wait DESC""")

    return render_template("performance.html", metricas=metricas,
                           resumen=resumen[0] if resumen else None, ratios=ratios, sga=sga,
                           pga=pga, esperas=esperas, topsql=topsql, activas=activas,
                           bloqueos=bloqueos, errores=errores, orden=orden,
                           ocultar_sys=ocultar_sys, auto=auto)
