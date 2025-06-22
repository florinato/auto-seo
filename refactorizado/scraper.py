# scraper.py
# Se encarga de buscar URLs candidatas (ej. en DuckDuckGo), resolverlas y analizar su metadata.

import json  # Mantenido aunque no se use directamente, estaba en el original
import re  # Mantenido aunque no se use directamente, estaba en el original
from urllib.parse import quote_plus

import analyzer
# Mantener imports necesarios para la búsqueda inicial (DuckDuckGo HTML)
import requests
import web_tools  # Importamos las herramientas web
from bs4 import BeautifulSoup

# Importamos módulos de utilidad y análisis
import database


def buscar_noticias(query: str, num_noticias: int = 5, min_score_fuente: int = 5, prompt_analyzer_template: str = None):
    """
    Busca noticias sobre un tema (query), resuelve URLs, analiza con IA y retorna resultados.

    Args:
        query (str): El tema o consulta de búsqueda.
        num_noticias (int): Número máximo de artículos a retornar después del filtrado.
        min_score_fuente (int): Score mínimo que debe tener una fuente analizada para ser considerada.
        prompt_analyzer_template (str, optional): Plantilla de prompt para el analizador. Defaults to None.
    """
    print(f"\n🔍 Buscando noticias sobre: {query} (Num noticias: {num_noticias}, Score min: {min_score_fuente})")

    # La función interna de búsqueda no necesita cambios.
    def fetch_urls_from_ddg():
        """Realiza la búsqueda en DuckDuckGo y retorna una lista de URLs candidatas."""
        query = f"{tema} site:.es OR site:.com after:2024"
        url = f"https://duckduckgo.com/html/?q={quote_plus(query)}&kl=es-es"
        headers = {'User-Agent': 'Mozilla/5.0'}

        try:
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            return [
                ("https:" + a['href'] if a['href'].startswith("//") else a['href'])
                for a in soup.select('a.result__url')[:10]
                if not any(x in a['href'] for x in ["youtube.com", "facebook.com", "twitter.com", "linkedin.com"])
            ]
        except requests.exceptions.RequestException as e:
            print(f"⚠️ Error en búsqueda de URLs (RequestException): {str(e)}")
            return []
        except Exception as e:
            print(f"⚠️ Error en búsqueda de URLs (General Exception): {str(e)}")
            return []

    # --- Lógica principal con la estructura corregida ---
    
    ranked_articles = []
    driver = None  # Inicializar driver fuera del try para que exista en el finally

    try:
        # 1. Iniciar el driver UNA SOLA VEZ.
        try:
            driver = web_tools.setup_driver()
        except Exception as e:
            print(f"❌ Falló la configuración del driver de Selenium: {e}. No se podrán resolver redirecciones.")
            driver = None # Asegurar que es None si falla

        # 2. Iterar sobre las URLs. El driver ya está vivo.
        for url in fetch_urls_from_ddg():
            try:
                # Resolver redirección (si el driver existe)
                final_url = url
                if driver:
                    resolved = web_tools.get_final_url(url, driver)
                    if resolved:
                        final_url = resolved
                    else:
                        print(f"⚠️ Usando URL original por fallo en redirección: {final_url[:60]}...")
                
                # Control de duplicados
                if database.url_existe(final_url):
                    print(f"⏩ Saltando duplicado: {final_url[:60]}...")
                    continue

                # Filtrar URLs no deseadas
                if any(x in final_url for x in ["/tag/", "/temas/", "?page=", "#", "/category/", ".pdf", ".zip"]):
                    print(f"⏩ Saltando URL no-articulo/archivo: {final_url[:60]}...")
                    continue

                # Obtener contenido
                text = web_tools.fetch_and_extract_content(final_url)
                if not text:
                    print(f"⏩ Saltando URL por contenido no extraído/muy corto: {final_url[:60]}...")
                    continue

                # Analizar con IA
                # TODO: Modificar analyzer.analyze_with_gemini para que acepte prompt_template si se proporciona
                analysis_result = analyzer.analyze_with_gemini(query, text) # Pasando 'query' como el tema para el análisis

                if not analysis_result: # Si el análisis falla o retorna None
                    print(f"⏩ Saltando URL por fallo en análisis IA: {final_url[:60]}...")
                    continue

                analysis_result['url'] = final_url # Asegurar que la URL está en el resultado
                ranked_articles.append(analysis_result)
                print(f"✅ Analizado: {final_url[:60]}... | Score: {analysis_result.get('score', 0)}")

            except Exception as e:
                # Capturar error de UNA SOLA URL, para que el bucle continúe
                print(f"⚠️ Error procesando URL {url}: {e}")
                # continue no es necesario, el bucle avanzará naturalmente

    finally:
        # 3. Cerrar el driver UNA SOLA VEZ al final de todo el proceso.
        if driver:
            try:
                driver.quit()
                print("\n✅ Driver de Selenium cerrado correctamente.")
            except Exception as e:
                print(f"⚠️ Error al cerrar el driver de Selenium: {e}")

    # Filtrar y ordenar los resultados
    # Usar el parámetro min_score_fuente en lugar del valor hardcodeado 5
    print(f"Filtrando artículos analizados con score >= {min_score_fuente}...")
    valid_articles = [a for a in ranked_articles if a and isinstance(a.get('score'), (int, float)) and a.get('score', 0) >= min_score_fuente]

    if not valid_articles:
        print(f"ℹ️ No se encontraron artículos con score >= {min_score_fuente} después del análisis.")
        return []

    valid_articles.sort(key=lambda x: x.get('score', 0), reverse=True)

    print(f"🏆 Retornando TOP {min(len(valid_articles), num_noticias)} artículos de {len(valid_articles)} válidos.")
    return valid_articles[:num_noticias]

