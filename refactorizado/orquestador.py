# orquestador.py
# Módulo orquestrador para el proceso de generación de contenido.
# Este módulo reemplaza la funcionalidad principal de main.py,
# pero está diseñado para ser llamado desde una API.

import content_generator
import database
import mock_publisher
import scraper
import web_tools
from models import GenerationParameters  # Importa el modelo de parámetros


def procesar_tema(tema: str, params: GenerationParameters):
    """
    Procesa un tema específico, ejecutando el pipeline completo.

    Args:
        tema (str): El tema a procesar.
        params (GenerationParameters): Parámetros de generación.
    """
    print(f"--- Iniciando procesamiento para el tema: '{tema}' ---")

    # =====================================================================
    # --- FASE 1: Buscar, Analizar y Guardar Fuentes ---
    # =====================================================================
    print(f"\n--- Fase 1: Búsqueda y Análisis de Fuentes para '{tema}' ---")

    num_noticias_buscar = params.num_fuentes_generador * 2  # Ajuste basado en los parámetros

    resultados_analisis_scraping = scraper.buscar_noticias(
        tema,
        num_noticias=num_noticias_buscar
    )

    if not resultados_analisis_scraping:
        print(f"⚠️ No se encontraron nuevos artículos fuente relevantes (score >= 5) para '{tema}' en esta ejecución de Fase 1.")
        return False  # Indica que no se pudo procesar el tema

    fuentes_guardadas = []
    for art in resultados_analisis_scraping:
        articulo_db_source_data = {
            'titulo': art.get('titulo', f"Artículo sobre {tema}"),
            'url': art.get('url', 'Sin URL'),
            'score': art.get('score', 0),
            'resumen': art.get('resumen', art.get('reason', '')),
            'fuente': art.get('url', '').split('/')[2] if art.get('url') else '',
            'tags': art.get('tags', [])
        }
        try:
            source_id_saved = database.guardar_articulo(articulo_db_source_data)
            if source_id_saved:
                print(f"   - Guardado/Actualizado como fuente en DB con ID {source_id_saved}.")
                fuentes_guardadas.append(source_id_saved)
            else:
                print(f"   - ⚠️ Falló el guardado o no se pudo obtener ID para fuente: {articulo_db_source_data.get('url', 'N/A')}")
        except Exception as e:
            print(f"⚠️ Falló el guardado del artículo fuente {articulo_db_source_data.get('url', 'N/A')}: {str(e)}")
            pass

    if not fuentes_guardadas:
        print(f"⚠️ No se guardaron fuentes para '{tema}'.")
        return False

    print(f"\n✅ Fase 1 completada para '{tema}'. Fuentes investigadas y guardadas.")

    # =====================================================================
    # --- FASE 2: Generación de Contenido, Imágenes y Guardado Final ---
    # =====================================================================
    print(f"\n--- Fase 2: Generación de Contenido para '{tema}' ---")

    try:
        print(f"🧠 Intentando generar artículo sobre '{tema}'...")
        generated_article_data = content_generator.generate_seo_content(
            topic=tema,
            num_sources=params.num_fuentes_generador,
            min_score=params.min_score_fuentes_generador,
            longitud=params.longitud,
            tono=params.tono
        )

        if generated_article_data:
            print(f"\n🎉 Artículo generado exitosamente para '{tema}'.")

            try:
                generated_article_id = database.save_generated_article(generated_article_data)
                if generated_article_id:
                    print(f"✅ Artículo generado guardado en DB con ID {generated_article_id}.")
                else:
                    print(f"❌ save_generated_article retornó None para tema '{tema}'.")
                    return False
            except Exception as e:
                print(f"❌ ERROR al guardar artículo generado en DB para tema '{tema}': {str(e)}")
                return False

            print("✅ Artículo generado guardado correctamente. Procediendo con imágenes y marcado de fuentes...")

            print(f"\n🖼️ Buscando {params.num_imagenes_buscar} imágenes relacionadas...")
            image_search_query = generated_article_data.get('title', tema)
            tags_list = generated_article_data.get('tags', [])
            if isinstance(tags_list, list) and tags_list:
                image_search_query += " " + " ".join(tags_list)
            image_search_query = image_search_query[:150].strip()

            print(f"   - Query para búsqueda de imágenes: '{image_search_query[:80]}...'")

            try:
                found_images_metadata = web_tools.find_free_images(image_search_query, num_results=params.num_imagenes_buscar)

                if found_images_metadata:
                    print(f"💾 Guardando metadata de {len(found_images_metadata)} imágenes encontradas en DB...")
                    if generated_article_id is not None:
                        for img_meta in found_images_metadata:
                            img_meta['articulo_generado_id'] = generated_article_id
                            try:
                                database.save_image_metadata(img_meta)
                            except Exception as e:
                                print(f"⚠️ Falló el guardado de metadata de una imagen para articulo ID {generated_article_id}: {str(e)}")
                                pass
                        print("✅ Metadata de imágenes guardada.")
                    else:
                        print("⚠️ No se pudo obtener generated_article_id. No se guardará metadata de imágenes.")
                else:
                    print("⚠️ No se encontraron imágenes adecuadas para guardar.")
            except Exception as e:
                print(f"❌ ERROR durante búsqueda o guardado de imágenes para tema '{tema}': {str(e)}")
                pass

            print("\n🔄 Intentando marcar fuentes utilizadas como usadas...")
            try:
                source_ids_actually_used = generated_article_data.get('fuente_ids_usadas', [])
                if source_ids_actually_used:
                    print(f"✅ Marcando {len(source_ids_actually_used)} fuentes utilizadas como usadas...")
                    for source_article_id in source_ids_actually_used:
                        database.mark_source_used(source_article_id)
                    print("✅ Fuentes marcadas como usadas.")
                else:
                    print("⚠️ No se pudo obtener la lista de IDs de fuentes utilizadas del artículo generado. No se marcará ninguna como usada.")
            except Exception as e:
                print(f"❌ ERROR al marcar fuentes utilizadas para tema '{tema}': {str(e)}")
                pass

            print("\n🚀 Simulando Publicación (Generando archivo HTML)...")
            try:
                mock_publisher.publish_to_html(generated_article_data, image_data=found_images_metadata)
                print("✅ Simulación de publicación completada.")
            except Exception as e:
                print(f"❌ ERROR al simular publicación (generar HTML) para tema '{tema}': {str(e)}")
                pass

        else:
            print(f"❌ La generación de contenido para '{tema}' falló.")
            return False

    except Exception as e:
        print(f"❌ ERROR general durante la fase de generación para '{tema}': {str(e)}")
        return False

    print(f"\n--- Pipeline COMPLETO para '{tema}' finalizado. ---")
    return True

def main():
    """
    Función principal para probar el orquestador.
    """
    database.inicializar_db()  # Asegúrate de inicializar la base de datos

    # Ejemplo de uso:
    from models import GenerationParameters
    tema_ejemplo = "experiencias cercanas a la muerte impactantes"
    parametros_ejemplo = GenerationParameters(
        tema=tema_ejemplo,
        num_fuentes_generador=3,
        min_score_fuentes_generador=7,
        num_imagenes_buscar=2,
        longitud="media",
        tono="neutral"
    )
    procesar_tema(tema_ejemplo, parametros_ejemplo)

if __name__ == "__main__":
    main()
