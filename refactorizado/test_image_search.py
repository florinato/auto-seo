# test_image_search.py
# Script de prueba para buscar imágenes usando web_tools.find_free_images
# y generar un HTML simple para visualizarlas.

import os
import re
import sys
import webbrowser
from datetime import datetime

# Asegúrate de que la ruta a web_tools.py sea correcta si no está en la misma carpeta
# Si web_tools.py está en la misma carpeta, esto es suficiente:
import web_tools


# Necesitamos una función simple para generar HTML, similar a mock_publisher pero más básica
def create_simple_image_html(images_metadata, query, filename=None):
    """
    Genera un archivo HTML simple para visualizar una lista de imágenes.

    Args:
        images_metadata (list): Lista de diccionarios con metadata de imágenes.
        query (str): La query que se usó para buscar las imágenes.
        filename (str, optional): Nombre del archivo HTML a generar.
                                  Si es None, se genera uno basado en la query y timestamp.
    """
    if not images_metadata:
        print("⚠️ No hay metadata de imágenes para generar el HTML.")
        # Generar un HTML simple indicando que no se encontraron imágenes
        html_content = f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>No se encontraron imágenes para "{query}"</title>
    <style>
        body {{ font-family: sans-serif; line-height: 1.6; margin: 20px; text-align: center; }}
        h1 {{ color: #333; }}
    </style>
</head>
<body>
    <h1>Resultados de Imágenes para "{query}"</h1>
    <p>No se encontraron imágenes con los parámetros actuales.</p>
</body>
</html>
"""

    else:
        # Construir el HTML para cada imagen
        images_html = ""
        for i, img_meta in enumerate(images_metadata):
            img_url = img_meta.get('url')
            img_alt = img_meta.get('alt_text', f"Imagen {i+1} sobre {query}")
            img_author = img_meta.get('author', 'Desconocido')
            img_author_url = img_meta.get('author_url')
            img_source_url = img_meta.get('source_page_url')
            sanitized_img_alt = img_alt.replace('"', "'")
            sanitized_author = img_author.replace('<', '<').replace('>', '>')
            sanitized_source = 'Unsplash' # o img_meta.get('license', 'Unsplash')

            if img_url:
                image_block = f"""
<figure style="margin: 20px auto; text-align: center; max-width: 600px; border: 1px solid #eee; padding: 10px; border-radius: 5px; box-shadow: 0 2px 5px rgba(0,0,0,0.05);">
    <img src="{img_url}" alt="{sanitized_img_alt}" style="max-width: 100%; height: auto; display: block; margin: 0 auto; border-radius: 3px;">
    <figcaption style="text-align: center; font-size: 0.9em; color: #555; margin-top: 10px; line-height: 1.4;">
"""
                caption_parts = []
                if img_author and img_author_url:
                    caption_parts.append(f'Foto por <a href="{img_author_url}" target="_blank" rel="noopener noreferrer nofollow" style="color: #555; text-decoration: none;">{sanitized_author}</a>')
                elif img_author:
                    caption_parts.append(f'Foto por {sanitized_author}')

                if img_source_url:
                    caption_parts.append(f'en <a href="{img_source_url}" target="_blank" rel="noopener noreferrer nofollow" style="color: #555; text-decoration: none;">{sanitized_source}</a>')

                if caption_parts:
                     image_block += ' | '.join(caption_parts)
                else:
                     # Mostrar el alt text o caption si no hay atribución completa y hay algo más
                     alt_or_caption = img_meta.get('caption', '').strip() or img_meta.get('alt_text', '').strip()
                     if alt_or_caption:
                          image_block += alt_or_caption.replace('<', '<').replace('>', '>')


                image_block += """
    </figcaption>
</figure>
"""
                images_html += image_block
            else:
                print(f"⚠️ Imagen {i+1} sin URL válida. Saltando.")


        html_content = f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Imágenes para "{query}"</title>
    <style>
        body {{ font-family: sans-serif; line-height: 1.6; margin: 20px; background-color: #f8f8f8; }}
        .container {{ max-width: 800px; margin: 20px auto; padding: 20px; background-color: #fff; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.05); }}
        h1 {{ color: #333; text-align: center; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Imágenes encontradas para "{query}"</h1>
        {images_html}
    </div>
</body>
</html>
"""

    # Generar nombre de archivo si es None
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_query_for_filename = re.sub(r'[^\w\s\-\._]', '', query).strip().replace(' ', '_')[:60]
        if not safe_query_for_filename:
             safe_query_for_filename = "image_results"
        filename = f"{safe_query_for_filename}_{timestamp}_preview.html"

    # Limpiar y asegurar nombre de archivo final
    safe_filename = "".join([c for c in filename if c.isalnum() or c in (' ', '-', '_', '.')]).rstrip()
    safe_filename = safe_filename.replace(' ', '_')
    if not safe_filename.lower().endswith('.html'):
        safe_filename += '.html'
    if not safe_filename or safe_filename.strip('._- ') == '':
         safe_filename = "image_results_preview.html"


    full_filepath = os.path.join(os.getcwd(), safe_filename)

    try:
        with open(full_filepath, "w", encoding="utf-8") as f:
            f.write(html_content)

        print(f"✅ HTML de resultados de imagen generado en: {full_filepath}")

        try:
            webbrowser.open(f"file://{os.path.abspath(full_filepath)}")
        except Exception as e:
            print(f"⚠️ No se pudo abrir el navegador automáticamente: {str(e)}")
            print(f"Por favor, abre el archivo '{full_filepath}' manualmente en tu navegador.")

    except IOError as e:
        print(f"❌ Error al escribir el archivo HTML '{safe_filename}': {str(e)}")
    except Exception as e:
        print(f"❌ Error inesperado al generar el archivo HTML: {str(e)}")


# --- Bloque principal de prueba ---
if __name__ == "__main__":
    print("--- Prueba independiente de Búsqueda de Imágenes ---")

    # Define la query de búsqueda de imágenes
    # Prueba con diferentes queries para ver los resultados
    test_image_query = "astronomia, universo" # Prueba con una query más directa en inglés
    # test_image_query = "IA en medicina" # Prueba en español
    # test_image_query = "robotics in education"

    # Define cuántos resultados quieres ver
    num_results_to_show = 5 # Puedes cambiar esto

    # Asegúrate de que la clave de Unsplash API está configurada en web_tools.py
    if web_tools.UNSPLASH_ACCESS_KEY == "TU_UNSPLASH_ACCESS_KEY":
         print("❌ Error: UNSPLASH_ACCESS_KEY no configurada en web_tools.py. No se puede buscar imágenes.")
         print("Por favor, reemplaza 'TU_UNSPLASH_ACCESS_KEY' con tu clave real.")
         sys.exit(1) # Salir si la clave no está configurada

    # Llama a la función de búsqueda de imágenes
    found_images = web_tools.find_free_images(test_image_query, num_results=num_results_to_show)

    # Genera el archivo HTML para visualizar los resultados
    create_simple_image_html(found_images, test_image_query)

    print("\n--- Fin de la prueba de Búsqueda de Imágenes ---")