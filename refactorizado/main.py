# main.py
# Punto de entrada principal. Orquesta el pipeline COMPLETO:
# Búsqueda de fuentes -> Análisis -> Guardado de fuentes ->
# Generación de contenido -> Búsqueda de imágenes -> Guardado de contenido generado y imágenes ->
# Marcado de fuentes usadas -> Simulación de publicación.

import content_generator
# Importamos los módulos necesarios
import database
import mock_publisher
import scraper
import web_tools

# analyzer y llm_client son usados internamente por otros módulos

if __name__ == "__main__":
    print("--- Iniciando Asistente de Contenido Inteligente (ACI) - Proceso Completo ---")

    # Inicializar la base de datos
    try:
        database.inicializar_db()
        print("✅ Base de datos lista.")
    except Exception as e:
        print(f"❌ Error CRÍTICO al inicializar la base de datos: {e}")
        print("Asegúrate de que 'schema.sql' existe en la ruta especificada en 'database.py' y que no hay errores en el script SQL.")
        exit(1)

    # Definir los temas para procesar
    temas_a_procesar = [ "ultimas novedades en astronomia 2025"]


    # --- Procesar cada tema ---
    for tema_actual in temas_a_procesar:
        print(f"\n--- Procesando pipeline COMPLETO para el tema: '{tema_actual}' ---")

        # =====================================================================
        # --- FASE 1: Buscar, Analizar y Guardar Fuentes ---
        # =====================================================================
        print(f"\n--- Fase 1: Búsqueda y Análisis de Fuentes para '{tema_actual}' ---")

        # Parámetros para Fase 1 (pueden venir de configuración por tema después)
        # TODO: Cargar configuración para tema_actual y usar estos valores desde config
        num_noticias_buscar = 10 # Cuántas URLs iniciales buscar en DDG
        # scraper.buscar_noticias internamente analiza con score 5 y retorna TOP N
        # num_resultados_analizar_y_guardar = 5 # Cuántas de las analizadas con score >= 5 se guardan


        resultados_analisis_scraping = scraper.buscar_noticias(
            tema_actual,
            num_noticias=num_noticias_buscar
            # scraper.buscar_noticias ya tiene un parametro num_noticias por defecto,
            # y filtra/retorna un numero limitado de resultados analizados.
            # Si queremos controlar el numero de resultados analizados retornados,
            # scraper.buscar_noticias necesita un argumento adicional para eso.
            # Por ahora, asumimos que num_noticias=10 y el filtro interno de scraper
            # (ej:[:5]) es suficiente para la fase 1.
        )

        if not resultados_analisis_scraping:
            print(f"⚠️ No se encontraron nuevos artículos fuente relevantes (score >= 5) para '{tema_actual}' en esta ejecución de Fase 1.")
            print("Continuando a Fase 2 para ver si hay fuentes antiguas utilizables...")
        else:
             print(f"\n🏆 TOP {len(resultados_analisis_scraping)} resultados analizados con Score >= 5 (se intentarán guardar como fuentes):")
             for i, art in enumerate(resultados_analisis_scraping, 1):
                 print(f"\n{i}. ⭐ {art.get('score', 'N/A')}/10: {art.get('reason', 'Sin razón')[:100]}...")
                 print(f"   🔗 {art.get('url', 'Sin URL')[:60]}...")
                 articulo_db_source_data = {
                     'titulo': art.get('titulo', f"Artículo sobre {tema_actual}"),
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
                     else:
                          print(f"   - ⚠️ Falló el guardado o no se pudo obtener ID para fuente: {articulo_db_source_data.get('url', 'N/A')}")
                 except Exception as e:
                     print(f"⚠️ Falló el guardado del artículo fuente {articulo_db_source_data.get('url', 'N/A')}: {str(e)}")
                     pass


        print(f"\n✅ Fase 1 completada para '{tema_actual}'. Fuentes investigadas y guardadas.")


        # =====================================================================
        # --- FASE 2: Generación de Contenido, Imágenes y Guardado Final ---
        # =====================================================================
        print(f"\n--- Fase 2: Generación de Contenido para '{tema_actual}' ---")

        # Parámetros para Fase 2 (pueden venir de configuración por tema después)
        # TODO: Cargar configuración para tema_actual y usar estos valores desde config
        num_fuentes_para_usar_generador = 3 # Cuántas fuentes intentar usar para la generación
        min_score_fuentes_para_usar = 7   # Score mínimo para que una fuente sea considerada por el generador
        num_imagenes_buscar = 2           # Cuántas imágenes candidatas buscar
        # TODO: Pasar parámetros de longitud, tono, plantillas de prompt a generate_seo_content


        # 1. Llamar al Generador de Contenido
        try:
            print(f"🧠 Intentando generar artículo sobre '{tema_actual}' usando {num_fuentes_para_usar_generador} fuentes con score >= {min_score_fuentes_para_usar}...")
            # content_generator.generate_seo_content internamente buscará las fuentes relevantes y no usadas.
            # Pasa los parámetros necesarios.
            generated_article_data = content_generator.generate_seo_content(
                topic=tema_actual,
                num_sources=num_fuentes_para_usar_generador,
                min_score=min_score_fuentes_para_usar
                # TODO: Pasar argumentos adicionales (longitud, tono, prompts) aquí
            )

            # --- Check si la generación fue exitosa ---
            if generated_article_data:
                print(f"\n🎉 Artículo generado exitosamente para '{tema_actual}'.")
                # generate_seo_content ya añadió 'tema', 'score_fuentes_promedio', 'fuente_ids_usadas'

                # 2. Guardar el artículo generado en la DB (tabla articulos_generados)
                print("💾 Intentando guardar artículo generado en DB...") # Debug print
                generated_article_id = None # Inicializar a None
                try:
                    generated_article_id = database.save_generated_article(generated_article_data)
                    if generated_article_id:
                        print(f"✅ Artículo generado guardado en DB con ID {generated_article_id}.")
                    else:
                         # save_generated_article solo retorna None si hay un error capturado internamente
                         print(f"❌ save_generated_article retornó None para tema '{tema_actual}'. Esto indica un fallo interno en la función.")
                         # Si falla el guardado del generado, no podemos asociar imágenes ni marcar fuentes, ni publicar
                         generated_article_data = None # Invalidar generated_article_data para saltar fases posteriores
                         # No levantar excepción aquí, el print anterior ya informa

                except Exception as e:
                    # Este catch es si save_generated_article LANZA una excepción
                    print(f"❌ ERROR al guardar artículo generado en DB para tema '{tema_actual}': {str(e)}")
                    # Si falla el guardado, no podemos asociar imágenes ni marcar fuentes, ni publicar
                    generated_article_data = None # Invalidar generated_article_data para saltar fases posteriores
                    # No levantar excepción aquí, el print anterior ya informa


                # --- Continuar solo si el artículo generado se guardó con éxito ---
                if generated_article_data: # Verifica de nuevo si sigue siendo válido (no None por los fallos anteriores)
                     print("✅ Artículo generado guardado correctamente. Procediendo con imágenes y marcado de fuentes...") # Debug print

                     # 3. Buscar Imágenes para el Artículo Generado
                     print(f"\n🖼️ Buscando {num_imagenes_buscar} imágenes relacionadas...")
                     image_search_query = generated_article_data.get('title', tema_actual)
                     tags_list = generated_article_data.get('tags', [])
                     if isinstance(tags_list, list) and tags_list:
                         image_search_query += " " + " ".join(tags_list)
                     image_search_query = image_search_query[:150].strip()

                     print(f"   - Query para búsqueda de imágenes: '{image_search_query[:80]}...'")

                     try:
                         found_images_metadata = web_tools.find_free_images(image_search_query, num_results=num_imagenes_buscar)

                         # 4. Guardar la metadata de las imágenes encontradas en la DB
                         if found_images_metadata:
                              print(f"💾 Guardando metadata de {len(found_images_metadata)} imágenes encontradas en DB...")
                              # Necesitamos el generated_article_id que obtuvimos antes
                              if generated_article_id is not None:
                                  for img_meta in found_images_metadata:
                                      img_meta['articulo_generado_id'] = generated_article_id
                                      try:
                                          database.save_image_metadata(img_meta)
                                      except Exception as e:
                                          print(f"⚠️ Falló el guardado de metadata de una imagen para articulo ID {generated_article_id}: {str(e)}")
                                          pass # Continúa

                                  print("✅ Metadata de imágenes guardada.")
                              else:
                                   print("⚠️ No se pudo obtener generated_article_id. No se guardará metadata de imágenes.")

                         else:
                             print("⚠️ No se encontraron imágenes adecuadas para guardar.")

                     except Exception as e:
                          print(f"❌ ERROR durante búsqueda o guardado de imágenes para tema '{tema_actual}': {str(e)}")
                          pass # Continúa


                     # 5. Marcar las fuentes utilizadas como 'usada_para_generar = 1'
                     print("\n🔄 Intentando marcar fuentes utilizadas como usadas...") # Debug print
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
                          print(f"❌ ERROR al marcar fuentes utilizadas para tema '{tema_actual}': {str(e)}")
                          pass # Continúa


                     # 6. Simular Publicación (Generar HTML para previsualización)
                     print("\n🚀 Simulando Publicación (Generando archivo HTML)...") # Debug print
                     try:
                         # Necesitamos los datos completos del artículo generado para el publisher
                         # generated_article_data ya los tiene (excepto las imágenes guardadas, pero mock_publisher acepta la lista temporal)
                         mock_publisher.publish_to_html(generated_article_data, image_data=found_images_metadata)
                         print("✅ Simulación de publicación completada.")
                     except Exception as e:
                          print(f"❌ ERROR al simular publicación (generar HTML) para tema '{tema_actual}': {str(e)}")
                          pass # Continúa si hay más temas


                else: # Si generated_article_data se volvio None por un fallo en el guardado
                    print("⏩ Saltando búsqueda de imágenes, marcado de fuentes y publicación simulada debido a un fallo anterior.")


            else: # Si content_generator.generate_seo_content devolvió None
                print(f"❌ La generación de contenido para '{tema_actual}' falló (generate_seo_content retornó None). Saltando fases posteriores.")
                # content_generator.py ya habrá impreso los detalles del error

        except Exception as e: # Captura errores generales durante la llamada a generate_seo_content
            print(f"❌ ERROR general durante la fase de generación para '{tema_actual}': {str(e)}")
            pass # Continúa al siguiente tema

        print(f"\n--- Pipeline COMPLETO para '{tema_actual}' finalizado. ---")
        print("-" * 40)


    print("\n✅ Proceso principal completo (Pipeline de generación ejecutado para todos los temas).")