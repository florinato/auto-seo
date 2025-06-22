# Genera un artículo de blog optimizado para SEO basado en fuentes y busca imágenes.

import json
import os  # Importar os para construir rutas de archivo
import re
from datetime import datetime

import database
import llm_client
import mock_publisher
import web_tools


def clean_json_response(json_str):
    """
    Intenta corregir errores comunes en la respuesta JSON de la IA.
    """
    # Eliminar comas adicionales al final de objetos o arrays
    json_str = re.sub(r',\s*([}\]])', r'\1', json_str)
    # Reemplazar dobles comillas dentro de las claves o valores (si es necesario)
    json_str = json_str.replace('\\"', '"')
    # Eliminar saltos de línea y tabulaciones innecesarias
    json_str = re.sub(r'\s+', ' ', json_str)
    # Eliminar caracteres de control no válidos (excepto tab, newline, return)
    regex_control_chars = r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F\u2028\u2029]'
    json_str = re.sub(regex_control_chars, '', json_str)
    return json_str.strip()


def generate_seo_content(topic, num_sources=3, min_score=7):
    """
    Genera un artículo de blog optimizado para SEO basado en fuentes encontradas en la DB.
    """
    print(f"\n✍️ Generando contenido para: {topic}")

    source_articles_meta = database.get_relevant_articles(topic=topic, min_score=min_score, limit=num_sources)

    if not source_articles_meta:
        print(f"❌ No se encontraron suficientes artículos fuente con score >= {min_score} para generar contenido sobre '{topic}'.")
        return None

    print(f"📚 Encontrados {len(source_articles_meta)} artículos fuente relevantes. Cargando contenido...")

    source_contents = []
    total_score = 0
    loaded_source_count = 0
    source_ids_used = []

    for i, article_meta in enumerate(source_articles_meta):
        url = article_meta.get('url')
        source_id = article_meta.get('id')
        score = article_meta.get('score', 0)

        if url and source_id is not None:
            content = web_tools.fetch_and_extract_content(url)

            if content:
                source_contents.append(f"### Fuente {i+1}: {article_meta.get('titulo', url)}\n\n{content}\n\n---\n\n")
                print(f"   - ✅ Contenido cargado de: {url[:60]}... (Score: {score})")
                total_score += score
                loaded_source_count += 1
                source_ids_used.append(source_id)
            else:
                 print(f"   - ⚠️ Falló o contenido muy corto de: {url[:60]}... (Score: {score})")

    if not source_contents:
        print(f"❌ No se pudo cargar contenido de ninguna fuente. No se puede generar artículo.")
        return None

    avg_source_score = total_score / loaded_source_count if loaded_source_count > 0 else 0
    print(f"📊 Score promedio de fuentes cargadas: {avg_source_score:.2f}")

    sources_text = "".join(source_contents)

    generation_prompt = f"""
Eres un experto redactor de contenido SEO y especialista en [marketing digital]. Tu objetivo es crear un artículo de blog **único, valioso y altamente optimizado para SEO** sobre el tema: **"{topic}"**.

Utilizarás la información proporcionada en las siguientes {loaded_source_count} fuentes para inspirarte y obtener datos, pero DEBES sintetizarla y reescribirla completamente con tus propias palabras. No copies ni parafrasees frases o párrafos directamente.

---
**Fuentes de Información:**
{sources_text}
---

**Instrucciones para el Artículo Generado:**

1.  **Rol:** Actúa como un redactor experto que crea contenido de autoridad para un blog especializado.
2.  **Tarea:** Escribe un artículo completo y bien estructurado sobre "{topic}".
3.  **Originalidad:** El artículo debe ser 100% original, resultado de la síntesis y reescritura de las fuentes. Evita el plagio.
4.  **Longitud:** Intenta que el cuerpo del artículo tenga una longitud razonable (ej: más de 1500 palabras), cubriendo los puntos clave de las fuentes.
5.  **Estructura y Formato:**
    *   Presenta la salida **EXCLUSIVAMENTE** como un objeto JSON válido.
    *   El objeto JSON DEBE ser válido y estar bien formado.
    *   El JSON debe tener las siguientes claves:
        *   `title`: Un título atractivo y optimizado para SEO (debe incluir la palabra clave principal "{topic}").
        *   `meta_description`: Una meta descripción concisa y persuasiva para motores de búsqueda (aprox. 150-160 caracteres), incluyendo la palabra clave principal.
        *   `tags`: Una lista de 3-4 palabras clave relevantes para el artículo.
        *   `body`: El contenido completo del artículo en formato Markdown. Dentro del 'body':
            *   Usa `##` para encabezados H2 y `###` para H3.
            *   Incluye una introducción clara.
            *   Divide el contenido en secciones lógicas usando encabezados H2/H3.
            *   Usa párrafos, listas (con `-` o `*` para puntos) y texto en **negrita** (con `**`) para mejorar la legibilidad.
            *   Incluye una conclusión.
6.  **Optimización SEO:**
    *   Incluye la palabra clave principal "{topic}" de forma natural en el `title`, `meta_description`, al principio del `body` (introducción), y en algunos encabezados (H2/H3) y párrafos del cuerpo.
    *   Incorpora las palabras clave secundarias que incluirás en la lista `tags` de forma natural en el cuerpo del artículo.
    *   Escribe para un público humano: el texto debe ser fácil de leer, interesante y útil.
7.  **Contenido:** Base el contenido *únicamente* en la información de las fuentes proporcionadas. No inventes datos ni afirmaciones. Si una fuente contradice a otra, puedes mencionarlo o simplemente omitir la información menos soportada, a tu criterio como experto.

Produce **SOLO** el objeto JSON. No añadas texto explicativo antes ni después del JSON.
"""

    try:
        print("🧠 Solicitando generación de contenido a Gemini...")
        raw_response_text = llm_client.generate_raw_content(generation_prompt)

        json_match = re.search(r'\{.*\}', raw_response_text, re.DOTALL)

        if json_match:
            json_str = json_match.group(0)
            json_str = json_str.replace('```json', '').replace('```', '').strip()

            cleaned_json_str = clean_json_response(json_str)

            try:
                generated_data = json.loads(cleaned_json_str)
                print("✅ JSON cargado con éxito después de la limpieza.")
            except json.JSONDecodeError as e:
                print(f"❌ Error al parsear JSON después de la limpieza: {e}")
                print(f"Cadena intentando parsear (limpia):\n{cleaned_json_str[:500]}...")
                return None

            required_keys = ['title', 'meta_description', 'tags', 'body']
            if not all(key in generated_data for key in required_keys):
                 print(f"❌ Respuesta de IA con formato JSON incompleto. Faltan claves.")
                 print(f"Respuesta limpia recibida:\n{cleaned_json_str[:500]}...")
                 return None

            print("✅ Contenido generado y parseado con éxito.")
            generated_data['tema'] = topic
            generated_data['score_fuentes_promedio'] = avg_source_score
            generated_data['fuente_ids_usadas'] = source_ids_used # Aunque no se usen ahora, es buena data

            return generated_data

        else:
            print("❌ La respuesta de la IA no contenía un objeto JSON válido.")
            print(f"Respuesta cruda recibida:\n{raw_response_text[:500]}...")
            return None

    except json.JSONDecodeError as e:
        print(f"❌ Error al parsear la respuesta JSON de la IA (incluso después de limpieza): {str(e)}")
        if 'cleaned_json_str' in locals():
             print(f"Cadena intentando parsear (limpia):\n{cleaned_json_str[:500]}...")
        return None
    except Exception as e:
        print(f"❌ Error general al generar contenido: {str(e)}")
        return None

