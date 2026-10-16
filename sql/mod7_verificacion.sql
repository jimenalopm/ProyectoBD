-- sqlplus / as sysdba
ALTER SESSION SET CONTAINER = XEPDB1;
SET LINESIZE 220 PAGESIZE 100
COL metric_name FORMAT A40
COL event FORMAT A45
COL sql_text FORMAT A60

-- Resumen de sesiones
SELECT COUNT(*) total, SUM(CASE WHEN status='ACTIVE' THEN 1 ELSE 0 END) activas
FROM v$session WHERE type='USER';

-- Metricas del sistema
SELECT metric_name, ROUND(value,2) value FROM v$sysmetric
WHERE metric_name IN ('Host CPU Utilization (%)','Buffer Cache Hit Ratio','Library Cache Hit Ratio','Average Active Sessions');

-- Buffer cache hit ratio
SELECT ROUND((1 - phy.value / (db.value + cons.value)) * 100, 2) buffer_hit
FROM v$sysstat phy, v$sysstat db, v$sysstat cons
WHERE phy.name='physical reads cache' AND db.name='db block gets from cache' AND cons.name='consistent gets from cache';

-- Top esperas
SELECT event, wait_class, total_waits, ROUND(time_waited_micro/1000000,2) segundos
FROM v$system_event WHERE wait_class <> 'Idle' ORDER BY time_waited_micro DESC FETCH FIRST 10 ROWS ONLY;

-- Top SQL por tiempo
SELECT sql_id, parsing_schema_name, executions, ROUND(elapsed_time/1000,1) elapsed_ms, SUBSTR(sql_text,1,60) sql_text
FROM v$sql WHERE executions > 0 ORDER BY elapsed_time DESC FETCH FIRST 10 ROWS ONLY;

-- Memoria
SELECT name, ROUND(bytes/1048576,1) mb FROM v$sgainfo WHERE name IN ('Buffer Cache Size','Shared Pool Size','Maximum SGA Size');
SELECT name, ROUND(value/1048576,1) mb FROM v$pgastat WHERE name IN ('total PGA allocated','aggregate PGA target parameter');

-- Prueba de bloqueo (dos sesiones SQL*Plus con un usuario de prueba):
--   Sesion 1: UPDATE t1 SET c=c WHERE id=1;   (sin COMMIT)
--   Sesion 2: UPDATE t1 SET c=c WHERE id=1;   (queda esperando)
--   La pantalla debe mostrar la fila en "Bloqueos". Consulta equivalente:
SELECT sid, blocking_session, event, seconds_in_wait FROM v$session WHERE blocking_session IS NOT NULL;
