# database.py
# Contiene todas las funciones para interactuar con la base de datos SQLite.

import json  # Necesario para save_generated_article
import os
import sqlite3
from datetime import datetime

# Define la ruta a tu archivo de esquema SQL
# ASEGÚRATE DE QUE ESTA RUTA ES CORRECTA PARA TU SISTEMA
SCHEMA_FILE_PATH = "C:\\Users\\oscar\\Desktop\\proyectospy\\auto-seo\\schema.sql"
DB_FILE_PATH = "seo_autopilot.db" # Nombre del archivo de la base de datos


def inicializar_db():
    """
    Inicializa la conexión con la base de datos y crea las tablas
    ejecutando el script SQL desde SCHEMA_FILE_PATH si no existen.
    Incluye depuración para la lectura del archivo SQL.
    """
    print(f"--- Intentando inicializar DB: {DB_FILE_PATH} ---")
    conn = sqlite3.connect(DB_FILE_PATH)
    cursor = conn.cursor()
    sql_script = "" # Inicializar script como vacío
    try:
        # Verificar si el archivo de esquema existe
        print(f"Verificando si el archivo de esquema existe en: {SCHEMA_FILE_PATH}")
        if not os.path.exists(SCHEMA_FILE_PATH):
             print(f"❌ Error: El archivo de esquema SQL NO FUE ENCONTRADO en {SCHEMA_FILE_PATH}")
             # No lanzar excepción aquí todavía, lo haremos después de intentar leer por si acaso
             sql_script = "" # Asegurar que script está vacío

        else:
            # Leer el contenido del archivo SQL
            print(f"Archivo de esquema encontrado. Leyendo contenido desde: {SCHEMA_FILE_PATH}")
            with open(SCHEMA_FILE_PATH, 'r', encoding='utf-8') as f:
                sql_script = f.read()
            print(f"Leído contenido del archivo. Longitud del script: {len(sql_script)} caracteres.")

            if len(sql_script) == 0 or not sql_script.strip():
                 print("⚠️ Advertencia: El contenido del script SQL parece estar vacío o solo contiene espacios en blanco.")
                 # Si el script está vacío, no hay nada que ejecutar.

        # Ejecutar el script SQL solo si tiene contenido
        if sql_script and sql_script.strip():
            print("Ejecutando script SQL para crear tablas...")
            cursor.executescript(sql_script)
            conn.commit()
            print("✅ Script SQL ejecutado y commit realizado.")
        else:
             print("⏩ Saltando ejecución del script SQL porque estaba vacío o no se encontró el archivo.")
             # Si no hay script, no hay nada que hacer, pero no es un error de ejecución SQL.


        print(f"✅ Base de datos {DB_FILE_PATH} inicializada/verificada usando {SCHEMA_FILE_PATH}.")

        # === VERIFICACIÓN ADICIONAL ===
        # Intentar seleccionar de una tabla clave para ver si existe
        try:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='articulos';")
            if cursor.fetchone():
                print("✅ Tabla 'articulos' verificada. EXISTE.")
            else:
                print("⚠️ La tabla 'articulos' NO FUE CREADA o no se encontró después de ejecutar el script. Revisa tu schema.sql y la salida de depuración anterior.")
                # Puedes añadir verificaciones para otras tablas clave si lo deseas
        except Exception as e:
             print(f"⚠️ Error al verificar tablas después de la inicialización: {str(e)}")
        # === FIN VERIFICACIÓN ADICIONAL ===


    except FileNotFoundError:
        print(f"❌ Error crítico: El archivo de esquema SQL no se encontró.")
        raise # Relanzamos
    except Exception as e:
        print(f"❌ Error al ejecutar script SQL de inicialización de DB: {str(e)}")
        conn.rollback()
        raise # Relanzar la excepción
    finally:
        conn.close()
        print("--- Fin inicialización DB ---")


# === FUNCIONES ORIGINALES (RESTAURADAS Y MODIFICADAS) ===

