# Admin Oracle 21c XE — Proyecto final EIF-402

Aplicación web (Python + Flask) para administrar una base de datos Oracle 21c XE:
tablespaces, seguridad de usuarios, auditoría, respaldos y recuperación con Data Pump,
administración de archivos de respaldo, performance y tuning de consultas.

## Requisitos
- Oracle Database 21c XE (servicio `OracleServiceXE` y listener activos).
- `expdp` / `impdp` en el `PATH` (carpeta `bin` de ORACLE_HOME).
- Python 3.10+.

## Instalación
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env      # luego edite .env y ponga la contraseña de SYS
python app.py
```
Abra http://localhost:5000.

## Configuración (`.env`)
| Variable | Descripción | Por defecto |
|---|---|---|
| DB_USER / DB_PASSWORD | Usuario administrador (conecta como SYSDBA) | SYS / — |
| DB_HOST / DB_PORT | Listener | localhost / 1521 |
| DB_SERVICE | Servicio: `XEPDB1` (PDB) o `XE` (CDB) | XEPDB1 |
| DB_SYSDBA | Conectar con privilegio SYSDBA | true |

## Módulos
| Módulo | Ruta | Verificación en SQL*Plus |
|---|---|---|
| Inicio | `/` | `sql/mod0_verificacion.sql` |
| Tablespaces | `/tablespaces` | `sql/mod1_verificacion.sql` |
| Seguridad de usuarios | `/usuarios` | `sql/mod2_verificacion.sql` |
| Auditoría | `/auditoria` | `sql/mod3_verificacion.sql` |
| Respaldos | `/respaldos` | `sql/mod4_verificacion.sql` |
| Recuperación | `/recuperacion` | `sql/mod5_verificacion.sql` |
| Archivos de respaldo | `/archivos` | `sql/mod6_verificacion.sql` |
| Performance | `/performance` | `sql/mod7_verificacion.sql` |
| Tuning de consultas | `/tuning` | `sql/mod8_verificacion.sql` |

## Notas
- Los respaldos usan un DIRECTORY de Oracle llamado `BACKUP_DIR`; el servicio Oracle debe poder escribir en su ruta.
- El historial de respaldos y recuperaciones se guarda en `SYSTEM.BKP_HISTORIAL`.
- La app conecta como SYSDBA: úsela solo en un entorno de laboratorio.
