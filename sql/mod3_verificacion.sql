-- sqlplus / as sysdba
ALTER SESSION SET CONTAINER = XEPDB1;
SET LINESIZE 220 PAGESIZE 100
COL policy_name FORMAT A30
COL entity_name FORMAT A20
COL dbusername FORMAT A15
COL action_name FORMAT A20
COL object_name FORMAT A25

-- Auditoria unificada activa?
SELECT parameter, value FROM v$option WHERE parameter='Unified Auditing';

-- Politicas y a quien estan habilitadas (pantalla "Politicas")
SELECT policy_name, COUNT(*) acciones FROM audit_unified_policies GROUP BY policy_name ORDER BY 1;
SELECT policy_name, enabled_option, entity_name, success, failure FROM audit_unified_enabled_policies ORDER BY 1;

-- Ultimos registros (pantalla "Registros")
SELECT TO_CHAR(event_timestamp,'YYYY-MM-DD HH24:MI:SS') fecha, dbusername, action_name,
       object_name, return_code
FROM unified_audit_trail ORDER BY event_timestamp DESC FETCH FIRST 20 ROWS ONLY;

-- Prueba sugerida: cree una politica con LOGON desde la app, conectese con otro usuario
-- (CONNECT usr_prueba/clave@localhost:1521/XEPDB1) y vuelva a ejecutar la consulta anterior.
-- El trail se escribe en cola: para ver los ultimos eventos al instante ejecute:
--   EXEC DBMS_AUDIT_MGMT.FLUSH_UNIFIED_AUDIT_TRAIL;
