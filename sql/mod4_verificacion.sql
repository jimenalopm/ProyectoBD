-- sqlplus / as sysdba
ALTER SESSION SET CONTAINER = XEPDB1;
SET LINESIZE 220 PAGESIZE 100
COL directory_name FORMAT A20
COL directory_path FORMAT A70
COL operacion FORMAT A9
COL archivo FORMAT A45

-- Directorio creado desde la app
SELECT directory_name, directory_path FROM dba_directories WHERE directory_name IN ('BACKUP_DIR','DATA_PUMP_DIR');

-- Historial de operaciones (tabla propia de la app)
SELECT id, operacion, tipo, archivo, estado, tamano_mb, TO_CHAR(inicio,'YYYY-MM-DD HH24:MI:SS') inicio
FROM system.bkp_historial ORDER BY id DESC;

-- Mismo respaldo por linea de comandos (otra terminal), para comparar:
--   expdp system/CLAVE@localhost:1521/XEPDB1 schemas=USR_PRUEBA directory=BACKUP_DIR dumpfile=manual.dmp logfile=manual.log
-- Y verificar que el archivo .dmp existe en la ruta de BACKUP_DIR (dir "ruta").
-- Trabajos Data Pump activos:
SELECT owner_name, job_name, operation, state FROM dba_datapump_jobs;
