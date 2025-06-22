# database.py (Corregido: get_config no define ni retorna prompts por defecto como strings)

import json
import os
import sqlite3
from datetime import datetime

# Define la ruta a tu archivo de esquema SQL
SCHEMA_FILE_PATH = "C:\\Users\\oscar\\Desktop\\proyectospy\\auto-seo\\schema.sql" # <-- VERIFICA ESTA RUTA
DB_FILE_PATH = "seo_autopilot.db"


def inicializar_db():
    """
    Inicializa la conexión con la base de datos y crea las tablas.
    """
    print(f"--- Intentando inicializar DB: {DB_FILE_PATH} ---")
    conn = sqlite3.connect(DB_FILE_PATH)
    cursor = conn.cursor()
    sql_script = ""
    try:
        print(f"Verificando si el archivo de esquema existe en: {SCHEMA_FILE_PATH}")
        if not os.path.exists(SCHEMA_FILE_PATH):
             print(f"❌ Error: El archivo de esquema SQL NO FUE ENCONTRADO en {SCHEMA_FILE_PATH}")
        else:
            print(f"Archivo de esquema encontrado. Leyendo contenido desde: {SCHEMA_FILE_PATH}")
            with open(SCHEMA_FILE_PATH, 'r', encoding='utf-8') as f:
                sql_script = f.read()
            print(f"Leído contenido del archivo. Longitud del script: {len(sql_script)} caracteres.")

        if sql_script and sql_script.strip():
            print("Ejecutando script SQL para crear tablas...")
            cursor.executescript(sql_script)
            conn.commit()
            print("✅ Script SQL ejecutado y commit realizado.")
        else:
             print("⏩ Saltando ejecución del script SQL porque estaba vacío o no se encontró el archivo.")

        print(f"✅ Base de datos {DB_FILE_PATH} inicializada/verificada usando {SCHEMA_FILE_PATH}.")

        try:
            # Verificaciones básicas de tablas clave
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='articulos';")
            if cursor.fetchone():
                print("✅ Tabla 'articulos' verificada. EXISTE.")
            else:
                print("⚠️ La tabla 'articulos' NO FUE CREADA.")

            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='configuracion';")
            if cursor.fetchone():
                 print("✅ Tabla 'configuracion' verificada. EXISTE.")
            else:
                 print("⚠️ La tabla 'configuracion' NO FUE CREADA.")

        except Exception as e:
             print(f"⚠️ Error al verificar tablas después de la inicialización: {str(e)}")

    except FileNotFoundError:
        print(f"❌ Error crítico: El archivo de esquema SQL no se encontró.")
        raise
    except Exception as e:
        print(f"❌ Error al ejecutar script SQL de inicialización de DB: {str(e)}")
        conn.rollback()
        raise
    finally:
        conn.close()
        print("--- Fin inicialización DB ---")


# --- Funciones existentes (sin cambios en su lógica, solo las incluyo por completitud) ---

