-- Ejecutar: sqlplus / as sysdba   (luego: ALTER SESSION SET CONTAINER=XEPDB1;)
ALTER SESSION SET CONTAINER = XEPDB1;
SET LINESIZE 200
SELECT instance_name, host_name, version_full, status FROM v$instance;
SELECT name, open_mode, log_mode FROM v$database;
SELECT SYS_CONTEXT('USERENV','CON_NAME') con_name FROM dual;
SELECT ROUND(SUM(bytes)/1024/1024) mb_datafiles FROM dba_data_files;
