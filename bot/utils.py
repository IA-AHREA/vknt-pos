from datetime import datetime

MESES_NOMBRES = [
    "❌ Pendiente", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
]


def nombre_mes(mes: int) -> str:
    return MESES_NOMBRES[mes]


def sumar_meses(anio_base: int, mes_base: int, cantidad: int) -> tuple[int, int]:
    """Suma `cantidad` meses (puede ser negativa) a mes_base/anio_base.

    mes_base puede ser 0 (Pendiente); en ese caso se toma como el mes
    anterior al actual para que la suma arranque desde "ahora".
    """
    if mes_base == 0:
        mes_base = datetime.now().month - 1

    total_meses = anio_base * 12 + mes_base + cantidad
    nuevo_anio, nuevo_mes = divmod(total_meses - 1, 12)
    return nuevo_anio, nuevo_mes + 1


def estado_texto(mes: int, anio: int) -> str:
    return f"{nombre_mes(mes)} {anio}" if mes > 0 else nombre_mes(mes)


def a_total_meses(anio: int, mes: int) -> int:
    return anio * 12 + mes


def es_moroso(outpost, anio_actual: int, mes_actual: int) -> bool:
    if outpost.pagado_hasta_mes == 0:
        return True
    if outpost.anio_vencimiento < anio_actual:
        return True
    return outpost.anio_vencimiento == anio_actual and outpost.pagado_hasta_mes < mes_actual


def construir_paginas(
    filas: list,
    fmt_fila,
    header: str,
    separator: str,
    items_por_pagina: int = 5,
    titulo: str = "",
) -> list[str]:
    """Arma una lista de strings, uno por página, listos para mostrar."""
    if not filas:
        return [f"{titulo}\nNo hay datos." if titulo else "No hay datos."]

    total_paginas = -(-len(filas) // items_por_pagina)  # ceil div
    paginas = []
    for pagina in range(total_paginas):
        inicio = pagina * items_por_pagina
        bloque = filas[inicio:inicio + items_por_pagina]
        cuerpo = "".join(fmt_fila(f) for f in bloque)
        texto = f"{titulo}\n```\n{header}{separator}{cuerpo}\nPágina {pagina + 1}/{total_paginas}```"
        paginas.append(texto)
    return paginas