def url_existe(url):
    """Verifica si una URL ya existe en la base de datos (tabla articulos)."""
    conn = sqlite3.connect(DB_FILE_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT 1 FROM articulos WHERE url = ?', (url,))
        return cursor.fetchone() is not None
    except sqlite3.OperationalError as e:
        print(f"⚠️ Error SQL en url_existe: {str(e)}. ¿Existe la tabla 'articulos'?")
        return False
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
        return {row[0] for row in cursor.fetchall()}
    except sqlite3.OperationalError as e:
        print(f"⚠️ Error SQL en obtener_urls_existentes: {str(e)}. ¿Existe la tabla 'articulos'?")
        return set()
    except Exception as e:
        print(f"Error en obtener_urls_existentes: {str(e)}")
        return set()
    finally:
        conn.close()

def get_source_id_by_url(url):
    """Obtiene el ID de un artículo fuente por su URL."""
    conn = sqlite3.connect(DB_FILE_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT id FROM articulos WHERE url = ?', (url,))
        row = cursor.fetchone()
        return row[0] if row else None
    except sqlite3.OperationalError as e:
        print(f"⚠️ Error SQL en get_source_id_by_url: {str(e)}. ¿Existe la tabla 'articulos'?")
        return None
    except Exception as e:
        print(f"Error en get_source_id_by_url: {str(e)}")
        return None
    finally:
        conn.close()

def guardar_articulo(articulo):
    """Guarda un artículo fuente en la tabla 'articulos' y sus tags."""
    conn = sqlite3.connect(DB_FILE_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT OR IGNORE INTO articulos
            (titulo, url, score, resumen, fuente, fecha_publicacion_fuente, fecha_scraping, usada_para_generar)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?)
        ''', (
            articulo.get('titulo', ''),
            articulo['url'],
            articulo['score'],
            articulo.get('resumen', ''),
            articulo.get('fuente', ''),
            articulo.get('fecha_publicacion_fuente', datetime.now().strftime('%Y-%m-%d')),
            articulo.get('usada_para_generar', 0)
        ))
        articulo_id = cursor.lastrowid
        # ... (lógica para obtener ID si usó IGNORE y guardar tags) ...
        if not articulo_id:
             cursor.execute('SELECT id FROM articulos WHERE url = ?', (articulo['url'],))
             articulo_id_row = cursor.fetchone()
             if articulo_id_row:
                  articulo_id = articulo_id_row[0]
             else:
                  print(f"⚠️ Falló al obtener ID para URL {articulo['url']} después de INSERT OR IGNORE.")
                  conn.rollback()
                  return None

        tag_table_name = 'articulos_fuente_tags'
        try:
            for tag in articulo.get('tags', []):
                tag = tag.strip()
                if not tag: continue
                cursor.execute('INSERT OR IGNORE INTO tags (tag) VALUES (?)', (tag,))
                cursor.execute('SELECT id FROM tags WHERE tag = ?', (tag,))
                tag_id_row = cursor.fetchone()
                if tag_id_row:
                    tag_id = tag_id_row[0]
                    cursor.execute(f'INSERT OR IGNORE INTO {tag_table_name} (articulo_fuente_id, tag_id) VALUES (?, ?)', (articulo_id, tag_id))
        except Exception as e:
             print(f"Error en la sección de tags/relaciones para artículo ID {articulo_id}: {str(e)}")
             pass # No relanzar, solo imprimir advertencia


        conn.commit()
        return articulo_id

    except Exception as e:
        print(f"Error general al guardar artículo fuente {articulo.get('url', 'N/A')}: {str(e)}")
        conn.rollback()
        raise
    finally:
        conn.close()


def get_relevant_articles(topic=None, min_score=7, limit=3):
    """Obtiene URLs y datos de artículos fuente NO USADOS con score >= min_score."""
    conn = sqlite3.connect(DB_FILE_PATH)
    cursor = conn.cursor()
    try:
        fecha_col = 'fecha_publicacion_fuente'
        cursor.execute(f'''
            SELECT id, url, titulo, score, resumen, fuente, usada_para_generar
            FROM articulos
            WHERE score >= ? AND usada_para_generar = 0
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
    except sqlite3.OperationalError as e:
        print(f"⚠️ Error SQL en mark_source_used: {str(e)}. ¿Existe la tabla 'articulos' y la columna 'usada_para_generar'?")
        conn.rollback()
    except Exception as e:
        print(f"Error en mark_source_used ID {source_article_id}: {str(e)}")
        conn.rollback()
    finally:
        conn.close()

def save_generated_article(article_data):
    """Guarda un artículo generado en la tabla articulos_generados."""
    conn = sqlite3.connect(DB_FILE_PATH)
    cursor = conn.cursor()
    try:
        tags_list = article_data.get('tags', [])
        if not isinstance(tags_list, list):
             print(f"⚠️ save_generated_article recibió 'tags' que no es lista: {type(tags_list)}. Guardando como cadena vacía.")
             tags_list = []
        tags_str = json.dumps(tags_list)

        # Asegurar que 'tema' existe en article_data
        tema = article_data.get('tema', 'Desconocido')
        if not tema: # Asegurar que el tema no está vacío
             print("⚠️ save_generated_article: El campo 'tema' está vacío. Usando 'Desconocido'.")
             tema = 'Desconocido'


        cursor.execute('''
            INSERT INTO articulos_generados
            (tema, titulo, meta_description, body, tags, fecha_publicacion_destino, estado, score_fuentes_promedio, fecha_generacion)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (
            tema,
            article_data.get('title', 'Sin título'),
            article_data.get('meta_description', ''),
            article_data.get('body', ''),
            tags_str,
            article_data.get('fecha_publicacion_destino'),
            article_data.get('estado', 'generado'),
            article_data.get('score_fuentes_promedio')
        ))
        article_id = cursor.lastrowid
        conn.commit()
        print(f"✅ Artículo generado '{article_data.get('title', 'N/A')[:50] + '...'}' guardado con ID {article_id}.")
        return article_id

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
        if not isinstance(image_data.get('articulo_generado_id'), int):
             print(f"⚠️ save_image_metadata: ID de artículo generado inválido o faltante: {image_data.get('articulo_generado_id')}. No se guardará la imagen.")
             return

        cursor.execute('''
            INSERT INTO imagenes_generadas
            (articulo_generado_id, url, alt_text, caption, licencia, autor)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            image_data['articulo_generado_id'],
            image_data.get('url', ''),
            image_data.get('alt_text', ''),
            image_data.get('caption', ''),
            image_data.get('licencia', 'Desconocida'),
            image_data.get('autor', 'Desconocido')
        ))
        conn.commit()
    except sqlite3.OperationalError as e:
         print(f"⚠️ Error SQL en save_image_metadata: {str(e)}. ¿Existe la tabla 'imagenes_generadas' y sus columnas?")
         conn.rollback()
    except Exception as e:
        print(f"Error al guardar metadata de imagen para articulo generado ID {image_data.get('articulo_generado_id', 'N/A')}: {str(e)}")
        conn.rollback()
    finally:
        conn.close()

# === Funciones para la tabla configuracion (CORREGIDAS) ===

# get_config ahora solo lee de la DB. Si no encuentra, retorna {}
def get_config(tema):
    """
    Obtiene la configuración guardada para un tema.
    Retorna un diccionario con la configuración si existe, o un diccionario vacío {} si no.
    Maneja errores de DB retornando también {}.
    """
    conn = sqlite3.connect(DB_FILE_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT * FROM configuracion WHERE tema = ?', (tema,))
        row = cursor.fetchone()

        if row:
            col_names = [description[0] for description in cursor.description]
            config = dict(zip(col_names, row))
            print(f"✅ Configuración encontrada para tema '{tema}'.")
            return config
        else:
            print(f"⚠️ No se encontró configuración guardada para tema '{tema}'.")
            return {} # Retornar diccionario vacío si no se encuentra

    except sqlite3.OperationalError as e:
        print(f"⚠️ Error SQL en get_config: {str(e)}. ¿Existe la tabla 'configuracion'?")
        # Retornar dict vacío en caso de error de DB (ej: tabla no existe)
        return {}

    except Exception as e:
        print(f"❌ Error en get_config para tema '{tema}': {str(e)}")
        return {}
    finally:
        conn.close()

def save_config(config_dict):
    """
    Guarda o actualiza la configuración para un tema.
    config_dict debe ser un diccionario con campos válidos para la tabla 'configuracion' e incluir 'tema'.
    """
    if 'tema' not in config_dict or not config_dict['tema']:
        print("❌ Error: config_dict debe incluir un 'tema' para guardar la configuración.")
        return False

    conn = sqlite3.connect(DB_FILE_PATH)
    cursor = conn.cursor()
    try:
        # Definir los campos válidos para la tabla configuracion
        valid_fields = [
            'tema', 'min_score_fuente', 'num_fuentes_scraper', 'num_resultados_scraper',
            'min_score_generador', 'num_fuentes_generador', 'longitud_texto', 'tono_texto',
            'num_imagenes_buscar', 'prompt_analyzer_template', 'prompt_generator_template',
            'prompt_copilot_template'
            # Asegúrate de que esta lista coincide con tu schema.sql
        ]

        # Filtrar config_dict para incluir solo campos válidos
        filtered_config_dict = {k: v for k, v in config_dict.items() if k in valid_fields}

        if 'tema' not in filtered_config_dict:
             print("❌ Error: El campo 'tema' es necesario y no está en los datos válidos.")
             return False

        tema = filtered_config_dict['tema'] # Obtener el tema para la query

        fields = list(filtered_config_dict.keys())
        values = list(filtered_config_dict.values())

        # Crear placeholders y nombres de campos para la query
        placeholders = ', '.join(['?'] * len(fields))
        field_names = ', '.join(fields)

        # Usamos INSERT OR REPLACE INTO
        query = f'''
            INSERT OR REPLACE INTO configuracion ({field_names})
            VALUES ({placeholders})
        '''
        cursor.execute(query, values)

        conn.commit()
        print(f"✅ Configuración guardada para tema '{tema}'.")
        return True

    except sqlite3.OperationalError as e:
         print(f"⚠️ Error SQL en save_config: {str(e)}")
         conn.rollback()
         return False
    except Exception as e:
        print(f"❌ Error al guardar configuración para tema '{tema}': {str(e)}")
        conn.rollback()
        return False
    finally:
        conn.close()


# Funciones para obtener datos de artículos generados para la UI/Admin
# Añadido filtro por tema/seccion
def get_all_generated_articles(tema=None, estado=None, limit=100):
    """Obtiene todos los artículos generados, opcionalmente filtrados por tema/seccion o estado."""
    conn = sqlite3.connect(DB_FILE_PATH)
    cursor = conn.cursor()
    try:
        query = 'SELECT id, tema, titulo, fecha_generacion, estado, score_fuentes_promedio FROM articulos_generados WHERE 1=1'
        params = []

        if tema: # Filtrar por tema (seccion)
            query += ' AND tema = ?'
            params.append(tema)
        if estado:
            query += ' AND estado = ?'
            params.append(estado)

        query += ' ORDER BY fecha_generacion DESC LIMIT ?'
        params.append(limit)


        cursor.execute(query, params)
        rows = cursor.fetchall()
        col_names = [description[0] for description in cursor.description]
        results = []
        for row in rows:
            results.append(dict(zip(col_names, row)))

        print(f"📚 Encontrados {len(results)} artículos generados (Filtros: Tema/Seccion={tema}, Estado={estado}).")
        return results

    except sqlite3.OperationalError as e:
        print(f"⚠️ Error SQL en get_all_generated_articles: {str(e)}. ¿Existe la tabla 'articulos_generados'?")
        return []
    except Exception as e:
        print(f"Error en get_all_generated_articles: {str(e)}")
        return []
    finally:
        conn.close()


def get_generated_article_by_id(article_id):
    """Obtiene un artículo generado por su ID, incluyendo metadata de imágenes asociadas."""
    conn = sqlite3.connect(DB_FILE_PATH)
    cursor = conn.cursor()
    try:
        # Obtener datos del artículo principal
        cursor.execute('SELECT * FROM articulos_generados WHERE id = ?', (article_id,))
        article_row = cursor.fetchone()

        if not article_row:
            print(f"⚠️ Artículo generado con ID {article_id} no encontrado.")
            return None

        article_col_names = [description[0] for description in cursor.description]
        article_data = dict(zip(article_col_names, article_row))

        # Convertir tags de string JSON a lista
        if 'tags' in article_data and article_data['tags']:
             try:
                  article_data['tags'] = json.loads(article_data['tags'])
             except json.JSONDecodeError:
                  print(f"⚠️ Error al parsear tags JSON para artículo ID {article_id}. Tags raw: {article_data['tags']}")
                  article_data['tags'] = [] # Default a lista vacía si falla el parseo


        # Obtener metadata de imágenes asociadas
        cursor.execute('SELECT url, alt_text, caption, licencia, autor FROM imagenes_generadas WHERE articulo_generado_id = ?', (article_id,))
        image_rows = cursor.fetchall()
        image_col_names = [description[0] for description in cursor.description]
        images_data = []
        for row in image_rows:
            images_data.append(dict(zip(image_col_names, row)))

        article_data['imagenes'] = images_data # Añadir la lista de imágenes al diccionario del artículo

        print(f"✅ Artículo generado ID {article_id} y {len(images_data)} imágenes asociadas cargados.")
        return article_data

    except sqlite3.OperationalError as e:
        print(f"⚠️ Error SQL en get_generated_article_by_id: {str(e)}. ¿Existen las tablas 'articulos_generados' e 'imagenes_generadas'?")
        return None
    except Exception as e:
        print(f"❌ Error en get_generated_article_by_id para ID {article_id}: {str(e)}")
        return None
    finally:
        conn.close()

def update_generated_article(article_id, updated_data):
    """Actualiza campos de un artículo generado por su ID."""
    conn = sqlite3.connect(DB_FILE_PATH)
    cursor = conn.cursor()
    try:
        set_clauses = []
        params = []
        allowed_fields = ['titulo', 'meta_description', 'body', 'tags', 'estado'] # Campos permitidos a actualizar

        filtered_updated_data = {}
        if 'tags' in updated_data and isinstance(updated_data['tags'], list):
             filtered_updated_data['tags'] = json.dumps(updated_data['tags']) # Convertir tags a JSON string
        for field in updated_data:
             if field in allowed_fields and field != 'tags':
                  filtered_updated_data[field] = updated_data[field]

        if not filtered_updated_data:
            print(f"⚠️ No hay campos válidos en updated_data para actualizar artículo ID {article_id}.")
            return False

        for field, value in filtered_updated_data.items():
            set_clauses.append(f"{field} = ?")
            params.append(value)

        # Si tienes columna fecha_actualizacion en articulos_generados, actualízala
        # set_clauses.append("fecha_actualizacion = CURRENT_TIMESTAMP") # Asumiendo que existe

        params.append(article_id)

        query = f"UPDATE articulos_generados SET {', '.join(set_clauses)} WHERE id = ?"

        cursor.execute(query, params)

        if cursor.rowcount == 0:
             print(f"⚠️ Artículo generado con ID {article_id} no encontrado para actualizar.")
             conn.rollback()
             return False

        conn.commit()
        print(f"✅ Artículo generado ID {article_id} actualizado.")
        return True

    except sqlite3.OperationalError as e:
        print(f"⚠️ Error SQL en update_generated_article: {str(e)}")
        conn.rollback()
        return False
    except Exception as e:
        print(f"❌ Error general al actualizar artículo generado ID {article_id}: {str(e)}")
        conn.rollback()
        return False
    finally:
        conn.close()

# Funciones para obtener fuentes para la UI/Admin
def get_all_sources(limit=100): # Simplificado, sin filtro por tema/estado por ahora
    """Obtiene todos los artículos fuente."""
    conn = sqlite3.connect(DB_FILE_PATH)
    cursor = conn.cursor()
    try:
        query = 'SELECT id, titulo, url, score, fuente, fecha_scraping, usada_para_generar FROM articulos ORDER BY fecha_scraping DESC LIMIT ?'
        params = [limit]

        cursor.execute(query, params)
        rows = cursor.fetchall()
        col_names = [description[0] for description in cursor.description]
        results = []
        for row in rows:
            results.append(dict(zip(col_names, row)))

        print(f"📚 Encontrados {len(results)} artículos fuente.")
        return results

    except sqlite3.OperationalError as e:
        print(f"⚠️ Error SQL en get_all_sources: {str(e)}. ¿Existe la tabla 'articulos'?")
        return []
    except Exception as e:
        print(f"Error en get_all_sources: {str(e)}")
        return []
    finally:
        conn.close()


# Funciones para obtener lista de TEMAS/SECCIONES disponibles
def get_available_temas_secciones():
    """Obtiene una lista de todos los temas/secciones con configuración guardada."""
    conn = sqlite3.connect(DB_FILE_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT DISTINCT tema FROM configuracion ORDER BY tema')
        rows = cursor.fetchall()
        # Retorna una lista de strings de tema
        return [row[0] for row in rows]
    except sqlite3.OperationalError as e:
        print(f"⚠️ Error SQL en get_available_temas_secciones: {str(e)}. ¿Existe la tabla 'configuracion'?")
        return []
    except Exception as e:
        print(f"❌ Error en get_available_temas_secciones: {str(e)}")
        return []
    finally:
        conn.close()

# === Funciones para la tabla generacion_tareas ===

def crear_tarea_generacion(tema: str, configuracion_id: int = None) -> int:
    """Crea una nueva tarea de generación en estado 'pendiente' y devuelve su ID."""
    conn = sqlite3.connect(DB_FILE_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO generacion_tareas (tema, configuracion_id, estado, fecha_actualizacion)
            VALUES (?, ?, 'pendiente', CURRENT_TIMESTAMP)
        ''', (tema, configuracion_id))
        tarea_id = cursor.lastrowid
        conn.commit()
        print(f"✅ Tarea de generación creada con ID {tarea_id} para tema '{tema}'.")
        return tarea_id
    except sqlite3.OperationalError as e:
        print(f"⚠️ Error SQL en crear_tarea_generacion: {str(e)}. ¿Existe la tabla 'generacion_tareas'?")
        conn.rollback()
        raise
    except Exception as e:
        print(f"❌ Error al crear tarea de generación para tema '{tema}': {str(e)}")
        conn.rollback()
        raise
    finally:
        conn.close()

def obtener_siguiente_tarea_pendiente() -> dict | None:
    """Obtiene la tarea pendiente más antigua (FIFO)."""
    conn = sqlite3.connect(DB_FILE_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute('''
            SELECT * FROM generacion_tareas
            WHERE estado = 'pendiente'
            ORDER BY fecha_solicitud ASC
            LIMIT 1
        ''')
        row = cursor.fetchone()
        if row:
            col_names = [description[0] for description in cursor.description]
            print(f"✅ Siguiente tarea pendiente encontrada: ID {row[0]}")
            return dict(zip(col_names, row))
        else:
            # print("ℹ️ No hay tareas pendientes en este momento.")
            return None
    except sqlite3.OperationalError as e:
        print(f"⚠️ Error SQL en obtener_siguiente_tarea_pendiente: {str(e)}. ¿Existe la tabla 'generacion_tareas'?")
        return None
    except Exception as e:
        print(f"❌ Error al obtener siguiente tarea pendiente: {str(e)}")
        return None
    finally:
        conn.close()

def actualizar_estado_tarea(tarea_id: int, estado: str, mensaje_error: str = None):
    """Actualiza el estado de una tarea y opcionalmente un mensaje de error."""
    conn = sqlite3.connect(DB_FILE_PATH)
    cursor = conn.cursor()
    try:
        current_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute('''
            UPDATE generacion_tareas
            SET estado = ?, mensaje_error = ?, fecha_actualizacion = ?
            WHERE id = ?
        ''', (estado, mensaje_error, current_timestamp, tarea_id))
        conn.commit()
        if cursor.rowcount == 0:
            print(f"⚠️ No se encontró la tarea con ID {tarea_id} para actualizar estado a '{estado}'.")
        else:
            print(f"✅ Estado de tarea ID {tarea_id} actualizado a '{estado}'.")
    except sqlite3.OperationalError as e:
        print(f"⚠️ Error SQL en actualizar_estado_tarea: {str(e)}.")
        conn.rollback()
    except Exception as e:
        print(f"❌ Error al actualizar estado de tarea ID {tarea_id}: {str(e)}")
        conn.rollback()
    finally:
        conn.close()

def marcar_tarea_completada(tarea_id: int, articulo_generado_id: int):
    """Marca una tarea como completada, asocia el ID del artículo y actualiza fechas."""
    conn = sqlite3.connect(DB_FILE_PATH)
    cursor = conn.cursor()
    try:
        current_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute('''
            UPDATE generacion_tareas
            SET estado = 'completado',
                articulo_generado_id = ?,
                mensaje_error = NULL,
                fecha_actualizacion = ?,
                fecha_finalizacion = ?
            WHERE id = ?
        ''', (articulo_generado_id, current_timestamp, current_timestamp, tarea_id))
        conn.commit()
        if cursor.rowcount == 0:
             print(f"⚠️ No se encontró la tarea con ID {tarea_id} para marcar como completada.")
        else:
            print(f"✅ Tarea ID {tarea_id} marcada como completada. Artículo generado ID: {articulo_generado_id}.")
    except sqlite3.OperationalError as e:
        print(f"⚠️ Error SQL en marcar_tarea_completada: {str(e)}.")
        conn.rollback()
    except Exception as e:
        print(f"❌ Error al marcar tarea ID {tarea_id} como completada: {str(e)}")
        conn.rollback()
    finally:
        conn.close()

def obtener_tareas_generacion(estado: str = None, limit: int = 50) -> list[dict]:
    """Obtiene una lista de tareas de generación, opcionalmente filtradas por estado."""
    conn = sqlite3.connect(DB_FILE_PATH)
    cursor = conn.cursor()
    try:
        query = 'SELECT id, tema, estado, fecha_solicitud, fecha_actualizacion, fecha_finalizacion, articulo_generado_id FROM generacion_tareas'
        params = []
        if estado:
            query += ' WHERE estado = ?'
            params.append(estado)
        query += ' ORDER BY fecha_solicitud DESC LIMIT ?'
        params.append(limit)

        cursor.execute(query, params)
        rows = cursor.fetchall()
        col_names = [description[0] for description in cursor.description]
        results = [dict(zip(col_names, row)) for row in rows]
        print(f"📚 Encontradas {len(results)} tareas de generación (Filtro estado: {estado}).")
        return results
    except sqlite3.OperationalError as e:
        print(f"⚠️ Error SQL en obtener_tareas_generacion: {str(e)}. ¿Existe la tabla 'generacion_tareas'?")
        return []
    except Exception as e:
        print(f"❌ Error en obtener_tareas_generacion: {str(e)}")
        return []
    finally:
        conn.close()


# Bloque __main__ para probar solo database.py
if __name__ == "__main__":
    print("--- Probando database.py (incluyendo generacion_tareas) ---")
    try:
        # Limpieza para empezar fresco en la prueba
        if os.path.exists(DB_FILE_PATH):
            print(f"Borrando '{DB_FILE_PATH}' para prueba...")
            os.remove(DB_FILE_PATH)
            print("Borrado.")

        # Asegurarse de que schema.sql existe y tiene la tabla 'configuracion'
        inicializar_db()
        print("--- Prueba de inicialización completada ---")

        # --- Prueba de get_config y save_config ---
        print("\n--- Probando get_config para tema 'DemoTestConfig' (debería retornar defaults) ---")
        config_test_default = get_config("DemoTestConfig")
        print(f"Config test (defaults): {config_test_default}")
        if config_test_default and config_test_default.get('tema') == 'DemoTestConfig' and config_test_default.get('min_score_generador') == 7:
             print("✅ get_config retornó defaults correctamente.")
        else:
             print("❌ get_config no retornó defaults como esperado.")


        print("\n--- Probando save_config y get_config de nuevo ---")
        modified_config = config_test_default.copy() # Copiar los defaults
        modified_config['min_score_generador'] = 8
        modified_config['prompt_generator_template'] = "Robot style prompt for {topic} based on {sources_text}"
        if save_config(modified_config):
            print("✅ save_config exitoso para 'DemoTestConfig'.")
            config_test_saved = get_config("DemoTestConfig")
            print(f"Config cargada después de guardar: {config_test_saved}")
            if config_test_saved.get('min_score_generador') == 8 and "Robot style" in config_test_saved.get('prompt_generator_template', ''):
                 print("✅ Configuración guardada y cargada correctamente.")
            else:
                 print("❌ Configuración guardada/cargada no coincide.")
        else:
            print("❌ save_config falló.")

        # --- Prueba de INSERT OR REPLACE para el mismo tema ---
        print("\n--- Probando save_config UPDATE para 'DemoTestConfig' ---")
        update_config = config_test_saved.copy()
        update_config['longitud_texto'] = 'larga'
        update_config['min_score_generador'] = 9 # Cambiar otro campo
        if save_config(update_config):
             print("✅ save_config (UPDATE) exitoso para 'DemoTestConfig'.")
             config_test_updated = get_config("DemoTestConfig")
             print(f"Config cargada después del UPDATE: {config_test_updated}")
             if config_test_updated.get('longitud_texto') == 'larga' and config_test_updated.get('min_score_generador') == 9:
                  print("✅ Configuración actualizada y cargada correctamente.")
             else:
                  print("❌ Configuración actualizada/cargada no coincide.")
        else:
            print("❌ save_config (UPDATE) falló.")

        # --- Prueba de get_available_temas_secciones ---
        print("\n--- Probando get_available_temas_secciones ---")
        available_temas = get_available_temas_secciones()
        print(f"Temas disponibles: {available_temas}")
        if 'DemoTestConfig' in available_temas:
             print("✅ 'DemoTestConfig' aparece en la lista de temas disponibles.")
        else:
             print("❌ 'DemoTestConfig' no aparece en la lista de temas disponibles.")

        # --- Pruebas para generacion_tareas ---
        print("\n--- Probando funciones de generacion_tareas ---")
        # Crear tarea
        tarea_id_1 = crear_tarea_generacion("TemaPruebaTareas1")
        if tarea_id_1:
            print(f"✅ Tarea 1 creada con ID: {tarea_id_1}")
        else:
            print(f"❌ Falló crear_tarea_generacion para TemaPruebaTareas1")

        tarea_id_2 = crear_tarea_generacion("TemaPruebaTareas2", configuracion_id=1) # Asumiendo que config id 1 podría existir
        if tarea_id_2:
            print(f"✅ Tarea 2 creada con ID: {tarea_id_2}")
        else:
            print(f"❌ Falló crear_tarea_generacion para TemaPruebaTareas2")

        # Obtener siguiente tarea pendiente
        print("\nObteniendo siguiente tarea pendiente...")
        tarea_pendiente = obtener_siguiente_tarea_pendiente()
        if tarea_pendiente and tarea_pendiente['id'] == tarea_id_1 and tarea_pendiente['tema'] == "TemaPruebaTareas1":
            print(f"✅ obtener_siguiente_tarea_pendiente() correcta: {tarea_pendiente}")
        elif tarea_pendiente:
            print(f"❌ obtener_siguiente_tarea_pendiente() incorrecta: {tarea_pendiente}")
        else:
            print("❌ No se encontró tarea pendiente como se esperaba.")

        # Actualizar estado a 'en_progreso'
        if tarea_pendiente:
            print(f"\nActualizando tarea ID {tarea_pendiente['id']} a 'en_progreso'...")
            actualizar_estado_tarea(tarea_pendiente['id'], "en_progreso")
            # Verificar (obteniendo todas las tareas)
            tareas = obtener_tareas_generacion()
            tarea_actualizada = next((t for t in tareas if t['id'] == tarea_pendiente['id']), None)
            if tarea_actualizada and tarea_actualizada['estado'] == 'en_progreso':
                print("✅ Estado actualizado a 'en_progreso' correctamente.")
            else:
                print(f"❌ Falló la actualización a 'en_progreso'. Tarea actual: {tarea_actualizada}")

        # Marcar tarea como completada (simulando un ID de artículo generado)
        mock_articulo_generado_id = 999
        if tarea_pendiente: # Usamos la misma tarea que estaba en progreso
            print(f"\nMarcando tarea ID {tarea_pendiente['id']} como 'completado' con artículo ID {mock_articulo_generado_id}...")
            marcar_tarea_completada(tarea_pendiente['id'], mock_articulo_generado_id)
            tareas = obtener_tareas_generacion()
            tarea_completada = next((t for t in tareas if t['id'] == tarea_pendiente['id']), None)
            if tarea_completada and tarea_completada['estado'] == 'completado' and tarea_completada['articulo_generado_id'] == mock_articulo_generado_id:
                print("✅ Tarea marcada como 'completado' correctamente.")
            else:
                print(f"❌ Falló el marcado como 'completado'. Tarea actual: {tarea_completada}")

        # Obtener siguiente tarea pendiente (debería ser tarea_id_2)
        print("\nObteniendo siguiente tarea pendiente (debería ser la Tarea 2)...")
        tarea_pendiente_2 = obtener_siguiente_tarea_pendiente()
        if tarea_pendiente_2 and tarea_pendiente_2['id'] == tarea_id_2:
            print(f"✅ obtener_siguiente_tarea_pendiente() correcta para Tarea 2: {tarea_pendiente_2}")
            # Actualizar a error
            print(f"\nActualizando tarea ID {tarea_pendiente_2['id']} a 'error'...")
            actualizar_estado_tarea(tarea_pendiente_2['id'], "error", "Simulación de error en worker.")
            tareas = obtener_tareas_generacion(estado='error')
            tarea_erronea = next((t for t in tareas if t['id'] == tarea_pendiente_2['id']), None)
            if tarea_erronea and tarea_erronea['estado'] == 'error' and tarea_erronea['mensaje_error']:
                print(f"✅ Estado actualizado a 'error' correctamente: {tarea_erronea['mensaje_error']}")
            else:
                print(f"❌ Falló la actualización a 'error'. Tarea actual: {tarea_erronea}")
        elif tarea_pendiente_2:
             print(f"❌ obtener_siguiente_tarea_pendiente() incorrecta, obtuvo: {tarea_pendiente_2}")
        else:
            print("❌ No se encontró la Tarea 2 pendiente como se esperaba.")

        # Listar todas las tareas
        print("\nListando todas las tareas de generación...")
        todas_las_tareas = obtener_tareas_generacion(limit=10) # Limitar para no imprimir demasiado
        for t in todas_las_tareas:
            print(f"  - ID: {t['id']}, Tema: {t['tema']}, Estado: {t['estado']}, ArtículoID: {t.get('articulo_generado_id')}")
        if len(todas_las_tareas) >= 2: # Deberíamos tener al menos las 2 que creamos
            print("✅ obtener_tareas_generacion() parece funcionar.")
        else:
            print("❌ obtener_tareas_generacion() no retornó suficientes tareas.")


    except Exception as e:
        print(f"La prueba de database.py falló: {str(e)}")

    print("\n--- Fin de la prueba independiente de Database ---")