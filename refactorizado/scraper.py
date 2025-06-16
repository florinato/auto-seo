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


def buscar_noticias(tema, num_noticias=5):
    """
    Busca noticias sobre un tema, resuelve URLs, analiza con IA y retorna resultados.
    """
    print(f"\n🔍 Buscando noticias sobre: {tema}")

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
                analysis = analyzer.analyze_with_gemini(tema, text)
                analysis['url'] = final_url
                ranked_articles.append(analysis)
                print(f"✅ Analizado: {final_url[:60]}... | Score: {analysis.get('score', 0)}")

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

    # Filtrar y ordenar los resultados (esto ya estaba bien)
    ranked_articles = [a for a in ranked_articles if a.get('score', 0) >= 5]
    ranked_articles.sort(key=lambda x: x.get('score', 0), reverse=True)

    return ranked_articles[:num_noticias]

