-- sqlplus / as sysdba
ALTER SESSION SET CONTAINER = XEPDB1;
SET LINESIZE 220 PAGESIZE 100
COL tablespace_name FORMAT A20
COL file_name FORMAT A70

-- Debe coincidir con la tabla "Tablespaces" de la pantalla
SELECT t.tablespace_name, t.status, ROUND(d.total_mb,1) total_mb,
       ROUND(d.total_mb - NVL(f.free_mb,0),1) used_mb, ROUND(NVL(f.free_mb,0),1) free_mb
FROM dba_tablespaces t
LEFT JOIN (SELECT tablespace_name, SUM(bytes)/1048576 total_mb FROM dba_data_files GROUP BY tablespace_name) d
       ON d.tablespace_name = t.tablespace_name
LEFT JOIN (SELECT tablespace_name, SUM(bytes)/1048576 free_mb FROM dba_free_space GROUP BY tablespace_name) f
       ON f.tablespace_name = t.tablespace_name
ORDER BY 1;

-- Datafiles
SELECT tablespace_name, file_name, bytes/1048576 mb, autoextensible FROM dba_data_files ORDER BY 1;

-- Tras crear TS_PRUEBA desde la app:
-- SELECT tablespace_name, status FROM dba_tablespaces WHERE tablespace_name='TS_PRUEBA';
