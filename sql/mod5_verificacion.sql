-- sqlplus / as sysdba
ALTER SESSION SET CONTAINER = XEPDB1;
SET LINESIZE 220 PAGESIZE 100
COL archivo FORMAT A45
COL objetos FORMAT A40

-- Historial de recuperaciones
SELECT id, tipo, objetos, archivo, estado, TO_CHAR(inicio,'YYYY-MM-DD HH24:MI:SS') inicio
FROM system.bkp_historial WHERE operacion='IMPORT' ORDER BY id DESC;

-- Prueba sugerida (con el usuario USR_PRUEBA y una tabla T1 respaldada en el modulo 4):
--   1) Respaldar USR_PRUEBA (modulo 4).
--   2) En SQL*Plus:  DROP TABLE usr_prueba.t1;   (o DROP USER usr_prueba CASCADE;)
--   3) Restaurar desde la app (modo SCHEMA o TABLE).
--   4) Verificar:
SELECT owner, table_name FROM dba_tables WHERE owner='USR_PRUEBA';
SELECT COUNT(*) FROM usr_prueba.t1;
-- Prueba de remap: restaurar con origen USR_PRUEBA y destino USR_COPIA, luego:
SELECT owner, table_name FROM dba_tables WHERE owner='USR_COPIA';
-- Datapump activos:
SELECT owner_name, job_name, operation, state FROM dba_datapump_jobs;
