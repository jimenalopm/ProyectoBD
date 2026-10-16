# Manual de usuario — Admin Oracle 21c XE

EIF-402 Administración de Bases de Datos · Universidad Nacional, Sede Interuniversitaria de Alajuela

## 1. Requisitos e inicio
1. Servicios `OracleServiceXE` y `OracleOraDB21Home1TNSListener` en ejecución.
2. Copie `.env.example` a `.env` y escriba la contraseña de SYS.
3. En la carpeta del proyecto ejecute `python app.py` y abra `http://localhost:5000`.

La pantalla **Inicio** muestra la instancia, la versión, el contenedor (XEPDB1), el modo de archivado y el tamaño de los datafiles. Si aparece un error de conexión, revise `.env` y que el listener esté activo. El menú lateral da acceso a todos los módulos.

## 2. Tablespaces
Muestra cada tablespace con tamaño, espacio usado y libre y barra de porcentaje (verde, amarillo > 70 %, rojo > 85 %).
- **Crear tablespace:** nombre, tamaño (`100M`, `1G`), ruta opcional y autoextend.
- **Agregar datafile**, **Resize** y **Autoextend ON/OFF** en la tabla de datafiles.
- **Offline / Online** por tablespace.
- **Eliminar:** pide escribir el nombre; borra contenido y datafiles. Los tablespaces del sistema están protegidos.

## 3. Seguridad de usuarios
Pestañas **Usuarios**, **Perfiles** y **Sesiones**.
- **Crear usuario** con contraseña, tablespace por defecto y temporal, perfil, cuota y `CREATE SESSION`.
- Por usuario: bloquear/desbloquear, cambiar contraseña y eliminar (CASCADE, con confirmación).
- Al hacer clic en el nombre: roles, privilegios de sistema y de objeto, y cuotas; se puede otorgar (con ADMIN OPTION) y revocar.
- **Perfiles:** crear, modificar límites (intentos fallidos, vida de la contraseña, sesiones, etc.) y eliminar.
- **Sesiones:** lista de sesiones de usuario y botón para terminarlas.

## 4. Auditoría
- **Políticas:** cree una política de auditoría unificada eligiendo acciones de sistema (LOGON, CREATE TABLE, DROP USER…) o acciones sobre un objeto (`ESQUEMA.TABLA`). Puede habilitarla para todos o para un usuario. Cada política se puede habilitar, deshabilitar o eliminar.
- **Registros:** consulta del trail (`UNIFIED_AUDIT_TRAIL`) con filtros por usuario, acción, fechas y resultado. El botón **Limpiar** borra el trail tras escribir `LIMPIAR`.

## 5. Respaldos
1. En **Directorio de respaldos** indique la ruta (por defecto la de `DATA_PUMP_DIR`) y pulse el botón; se crea el DIRECTORY `BACKUP_DIR`.
2. En **Nuevo respaldo** elija el tipo:
   - **Por schema(s):** seleccione uno o varios esquemas.
   - **Por tabla(s):** elija el esquema y luego las tablas.
   - **Full:** toda la base de datos.
   También puede exportar solo la estructura o solo los datos.
3. El respaldo corre en segundo plano; el **Historial** se actualiza solo y muestra estado (OK, ADVERTENCIA, ERROR), duración y tamaño. **Ver log** abre el log de Data Pump.

## 6. Recuperación
Elija un archivo `.dmp` del directorio, el modo (**SCHEMA**, **TABLE** o **FULL**) y qué hacer si la tabla existe (`SKIP`, `APPEND`, `TRUNCATE`, `REPLACE`).
- Para otro esquema use **Remap** (origen → destino).
- FULL exige escribir `FULL` para confirmar.
El historial de recuperaciones y sus logs aparecen debajo.

## 7. Archivos de respaldo
- Lista de `.dmp` y `.log` con tamaño, fecha y antigüedad; **descargar**, **renombrar** y **eliminar** (opcionalmente con su log).
- **Política de retención:** indique los días, vea qué archivos se afectan (resaltados) y elimine los antiguos.
- Espacio en disco y administración de directorios de Oracle (`DBA_DIRECTORIES`): crear y eliminar los creados por usuarios.

## 8. Performance
Panel con sesiones, métricas del sistema, ratios (buffer cache, library cache), memoria SGA/PGA, principales esperas, **Top 10 SQL** (ordenable por tiempo, CPU, lecturas, buffer gets o ejecuciones), sesiones activas y bloqueos. Active «Actualizar cada 10 s» para monitoreo continuo.

## 9. Tuning de consultas
- **Plan de ejecución:** escriba una sentencia, elija el esquema y pulse **Explicar plan** (no la ejecuta). **Ejecutar y medir** corre un SELECT y muestra tiempo y plan real. Al repetir la misma sentencia se muestra el plan anterior y si el costo mejoró.
- **Estadísticas:** por esquema, vea filas, bloques, último análisis y si están obsoletas; recolecte (tabla o esquema) o borre.
- **Índices:** liste índices con columnas, estado y uso; cree (normal o UNIQUE), reconstruya o elimine.

## 10. Verificación con SQL*Plus
La carpeta `sql/` incluye un script por módulo con las consultas equivalentes (`sqlplus / as sysdba`, luego `ALTER SESSION SET CONTAINER = XEPDB1;`).
