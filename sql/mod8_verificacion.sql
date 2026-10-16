-- sqlplus / as sysdba
ALTER SESSION SET CONTAINER = XEPDB1;
SET LINESIZE 220 PAGESIZE 100
COL table_name FORMAT A25
COL index_name FORMAT A25
COL columnas FORMAT A40

-- Escenario de prueba (cree una tabla grande con un usuario de prueba)
-- CREATE USER usr_tuning IDENTIFIED BY "clave" DEFAULT TABLESPACE users QUOTA UNLIMITED ON users;
-- GRANT CREATE SESSION, CREATE TABLE TO usr_tuning;
-- CREATE TABLE usr_tuning.ventas AS
--   SELECT level id, MOD(level,500) cliente, SYSDATE-MOD(level,365) fecha, ROUND(DBMS_RANDOM.VALUE(1,1000),2) monto
--   FROM dual CONNECT BY level <= 200000;

-- 1) PLAN: en la app (esquema USR_TUNING) explique:  SELECT * FROM ventas WHERE cliente = 42
--    Mismo plan por SQL*Plus:
EXPLAIN PLAN FOR SELECT * FROM usr_tuning.ventas WHERE cliente = 42;
SELECT * FROM TABLE(DBMS_XPLAN.DISPLAY);
--    Debe verse TABLE ACCESS FULL. Cree el indice desde la pestana "Indices" (VENTAS, CLIENTE, IDX_VENTAS_CLIENTE)
--    y vuelva a explicar: debe aparecer INDEX RANGE SCAN y el costo baja.

-- 2) ESTADISTICAS
SELECT table_name, num_rows, blocks, TO_CHAR(last_analyzed,'YYYY-MM-DD HH24:MI') FROM dba_tables WHERE owner='USR_TUNING';
SELECT table_name, stale_stats FROM dba_tab_statistics WHERE owner='USR_TUNING' AND object_type='TABLE';
--    Recolecte desde la app y repita la primera consulta: num_rows = 200000.

-- 3) INDICES
SELECT index_name, table_name, uniqueness, status FROM dba_indexes WHERE owner='USR_TUNING';
SELECT index_name, column_name, column_position FROM dba_ind_columns WHERE index_owner='USR_TUNING' ORDER BY 1,3;
SELECT name, total_access_count, last_used FROM dba_index_usage WHERE owner='USR_TUNING';