# === Bloque para pruebas independientes ===
if __name__ == "__main__":
    print("--- Prueba independiente del Generador de Contenido (Leyendo de DB Real y generando HTML con imágenes) ---")

    try:
        database.inicializar_db()
        print("✅ Base de datos lista para prueba independiente.")
    except Exception as e:
        print(f"❌ Error al inicializar la base de datos para la prueba: {e}")
        print("Asegúrate de que 'schema.sql' y 'seo_autopilot.db' están accesibles.")
        exit(1)

    # Define el tema para probar. Asegúrate de tener fuentes sobre él con score >= min_score no usadas.
    test_topic = "experiencias cercanas a la muerte impactantes"

    test_num_sources = 10
    test_min_score = 7

    generated_article = generate_seo_content(
        topic=test_topic,
        num_sources=test_num_sources,
        min_score=test_min_score
    )

    if generated_article:
        print("\n--- RESULTADO DE LA GENERACIÓN ---")
        print(f"Título: {generated_article.get('title', 'N/A')}")
        print(f"Meta Descripción: {generated_article.get('meta_description', 'N/A')}")
        print(f"Tags: {', '.join(generated_article.get('tags', []))}")
        print(f"Score Promedio Fuentes: {generated_article.get('score_fuentes_promedio', 'N/A'):.2f}")
        print(f"Fuentes usadas (IDs): {generated_article.get('fuente_ids_usadas', [])}")
        print("\nCuerpo (Markdown):\n")
        body_content = generated_article.get('body', 'Contenido vacío')
        print(body_content[:1000] + "..." if len(body_content) > 1000 else body_content)
        print("\n--- FIN RESULTADO ---")

        # === Buscar Imágenes para el Artículo (dentro de la prueba independiente) ===
        print("\n🖼️ Buscando imágenes relacionadas para la previsualización...")
        image_search_query = generated_article.get('title', test_topic)
        tags_list = generated_article.get('tags', [])
        print("*******lista de tags*******",tags_list)
        if isinstance(tags_list, list) and tags_list:
             image_search_query += " " + " ".join(tags_list)
        image_search_query = image_search_query[:150].strip()

        found_images_metadata = web_tools.find_free_images(image_search_query, num_results=2)

        if not found_images_metadata:
            print("⚠️ No se encontraron imágenes adecuadas para la previsualización.")
        else:
            print(f"✅ Encontradas {len(found_images_metadata)} imágenes para la previsualización.")

        # === Simular Publicación con Mock Publisher (incluyendo imágenes) ===
        print("\n🚀 Simulando Publicación (Generando HTML)...")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_title_for_filename = re.sub(r'[^\w\-_\. ]', '', generated_article.get('title', test_topic)).replace(' ', '_')[:50]
        filename = f"{safe_title_for_filename}_{timestamp}_preview.html"

        # Llamar a mock_publisher, pasando los datos del artículo Y la lista de metadata de imágenes
        mock_publisher.publish_to_html(generated_article, image_data=found_images_metadata, filename=filename)
        print("✅ Simulación de publicación completada.")

        # NOTA: En el flujo principal orquestado por main.py, aquí también llamarías
        # para guardar todo en la DB antes de marcar las fuentes como usadas.

    else:
        print("\n❌ La generación de contenido independiente falló. No se generará archivo HTML.")

    print("\n--- Fin de la prueba independiente del Generador ---")
