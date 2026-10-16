-- sqlplus / as sysdba
ALTER SESSION SET CONTAINER = XEPDB1;
SET LINESIZE 200 PAGESIZE 100
COL directory_name FORMAT A25
COL directory_path FORMAT A80

-- Directorios de Oracle (misma lista que la pantalla)
SELECT directory_name, directory_path FROM dba_directories ORDER BY 1;

-- Directorios creados por usuarios (los unicos que la app permite eliminar)
SELECT d.directory_name FROM dba_directories d
JOIN dba_objects o ON o.object_name = d.directory_name AND o.object_type='DIRECTORY'
WHERE o.oracle_maintained='N';

-- Prueba sugerida:
--   1) En la app crear el directorio DIR_PRUEBA con ruta C:\app\Jimen\prueba_dir y verificar arriba.
--   2) Listar archivos desde SQL*Plus con HOST (equivale a la tabla de la pantalla):
--        HOST dir "C:\ruta\de\BACKUP_DIR"
--   3) Renombrar / eliminar un .log desde la app y repetir HOST dir.
--   4) Eliminar DIR_PRUEBA desde la app y repetir la consulta de dba_directories.
