import oracledb
import config


def get_connection(service=None):
    kwargs = dict(
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        dsn=f"{config.DB_HOST}:{config.DB_PORT}/{service or config.DB_SERVICE}",
    )
    if config.DB_SYSDBA:
        kwargs["mode"] = oracledb.AUTH_MODE_SYSDBA
    return oracledb.connect(**kwargs)


def query(sql, params=None):
    """Ejecuta un SELECT y devuelve (columnas, filas)."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params or {})
            cols = [c[0] for c in cur.description]
            return cols, cur.fetchall()


def query_dicts(sql, params=None):
    cols, rows = query(sql, params)
    return [dict(zip(cols, r)) for r in rows]
