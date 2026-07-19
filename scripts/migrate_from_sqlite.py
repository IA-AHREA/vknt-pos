"""Migra los datos del eve_pos.db (SQLite) viejo hacia Postgres via Prisma.

Uso:
    DATABASE_URL=postgresql://... python3 scripts/migrate_from_sqlite.py [ruta_al_db]

Es idempotente: se puede correr más de una vez sin duplicar datos
(usa upsert tanto para sistemas como para outposts).
"""

import asyncio
import re
import sqlite3
import sys
from pathlib import Path

from prisma import Prisma

DISCORD_ID_RE = re.compile(r"\d+")


def extraer_discord_id(valor: str) -> str:
    """El esquema viejo guardaba el discord_id como '<@123456789>'."""
    match = DISCORD_ID_RE.search(valor)
    if not match:
        raise ValueError(f"No se pudo extraer un discord_id de: {valor!r}")
    return match.group(0)


async def migrar(ruta_db: str) -> None:
    if not Path(ruta_db).exists():
        raise SystemExit(f"No se encontró el archivo {ruta_db}")

    conn = sqlite3.connect(ruta_db)
    conn.row_factory = sqlite3.Row
    filas = conn.execute(
        "SELECT id_num, discord_id, nombre_outpost, sistema, pagado_hasta_mes, anio_vencimiento "
        "FROM outposts"
    ).fetchall()
    conn.close()

    print(f"Encontrados {len(filas)} outposts en {ruta_db}.")

    db = Prisma()
    await db.connect()
    try:
        sistemas_creados = {}
        for fila in filas:
            nombre_sistema = fila["sistema"]
            if nombre_sistema in sistemas_creados:
                continue
            sistema = await db.sistema.upsert(
                where={"nombre": nombre_sistema},
                data={
                    "create": {"nombre": nombre_sistema},
                    "update": {},
                },
            )
            sistemas_creados[nombre_sistema] = sistema.id
            print(f"  Sistema listo: {nombre_sistema}")

        for fila in filas:
            discord_id = extraer_discord_id(fila["discord_id"])
            await db.outpost.upsert(
                where={"id_num": fila["id_num"]},
                data={
                    "create": {
                        "id_num": fila["id_num"],
                        "discord_id": discord_id,
                        "nombre_pos": fila["nombre_outpost"],
                        "sistema_id": sistemas_creados[fila["sistema"]],
                        "pagado_hasta_mes": fila["pagado_hasta_mes"],
                        "anio_vencimiento": fila["anio_vencimiento"],
                    },
                    "update": {
                        "discord_id": discord_id,
                        "nombre_pos": fila["nombre_outpost"],
                        "sistema_id": sistemas_creados[fila["sistema"]],
                        "pagado_hasta_mes": fila["pagado_hasta_mes"],
                        "anio_vencimiento": fila["anio_vencimiento"],
                    },
                },
            )
            print(f"  POS #{fila['id_num']} ({fila['nombre_outpost']}) migrada.")

        print(f"\n✅ Migración completa: {len(filas)} outposts, {len(sistemas_creados)} sistemas.")
    finally:
        await db.disconnect()


if __name__ == "__main__":
    ruta = sys.argv[1] if len(sys.argv) > 1 else "eve_pos.db"
    asyncio.run(migrar(ruta))