def url_existe(url):
    """Verifica si una URL ya existe en la base de datos (tabla articulos)."""
    conn = sqlite3.connect(DB_FILE_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT 1 FROM articulos WHERE url = ?', (url,))
        return cursor.fetchone() is not None
    except sqlite3.OperationalError as e:
        print(f"⚠️ Error SQL en url_existe: {str(e)}. ¿Existe la tabla 'articulos'?")
        return False # Si la tabla no existe, la URL obviamente no existe en ella
    except Exception as e:
        print(f"Error en url_existe: {str(e)}")
        return False
    finally:
        conn.close()

def obtener_urls_existentes():
    """Obtiene todas las URLs ya almacenadas en la base de datos (tabla articulos)."""
    conn = sqlite3.connect(DB_FILE_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT url FROM articulos')
        # --- AQUI ES DONDE SE CAUSABA EL ERROR 'no such table: articulos' SI LA TABLA NO SE CREÓ ---
        return {row[0] for row in cursor.fetchall()}
    except sqlite3.OperationalError as e:
        print(f"⚠️ Error SQL en obtener_urls_existentes: {str(e)}. ¿Existe la tabla 'articulos'?")
        return set() # Si la tabla no existe, retorna un conjunto vacío
    except Exception as e:
        print(f"Error en obtener_urls_existentes: {str(e)}")
        return set()
    finally:
        conn.close()

# === Nueva función: obtener ID de fuente por URL ===
def get_source_id_by_url(url):
    """Obtiene el ID de un artículo fuente por su URL."""
    conn = sqlite3.connect(DB_FILE_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT id FROM articulos WHERE url = ?', (url,))
        row = cursor.fetchone()
        return row[0] if row else None # Retorna ID o None si no existe
    except sqlite3.OperationalError as e:
        print(f"⚠️ Error SQL en get_source_id_by_url: {str(e)}. ¿Existe la tabla 'articulos'?")
        return None
    except Exception as e:
        print(f"Error en get_source_id_by_url: {str(e)}")
        return None
    finally:
        conn.close()


# === Modificar guardar_articulo para retornar el ID ===
def guardar_articulo(articulo):
    """
    Guarda un artículo fuente en la tabla 'articulos' y sus tags.
    Retorna el ID del artículo fuente guardado o existente.
    """
    conn = sqlite3.connect(DB_FILE_PATH)
    cursor = conn.cursor()
    try:
        # Intentar insertar. Si ya existe (IGNORE), no hará nada.
        cursor.execute('''
            INSERT OR IGNORE INTO articulos
            (titulo, url, score, resumen, fuente, fecha_publicacion_fuente, fecha_scraping, usada_para_generar)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?)
        ''', (
            articulo.get('titulo', ''),
            articulo['url'], # Puede fallar si 'url' no está en dict
            articulo['score'], # Puede fallar si 'score' no está en dict
            articulo.get('resumen', ''),
            articulo.get('fuente', ''),
            articulo.get('fecha_publicacion_fuente', datetime.now().strftime('%Y-%m-%d')), # Usar fecha del dict si existe, sino actual
            articulo.get('usada_para_generar', 0) # Asegurar que se guarda, por defecto 0
        ))

        # Obtener ID del artículo (recién insertado o pre-existente)
        # Si la inserción fue exitosa, lastrowid es el ID.
        # Si fue ignorada, necesitamos consultar por URL.
        articulo_id = cursor.lastrowid

        if not articulo_id: # Si lastrowid es 0 (usó IGNORE)
             # Consultar la base de datos para obtener el ID del artículo existente
             cursor.execute('SELECT id FROM articulos WHERE url = ?', (articulo['url'],))
             articulo_id_row = cursor.fetchone()
             if articulo_id_row:
                  articulo_id = articulo_id_row[0]
             else:
                  # Esto no debería pasar si url_existe() se usó antes o si IGNORE funcionó
                  print(f"⚠️ Falló al obtener ID para URL {articulo['url']} después de INSERT OR IGNORE.")
                  conn.rollback()
                  return None # Retornar None si no se puede obtener el ID


        # Insertar tags y relaciones
        # Asume que la tabla de relación de tags se llama 'articulos_fuente_tags'
        tag_table_name = 'articulos_fuente_tags' # O 'articulos_tags' si no cambiaste el nombre en SQL
        try:
            for tag in articulo.get('tags', []):
                tag = tag.strip()
                if not tag: continue

                cursor.execute('INSERT OR IGNORE INTO tags (tag) VALUES (?)', (tag,))
                cursor.execute('SELECT id FROM tags WHERE tag = ?', (tag,))
                tag_id_row = cursor.fetchone()
                if tag_id_row:
                    tag_id = tag_id_row[0]
                    # Usamos el ID de artículo obtenido anteriormente
                    cursor.execute(
                        f'INSERT OR IGNORE INTO {tag_table_name} (articulo_fuente_id, tag_id) VALUES (?, ?)',
                        (articulo_id, tag_id)
                    )
                else:
                     print(f"⚠️ No se pudo encontrar ID para el tag '{tag}' después de la inserción en guardar_articulo.")

        except sqlite3.OperationalError as e:
            print(f"⚠️ Error SQL al insertar tags/relaciones en {tag_table_name}: {str(e)}. ¿Existe la tabla '{tag_table_name}'?")
            # No relanzar, solo rollback de esta parte
            conn.rollback() # Rollback de tags/relaciones si fallan
            pass # No lanzar excepción si falla solo la parte de tags
        except Exception as e:
             print(f"Error en la sección de tags/relaciones para artículo ID {articulo_id}: {str(e)}")
             pass


        conn.commit() # Commit final si todo lo anterior fue bien
        # print(f"✅ Artículo fuente '{articulo.get('titulo', articulo.get('url', 'N/A'))[:50] + '...'}' guardado con ID {articulo_id}.")
        return articulo_id # <<-- Retornar el ID


    except Exception as e:
        print(f"Error general al guardar artículo fuente {articulo.get('url', 'N/A')}: {str(e)}")
        conn.rollback()
        raise # Relanzar la excepción
    finally:
        conn.close()


# === Función para obtener artículos fuente relevantes ===
# Esta función interactúa con la tabla `articulos` (fuentes).
# Asume la existencia del campo 'usada_para_generar' y la columna de fecha (ej. fecha_publicacion_fuente).
def get_relevant_articles(topic=None, min_score=7, limit=3):
    """
    Obtiene URLs y datos de artículos fuente NO USADOS con score >= min_score, ordenados por score y fecha.
    """
    conn = sqlite3.connect(DB_FILE_PATH)
    cursor = conn.cursor()
    try:
        # Usar el nombre de columna de fecha que tengas en tu schema.sql
        # Si lo renombraste a fecha_publicacion_fuente, úsalo. Si lo dejaste como fecha_publicacion, úsalo.
        fecha_col = 'fecha_publicacion_fuente' # <<-- Cambia esto si tu columna de fecha fuente se llama diferente
        cursor.execute(f'''
            SELECT id, url, titulo, score, resumen, fuente, usada_para_generar
            FROM articulos
            WHERE score >= ? AND usada_para_generar = 0 -- Añadido: solo fuentes NO usadas aún
            ORDER BY score DESC, {fecha_col} DESC
            LIMIT ?
        ''', (min_score, limit))

        rows = cursor.fetchall()
        col_names = [description[0] for description in cursor.description]
        results = []
        for row in rows:
            results.append(dict(zip(col_names, row)))

        print(f"📚 Encontrados {len(results)} artículos fuente NO usados (score >= {min_score}).")
        return results

    except sqlite3.OperationalError as e:
        print(f"⚠️ Error SQL en get_relevant_articles: {str(e)}. ¿Existe la tabla 'articulos' y la columna '{fecha_col}' y 'usada_para_generar'?")
        return []
    except Exception as e:
        print(f"Error en get_relevant_articles: {str(e)}")
        return []
    finally:
        conn.close()

# === Nueva función para marcar fuente como usada ===
def mark_source_used(source_article_id):
    """Marca un artículo fuente como usado para generar contenido."""
    conn = sqlite3.connect(DB_FILE_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute('''
            UPDATE articulos
            SET usada_para_generar = 1
            WHERE id = ?
        ''', (source_article_id,))
        conn.commit()
        # print(f"✅ Fuente ID {source_article_id} marcada como usada.")
    except sqlite3.OperationalError as e:
        print(f"⚠️ Error SQL en mark_source_used: {str(e)}. ¿Existe la tabla 'articulos' y la columna 'usada_para_generar'?")
        conn.rollback()
    except Exception as e:
        print(f"Error en mark_source_used ID {source_article_id}: {str(e)}")
        conn.rollback()
    finally:
        conn.close()


# === Nuevas funciones para manejar artículos generados e imágenes ===
# Estas funciones asumen la existencia de las tablas 'articulos_generados' e 'imagenes_generadas'.

def save_generated_article(article_data):
    """Guarda un artículo generado en la tabla articulos_generados."""
    conn = sqlite3.connect(DB_FILE_PATH)
    cursor = conn.cursor()
    try:
        # Convertir lista de tags a string (ej: JSON) para guardar
        # Asegúrate de que 'tags' en article_data es una lista o usa get con []
        tags_list = article_data.get('tags', [])
        if not isinstance(tags_list, list):
             print(f"⚠️ save_generated_article recibió 'tags' que no es lista: {type(tags_list)}. Guardando como cadena vacía.")
             tags_list = []
        tags_str = json.dumps(tags_list)


        cursor.execute('''
            INSERT INTO articulos_generados
            (tema, titulo, meta_description, body, tags, fecha_publicacion_destino, estado, score_fuentes_promedio, fecha_generacion)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP) -- Asegurar fecha_generacion se inserta
        ''', (
            article_data.get('tema', 'Desconocido'),
            article_data.get('title', 'Sin título'),
            article_data.get('meta_description', ''),
            article_data.get('body', ''),
            tags_str, # Guardamos los tags como string JSON
            article_data.get('fecha_publicacion_destino'), # Puede ser None inicialmente
            article_data.get('estado', 'generado'), # Estado por defecto 'generado'
            article_data.get('score_fuentes_promedio') # Puede ser None
        ))
        article_id = cursor.lastrowid
        conn.commit()
        print(f"✅ Artículo generado '{article_data.get('title', 'N/A')[:50] + '...'}' guardado con ID {article_id}.")
        return article_id # Retornar el ID del artículo generado guardado

    except sqlite3.OperationalError as e:
         print(f"⚠️ Error SQL en save_generated_article: {str(e)}. ¿Existe la tabla 'articulos_generados' y sus columnas?")
         conn.rollback()
         raise
    except Exception as e:
        print(f"Error al guardar artículo generado '{article_data.get('title', 'N/A')}': {str(e)}")
        conn.rollback()
        raise
    finally:
        conn.close()

def save_image_metadata(image_data):
    """Guarda la metadata de una imagen asociada a un artículo generado."""
    conn = sqlite3.connect(DB_FILE_PATH)
    cursor = conn.cursor()
    try:
        # Asegurarse de que 'articulo_generado_id' está presente y es un número
        if not isinstance(image_data.get('articulo_generado_id'), int):
             print(f"⚠️ save_image_metadata: ID de artículo generado inválido o faltante: {image_data.get('articulo_generado_id')}. No se guardará la imagen.")
             return # No guardar si no hay ID válido

        cursor.execute('''
            INSERT INTO imagenes_generadas
            (articulo_generado_id, url, alt_text, caption, licencia, autor)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            image_data['articulo_generado_id'], # Usar [] ya que validamos que existe y es int
            image_data.get('url', ''),
            image_data.get('alt_text', ''),
            image_data.get('caption', ''),
            image_data.get('licencia', 'Desconocida'),
            image_data.get('autor', 'Desconocido')
        ))
        conn.commit()
        # print(f"✅ Metadata de imagen guardada para articulo generado ID {image_data.get('articulo_generado_id')}")
    except sqlite3.OperationalError as e:
         print(f"⚠️ Error SQL en save_image_metadata: {str(e)}. ¿Existe la tabla 'imagenes_generadas' y sus columnas?")
         conn.rollback()
         # No relanzar, una imagen fallida no debería detener todo
    except Exception as e:
        print(f"Error al guardar metadata de imagen para articulo generado ID {image_data.get('articulo_generado_id', 'N/A')}: {str(e)}")
        conn.rollback()
        # No relanzar
    finally:
        conn.close()


# Bloque __main__ para probar solo database.py (opcional, pero útil para verificar la inicialización)
if __name__ == "__main__":
    print("--- Probando inicializar_db ---")
    try:
        # Borra seo_autopilot.db antes de ejecutar esto para probar la creación
        if os.path.exists(DB_FILE_PATH):
            print(f"Borrando '{DB_FILE_PATH}' para prueba...")
            os.remove(DB_FILE_PATH)
            print("Borrado.")
        else:
            print(f"'{DB_FILE_PATH}' no existe, se creará.")


        inicializar_db()
        print("--- Prueba de inicializar_db completada ---")
    except Exception as e:
        print(f"La prueba de inicializar_db falló: {str(e)}")
    # Después de ejecutar 'python database.py', abre seo_autopilot.db con tu visor SQL
    # y verifica si las tablas se crearon (especialmente 'articulos').