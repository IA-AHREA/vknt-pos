import discord
from discord.ext import commands
from discord import app_commands, ui
import sqlite3
import os
from dotenv import load_dotenv
import math
from datetime import datetime

# Cargar configuración
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
ID_ROL_CEO = int(os.getenv('CEO_ROLE_ID'))

class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True  
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        self.tree.add_command(registrar_pago_context)
        await self.tree.sync()
        print(f"✅ Bot iniciado como {self.user}")

bot = MyBot()

def es_ceo(interaction: discord.Interaction) -> bool:
    return any(role.id == ID_ROL_CEO for role in interaction.user.roles)

# --- COMANDO: REGISTRAR POS ---
@bot.tree.command(name="registrar-pos", description="Registra un Outpost con ID único (100-999)")
@app_commands.choices(sistema=[
    app_commands.Choice(name="CU9-T0", value="CU9-T0"),
    app_commands.Choice(name="94-H3F", value="94-H3F"),
    app_commands.Choice(name="XCF-8N", value="XCF-8N"),
    app_commands.Choice(name="N-H32Y", value="N-H32Y"),
    app_commands.Choice(name="EL8-4Q", value="EL8-4Q"),
    app_commands.Choice(name="5-9WNU", value="5-9WNU"),
    app_commands.Choice(name="D7T-C0", value="D7T-C0"),
])
async def registrar_pos(interaction: discord.Interaction, 
                        id_id: app_commands.Range[int, 100, 999], 
                        dueño: discord.Member, 
                        nombre_pos: str, 
                        sistema: app_commands.Choice[str]):
    if not es_ceo(interaction): return await interaction.response.send_message("❌ No autorizado", ephemeral=True)

    try:
        conn = sqlite3.connect('eve_pos.db')
        cursor = conn.cursor()
        mencion_id = f"<@{dueño.id}>"
        anio_actual = datetime.now().year
        cursor.execute('INSERT INTO outposts (id_num, discord_id, nombre_outpost, sistema, pagado_hasta_mes, anio_vencimiento) VALUES (?, ?, ?, ?, 0, ?)', 
                        (id_id, mencion_id, nombre_pos, sistema.value, anio_actual))
        conn.commit()
        conn.close()
        await interaction.response.send_message(f"✅ POS #{id_id} registrada para {mencion_id} en {sistema.value}.")
    except sqlite3.IntegrityError:
        await interaction.response.send_message(f"❌ El ID {id_id} ya existe.", ephemeral=True)

# --- LÓGICA DE PAGO (MODAL) ---
class PagoModal(ui.Modal, title='Registrar Meses de Pago'):
    meses_input = ui.TextInput(label='¿Cuántos meses paga?', placeholder='Ej: 1 o 12', default='1')

    def __init__(self, id_num, nombre):
        super().__init__()
        self.id_num = id_num
        self.nombre = nombre

    async def on_submit(self, interaction: discord.Interaction):
        try:
            cant_meses = int(self.meses_input.value)
            conn = sqlite3.connect('eve_pos.db')
            cursor = conn.cursor()
            
            cursor.execute('SELECT pagado_hasta_mes, anio_vencimiento FROM outposts WHERE id_num = ?', (self.id_num,))
            res = cursor.fetchone()
            mes_actual_db, anio_actual_db = res

            # Si el mes es 0, tomamos el mes anterior al actual para que la suma empiece correctamente
            base_mes = mes_actual_db if mes_actual_db > 0 else datetime.now().month - 1
            total_meses = (anio_actual_db * 12 + base_mes) + cant_meses
            
            nuevo_anio = (total_meses - 1) // 12
            nuevo_mes = total_meses % 12
            if nuevo_mes == 0: nuevo_mes = 12

            cursor.execute('UPDATE outposts SET pagado_hasta_mes = ?, anio_vencimiento = ? WHERE id_num = ?', 
                           (nuevo_mes, nuevo_anio, self.id_num))
            conn.commit()
            conn.close()

            meses_nombres = ["Pendiente", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
            await interaction.response.send_message(f"✅ Pago registrado para #{self.id_num}. Pagado hasta: **{meses_nombres[nuevo_mes]} {nuevo_anio}**")
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)

# --- CLIC DERECHO PARA PAGAR ---
@app_commands.context_menu(name="Pagar Outpost")
async def registrar_pago_context(interaction: discord.Interaction, message: discord.Message):
    if not es_ceo(interaction): return
    conn = sqlite3.connect('eve_pos.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id_num, nombre_outpost FROM outposts WHERE discord_id = ?', (f"<@{message.author.id}>",))
    res = cursor.fetchone()
    conn.close()
    if not res: return await interaction.response.send_message("❌ Usuario no registrado.", ephemeral=True)
    await interaction.response.send_modal(PagoModal(res[0], res[1]))

