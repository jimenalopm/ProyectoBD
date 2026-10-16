# Guion de demostración (≈ 15 min)

Preparación: servicios Oracle activos, `.env` listo, `python app.py`, una ventana SQL*Plus (`sqlplus / as sysdba` → `ALTER SESSION SET CONTAINER = XEPDB1;`).

1. **Inicio** (1 min): estado de la instancia; compare con `SELECT * FROM v$instance`.
2. **Tablespaces** (2 min): crear `TS_DEMO` 50M con autoextend, agregar datafile, resize; verificar en `dba_data_files`; eliminar.
3. **Usuarios** (2 min): crear `USR_DEMO` (tablespace `USERS`, cuota 50M, CREATE SESSION); otorgar `CREATE TABLE`; conectarse con SQL*Plus y crear tabla `T1` con datos. Mostrar perfil y bloquear/desbloquear.
4. **Auditoría** (2 min): política `POL_DEMO` con LOGON + CREATE TABLE para `USR_DEMO`; reconectarse; mostrar en Registros.
5. **Respaldos** (2 min): respaldo por schema `USR_DEMO`, por tabla `USR_DEMO.T1` y full; mostrar historial y log; ver los `.dmp` en disco.
6. **Recuperación** (2 min): `DROP TABLE usr_demo.t1`; restaurar por tabla; `SELECT COUNT(*)` para validar. Restaurar con remap a `USR_COPIA`.
7. **Archivos** (1 min): descargar, renombrar, política de retención, directorios Oracle.
8. **Performance** (1 min): bloqueo con dos sesiones SQL*Plus visible en «Bloqueos»; Top SQL.
9. **Tuning** (2 min): tabla con 200 000 filas → plan con FULL SCAN, crear índice, nuevo plan con INDEX RANGE SCAN y costo menor; recolectar estadísticas.

Limpieza: eliminar `USR_DEMO`, `USR_COPIA`, política `POL_DEMO` y archivos de prueba.
