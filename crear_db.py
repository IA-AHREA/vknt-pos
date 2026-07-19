import sqlite3

def reiniciar_db():
    conn = sqlite3.connect('eve_pos.db')
    cursor = conn.cursor()
    
    # Borramos tablas viejas para empezar de cero
    cursor.execute('DROP TABLE IF EXISTS pagos')
    cursor.execute('DROP TABLE IF EXISTS pos')
    cursor.execute('DROP TABLE IF EXISTS pilotos')

    # Nueva Tabla de Outposts con ID de 3 dígitos
    cursor.execute('''
        CREATE TABLE outposts (
            id_num INTEGER PRIMARY KEY, 
            discord_id TEXT NOT NULL,
            nombre_outpost TEXT NOT NULL,
            sistema TEXT NOT NULL,
            pagado_hasta_mes INTEGER DEFAULT 0, -- Mes en número (1-12)
            anio_vencimiento INTEGER DEFAULT 2026
        )
    ''')
    
    conn.commit()
    conn.close()
    print("Base de datos reiniciada con éxito.")

if __name__ == "__main__":
    reiniciar_db()