# --- REPORTE ---
@bot.tree.command(name="reporte", description="Ver lista de pagos")
async def reporte(interaction: discord.Interaction, pagina: int = 1):
    if not es_ceo(interaction): return
    conn = sqlite3.connect('eve_pos.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id_num, discord_id, nombre_outpost, pagado_hasta_mes, sistema, anio_vencimiento FROM outposts')
    filas = cursor.fetchall()
    conn.close()

    if not filas: return await interaction.response.send_message("No hay datos.")
    
    items_por_pagina = 5
    max_paginas = math.ceil(len(filas) / items_por_pagina)
    inicio = (pagina - 1) * items_por_pagina
    
    meses_nombres = ["❌ Pendiente", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
    header = f"{'ID':<4} | {'Dueño':<22} | {'Outpost':<15} | {'Estado':<11} | {'Sistema'}\n"
    separator = "-"*4 + "+" + "-"*24 + "+" + "-"*17 + "+" + "-"*13 + "+" + "-"*10 + "\n"
    tabla = "```\n" + header + separator
    
    for id_n, d_id, n_pos, mes, sist, anio in filas[inicio:inicio+items_por_pagina]:
        estado = f"{meses_nombres[mes]}"
        tabla += f"#{id_n:<3} | {d_id:<22} | {n_pos[:15]:<15} | {estado:<11} | {sist}\n"
    
    tabla += f"\nPagina {pagina}/{max_paginas}```"
    await interaction.response.send_message(tabla)

# --- COMANDO: RECORDATORIO DE MORA (DINÁMICO) ---
@bot.tree.command(name="recordar-mora", description="Etiqueta a quienes deban meses anteriores al mes límite")
@app_commands.describe(mes_limite="Si pones 2, etiqueta a los que tienen pagado Enero o Pendiente (1 o 0)")
async def recordar_mora(interaction: discord.Interaction, mes_limite: app_commands.Range[int, 1, 12]):
    if not es_ceo(interaction): 
        return await interaction.response.send_message("❌ No autorizado", ephemeral=True)

    await interaction.response.defer()

    conn = sqlite3.connect('eve_pos.db')
    cursor = conn.cursor()
    anio_actual = datetime.now().year

    # Buscamos: Pendientes (0), años anteriores, o mes del año actual menor al limite
    cursor.execute('''
        SELECT discord_id, id_num, nombre_outpost, pagado_hasta_mes, anio_vencimiento, sistema 
        FROM outposts 
        WHERE pagado_hasta_mes = 0 
           OR anio_vencimiento < ? 
           OR (anio_vencimiento = ? AND pagado_hasta_mes < ?)
    ''', (anio_actual, anio_actual, mes_limite))
    
    morosos = cursor.fetchall()
    conn.close()

    if not morosos:
        return await interaction.followup.send(f"✅ Todos están al día con el mes {mes_limite}.")

    meses_nombres = ["Pendiente", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
    menciones = []
    for d_id_raw, id_n, nombre_pos, mes_p, anio_p, sist in morosos:
        estado_txt = f"{meses_nombres[mes_p]} {anio_p}"
        menciones.append(f"- {d_id_raw} | POS #{id_n} ({nombre_pos}) en **{sist}** | Pago: {estado_txt}")

    lista_final = "\n".join(menciones)
    nombre_mes_limite = meses_nombres[mes_limite]

    mensaje_alerta = (
        f"⚠️ **RECORDATORIO DE COBRO - MES {nombre_mes_limite.upper()}** ⚠️\n"
        f"Los siguientes pilotos tienen pagos pendientes o meses anteriores a {nombre_mes_limite}:\n\n"
        f"{lista_final}\n\n"
        f"Por favor, contacten con un CEO para pagar. ¡Eviten estarles molestando!"
    )
    
    await interaction.followup.send(mensaje_alerta)

# --- COMANDO: CORREGIR PAGO ---
@bot.tree.command(name="corregir-pago", description="Resta meses por error")
async def corregir_pago(interaction: discord.Interaction, id_id: int, meses_a_quitar: int):
    if not es_ceo(interaction): return
    
    conn = sqlite3.connect('eve_pos.db')
    cursor = conn.cursor()
    cursor.execute('SELECT pagado_hasta_mes, anio_vencimiento FROM outposts WHERE id_num = ?', (id_id,))
    res = cursor.fetchone()
    
    if not res:
        conn.close()
        return await interaction.response.send_message(f"❌ No se encontró la POS #{id_id}.", ephemeral=True)
    
    mes_act, anio_act = res
    total_meses_actual = (anio_act * 12 + mes_act)
    total_meses_final = total_meses_actual - meses_a_quitar
    
    if total_meses_final < (datetime.now().year * 12):
        conn.close()
        return await interaction.response.send_message("❌ Error: La POS quedaría con fecha anterior al año actual.", ephemeral=True)

    nuevo_anio = total_meses_final // 12
    nuevo_mes = total_meses_final % 12
    if nuevo_mes == 0:
        nuevo_mes = 12
        nuevo_anio -= 1

    cursor.execute('UPDATE outposts SET pagado_hasta_mes = ?, anio_vencimiento = ? WHERE id_num = ?', 
                   (nuevo_mes, nuevo_anio, id_id))
    conn.commit()
    conn.close()
    
    meses_nombres = ["❌ Pendiente", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
    await interaction.response.send_message(f"⚠️ Corrección aplicada a #{id_id}. Nuevo vencimiento: **{meses_nombres[nuevo_mes]} {nuevo_anio}**")

# --- BORRAR POS ---
@bot.tree.command(name="borrar-pos", description="Borra una POS")
async def borrar_pos(interaction: discord.Interaction, id_id: int):
    if not es_ceo(interaction): return
    conn = sqlite3.connect('eve_pos.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM outposts WHERE id_num = ?', (id_id,))
    conn.commit()
    conn.close()
    await interaction.response.send_message(f"🗑️ POS #{id_id} eliminada.")

bot.run(TOKEN)