# VKNT POS Bot

Bot de Discord para llevar el control de pago de renta de Outposts (EVE Online).
Antes usaba SQLite; ahora usa **PostgreSQL + Prisma** (`prisma-client-py`).

## ⚠️ Antes que nada: rota el token de Discord

El `.env` con el `DISCORD_TOKEN` viejo estuvo commiteado en el repo. Ya se limpió
del historial de git de esta rama, pero **el token debe considerarse expuesto**
igual (estuvo pusheado a GitHub). Andá a
https://discord.com/developers/applications → tu aplicación → Bot → **Reset Token**,
y usá el token nuevo en todos lados (nunca el viejo).

## Estructura

```
bot/
  main.py            # entry point, setup del bot y sync de comandos
  config.py          # variables de entorno
  db.py              # cliente Prisma (singleton)
  checks.py          # validación de rol CEO
  utils.py           # matemática de meses, formateo, paginación
  ui.py              # View con botones para paginar
  commands/
    outposts.py      # /registrar-pos /borrar-pos /reporte
    pagos.py         # modal de pago, menú contextual, /corregir-pago /historial-pos
    sistemas.py       # /sistema-agregar /sistema-listar /sistema-borrar
    recordatorios.py  # /recordar-mora
prisma/
  schema.prisma
  migrations/
scripts/
  migrate_from_sqlite.py   # migración one-shot desde el eve_pos.db viejo
```

## Variables de entorno

Copiá `.env.example` a `.env` y completá:

- `DISCORD_TOKEN`: token del bot (el nuevo, rotado).
- `CEO_ROLE_ID`: ID del rol de Discord autorizado para los comandos de gestión.
- `DATABASE_URL`: connection string de Postgres, ej. `postgresql://user:pass@host:5432/db`.

## Correr localmente

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python -m prisma generate
python -m prisma migrate deploy   # aplica las migraciones existentes

python -m bot.main
```

## Migrar los datos viejos (una sola vez)

Con `DATABASE_URL` apuntando a la base nueva (local o de Railway) y el archivo
`eve_pos.db` a mano:

```bash
DATABASE_URL="postgresql://..." python3 scripts/migrate_from_sqlite.py eve_pos.db
```

Es idempotente (usa upsert), así que se puede correr de nuevo sin duplicar datos
si algo falla a la mitad.

## Desplegar en Railway

1. **Crear el servicio de Postgres**: en tu proyecto de Railway, `+ New` →
   `Database` → `PostgreSQL`. Railway genera automáticamente una variable
   `DATABASE_URL` en ese servicio.
2. **Crear el servicio del bot**: `+ New` → `GitHub Repo` → elegí este repo y la
   rama que quieras desplegar. Railway detecta el `Dockerfile` automáticamente
   (ya incluido en este repo) y lo usa para el build.
3. **Variables de entorno del servicio del bot**:
   - `DISCORD_TOKEN`: tu token rotado.
   - `CEO_ROLE_ID`: el ID del rol CEO.
   - `DATABASE_URL`: referenciá la del servicio de Postgres con
     `${{Postgres.DATABASE_URL}}` (Railway resuelve la referencia entre
     servicios automáticamente), en vez de copiarla a mano.
4. **Deploy**. El contenedor corre `prisma migrate deploy` antes de arrancar el
   bot, así que las migraciones se aplican solas en cada deploy.
5. **Migración de datos**: corré `scripts/migrate_from_sqlite.py` una vez desde
   tu máquina apuntando el `DATABASE_URL` a la base de Railway (Railway te la
   muestra en la pestaña "Connect" del servicio Postgres), o usá
   `railway run` si tenés el CLI instalado.
6. Este servicio **no necesita dominio público** — es un worker que solo
   mantiene conexión saliente con Discord y Postgres. No hace falta exponer
   ningún puerto.

## Comandos disponibles

| Comando | Quién | Descripción |
|---|---|---|
| `/ayuda` | Todos | Explica todos los comandos (respuesta solo visible para vos) |
| `/registrar-pos` | CEO | Registra una nueva POS (el ID se asigna solo, no hace falta capturarlo) |
| `/borrar-pos` | CEO | Elimina una POS |
| `/buscar` | CEO | Busca todas las POS de un usuario (respuesta solo visible para vos) y permite elegir una para editarla (nombre + estado de pago) |
| `/reporte` | CEO | Lista de POS en Embeds, con filtro (todos/morosos/al día) y ordenada por urgencia |
| `/corregir-pago` | CEO | Resta meses por error, queda en el historial |
| `/historial-pos` | CEO | Historial de pagos/correcciones de una POS |
| `/recordar-mora` | CEO | Etiqueta a quienes no tienen pagado el mes actual |
| `/sistema-agregar` | CEO | Agrega un sistema EVE a la lista |
| `/sistema-listar` | Todos | Lista los sistemas disponibles |
| `/sistema-borrar` | CEO | Elimina un sistema (si no tiene POS asignadas) |
| Clic derecho → "Pagar Outpost" | CEO | Abre el modal de pago (meses + monto opcional). Si el usuario tiene varias POS, primero pide elegir cuál |

## Notas

- Un mismo usuario puede tener cualquier cantidad de POS registradas; tanto el pago (clic derecho) como la búsqueda/edición (`/buscar`) piden elegir cuál cuando hay más de una.
- `pagado_hasta_mes = 0` significa "pendiente" (nunca pagó).
- Cada pago o corrección queda registrado en la tabla `Pago` con quién lo hizo,
  cuándo, cuántos meses y el monto (si se cargó).
- Los sistemas EVE ya no están hardcodeados: se administran con
  `/sistema-agregar` / `/sistema-borrar` y aparecen por autocompletado.
