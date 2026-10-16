-- sqlplus / as sysdba
ALTER SESSION SET CONTAINER = XEPDB1;
SET LINESIZE 200 PAGESIZE 100
COL username FORMAT A20
COL profile FORMAT A20
COL grantee FORMAT A20
COL privilege FORMAT A30

-- Lista de usuarios (pantalla "Usuarios")
SELECT username, account_status, default_tablespace, temporary_tablespace, profile
FROM dba_users WHERE oracle_maintained='N' ORDER BY 1;

-- Roles, privilegios y cuotas de un usuario creado desde la app (cambie USR_PRUEBA)
SELECT grantee, granted_role FROM dba_role_privs WHERE grantee='USR_PRUEBA';
SELECT grantee, privilege FROM dba_sys_privs WHERE grantee='USR_PRUEBA';
SELECT username, tablespace_name, bytes, max_bytes FROM dba_ts_quotas WHERE username='USR_PRUEBA';

-- Perfiles
SELECT profile, resource_name, limit FROM dba_profiles
WHERE resource_name IN ('FAILED_LOGIN_ATTEMPTS','PASSWORD_LIFE_TIME','SESSIONS_PER_USER') ORDER BY 1,2;

-- Sesiones
SELECT sid, serial#, username, status FROM v$session WHERE type='USER' AND username IS NOT NULL;

-- Probar login del usuario creado:  CONNECT usr_prueba/clave@localhost:1521/XEPDB1
