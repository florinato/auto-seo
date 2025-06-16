# main.py
# Punto de entrada principal. Orquesta solo la fase de búsqueda, análisis y guardado de fuentes.

import scraper

# Importamos los módulos necesarios
import database

# analyzer y llm_client son usados internamente por scraper y analyzer,
# no necesitan importarse aquí directamente para la estructura deseada.

if __name__ == "__main__":
    # Inicializar la base de datos - LLAMA A LA FUNCIÓN QUE CARGA schema.sql
    # Esto asegurará que las tablas existan.
    database.inicializar_db()

    # Definir los temas para buscar fuentes
    # Puedes cambiar este tema si ya tienes muchas fuentes sobre él
    temas = ["ultimas noticias sobre la guerra en Ucrania"]
    # Ejemplo con otro tema: temas = ["tendencias en robótica educativa 2024"]s


    # Iterar sobre los temas
    for tema in temas:
        # --- FASE 1: Buscar y Analizar Fuentes ---
        print(f"\n--- Iniciando fase de búsqueda y análisis de fuentes para '{tema}' ---")

        # El scraper busca noticias, las analiza con Gemini y retorna las metadata de las que pasaron el filtro (score >= 5)
        # Mantenemos el comportamiento original de buscar un máximo de 5 resultados analizados
        resultados_analisis_scraping = scraper.buscar_noticias(tema, num_noticias=10)

        # === Lógica de Feedback si no hay resultados analizados ===
        if not resultados_analisis_scraping:
            print(f"⚠️ No se encontraron artículos fuente relevantes (score >= 5) para '{tema}' en esta ejecución.")
            print("Esto puede deberse a que las fuentes encontradas ya estaban en la base de datos, no cumplieron el criterio de score/contenido, o hubo errores de acceso.")
            print("No se guardará ninguna fuente en esta ejecución para este tema.")
            continue # Saltar al siguiente tema o terminar si solo hay uno
        # === FIN Lógica de Feedback ===


        # Imprimir los resultados analizados que se considerarán para guardar
        # Mantenemos la impresión original del TOP 3 de los resultados analizados encontrados
        print(f"\n🏆 TOP {min(len(resultados_analisis_scraping), 3)} resultados analizados con Score >= 5 (se intentarán guardar como fuentes):")

        # Iterar sobre los primeros 3 resultados analizados para imprimir y guardar
        # El .get() para score, reason, url, tags y resumen se usa para mayor seguridad, aunque tu original usaba [] para algunos.
        # Mantengo la lógica de iterar solo sobre los 3 primeros analizados (resultados_analisis_scraping[:3])
        for i, art in enumerate(resultados_analisis_scraping[:3], 1):
            print(f"\n{i}. ⭐ {art.get('score', 'N/A')}/10: {art.get('reason', 'Sin razón')}")
            print(f"   🔗 {art.get('url', 'Sin URL')}")
            resumen_texto = art.get('resumen', art.get('reason', 'Sin resumen'))
            print(f"   📝 Resumen: {resumen_texto}")
            print(f"   🏷️ Tags: {', '.join(art.get('tags', []))}")

            # Preparar el diccionario del artículo para guardar en la tabla 'articulos'
            # Esta función guarda en la tabla 'articulos' y 'articulos_fuente_tags'.
            # Asumimos que guardar_articulo ahora también maneja el campo 'usada_para_generar' (con default 0)
            # y retorna el ID del artículo fuente guardado o existente.
            articulo_db_source_data = {
                'titulo': art.get('titulo', f"Artículo sobre {tema}"), # Lógica similar a la original
                'url': art.get('url', 'Sin URL'), # Usando .get por seguridad
                'score': art.get('score', 0), # Usando .get por seguridad
                'resumen': art.get('resumen', art.get('reason', '')[:100]), # Lógica original para resumen
                'fuente': art.get('url', '').split('/')[2] if art.get('url') else '',
                'tags': art.get('tags', []) # Usando .get
                # 'usada_para_generar' no se pasa aquí; se espera que save_articulo la inserte con DEFAULT 0
            }

            # Guardar el artículo fuente en la base de datos
            try:
                # guardar_articulo ahora retorna el ID del artículo fuente guardado o existente
                source_id_saved = database.guardar_articulo(articulo_db_source_data)
                if source_id_saved:
                    print(f"   - Guardado/Actualizado como fuente en DB con ID {source_id_saved}.")
                else:
                     # Esto podría ocurrir si guardar_articulo retorna None por algún fallo interno
                     print(f"   - ⚠️ Falló el guardado o no se pudo obtener ID para fuente: {articulo_db_source_data.get('url', 'N/A')}")

            except Exception as e:
                # El manejo de error original solo imprime y continúa. Lo replicamos.
                print(f"⚠️ Falló el guardado del artículo fuente {articulo_db_source_data.get('url', 'N/A')}: {str(e)}")
                pass # Continúa con el siguiente artículo fuente aunque falle uno

        print("\n✅ Fase de búsqueda, análisis y guardado de fuentes completada.")

    # Mensaje final - Copiado exacto del original (aunque ahora solo guarda fuentes)
    print("\n✅ Proceso principal completado (solo búsqueda y guardado de fuentes).")