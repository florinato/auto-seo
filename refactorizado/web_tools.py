# web_tools.py
# Contiene funciones de utilidad para interactuar con la web (scraping básico, manejo de URLs, búsqueda de imágenes).

# === Configuración de Unsplash API ===
import os

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
# No importamos EC ya que no se usa en las funciones movidas, aunque estaba en el original.
from webdriver_manager.chrome import ChromeDriverManager

# import urllib.parse # No se usa directamente aquí, se usa en scraper para quote_plus


load_dotenv()

# NOTA IMPORTANTE: Usa variables de entorno para la clave de API de Unsplash.
UNSPLASH_ACCESS_KEY = os.getenv("UNSPLASH_ACCESS_KEY")
UNSPLASH_API_URL = "https://api.unsplash.com/"


def setup_driver():
    """
    Configura y retorna un driver de Selenium optimizado para uso headless.
    Retorna el driver si tiene éxito, None si falla.
    """
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--log-level=3") # Menos log de Selenium
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--window-size=1920,1080") # Definir tamaño de ventana para headless

    # Usando Service para compatibilidad con versiones recientes de Selenium y webdriver-manager
    try:
        # Intentar instalar el driver si no está presente y obtener su path
        driver_path = ChromeDriverManager().install()
        service = Service(driver_path)
        driver = webdriver.Chrome(service=service, options=options)
        # print("✅ Driver de Selenium configurado correctamente (headless).") # Depuración, opcional
        return driver
    except Exception as e:
        print(f"⚠️ Error al configurar el driver de Selenium: {str(e)}")
        print("Asegúrate de tener Chrome instalado y que webdriver-manager funciona correctamente.")
        # No lanzar excepción, retorna None para que scraper.py pueda continuar sin driver
        return None


def get_final_url(ddg_redirect_url, driver):
    """
    Resuelve redirecciones de DuckDuckGo usando Selenium para obtener la URL final.
    Requiere un driver de Selenium activo.
    Retorna la URL final o None si falla.
    """
    if not driver:
        # print("⚠️ Driver de Selenium no disponible. No se puede resolver redirección.") # Depuración, opcional
        return None # No se puede resolver sin driver

    try:
        # Navegar a la URL que genera la redirección de DDG
        driver.get(ddg_redirect_url)
        # Espera hasta que la URL cambie, indicando la redirección ha terminado
        # Aumentar el timeout por si acaso (era 10, ahora 15)
        WebDriverWait(driver, 15).until(
            lambda d: d.current_url != ddg_redirect_url and d.current_url != 'about:blank' and not d.current_url.startswith('https://duckduckgo.com/') # Asegurar que salió de DDG
        )
        # Asegurarse de que la URL final no es una página de error o blank
        final_url = driver.current_url
        if final_url and final_url != 'about:blank' and not final_url.startswith('data:'):
            # print(f"➡️ Redirección resuelta a: {final_url[:60]}...") # Depuración, opcional
            return final_url
        else:
             print(f"⚠️ Redirección a URL inesperada o en blanco para {ddg_redirect_url[:60]}...")
             return None # No se redirigió a una URL útil
    except Exception as e:
        # Capturamos Timeouts u otros errores durante la redirección
        print(f"⚠️ Error de Selenium en redirección para {ddg_redirect_url[:60]}...: {str(e)}")
        return None # Falló la resolución de la URL


def extract_article_content(soup):
    """
    Extrae el contenido principal del artículo de un objeto BeautifulSoup.
    Intenta identificar bloques de contenido comunes y limpia elementos irrelevantes.
    Retorna el texto extraído o una cadena vacía/None si no se encuentra contenido significativo.
    """
    # Remover elementos que generalmente no son parte del cuerpo del artículo
    for element in soup(['script', 'style', 'nav', 'footer', 'iframe', 'aside', 'header', 'form', '.sidebar']): # Añadidos más selectores comunes
        if element: # Added check
            try:
                element.decompose()
            except Exception as e:
                 # print(f"⚠️ Error al descomponer elemento: {e}") # Depuración, opcional
                 pass


    # Selectores comunes para identificar el cuerpo del artículo
    selectors = [
        'article', # La etiqueta semántica article
        '.article-content', '.entry-content', '.post-content', # Clases comunes
        '#main-content', '#content', # IDs comunes para el área principal
        'div[itemprop="articleBody"]', # Microdatos
        'div.body', 'div.story', 'div.text', 'div.content' # Otros selectores genéricos
    ]

    content_element = None
    for selector in selectors:
        content_element = soup.select_one(selector)
        if content_element:
            # print(f"✅ Contenido encontrado usando selector: {selector}") # Depuración, opcional
            break # Encontramos un candidato, salimos del bucle

    # Si no se encontró un contenedor específico, intentar con el body o un div genérico
    if not content_element:
        # print("⚠️ No se encontró contenedor específico. Intentando fallback con body o div.") # Depuración, opcional
        content_element = soup.body or soup.find('div') # Fallback al body o al primer div

    if not content_element:
         # print("❌ No se encontró ningún elemento para extraer contenido.") # Depuración, opcional
         return None


    # Extraer texto de los párrafos dentro del elemento encontrado
    # Limite de párrafos para evitar descargar/procesar contenido masivo accidentalmente
    paragraphs = content_element.find_all('p', limit=20) # Aumentado ligeramente el límite

    # Si no hay párrafos directos, intentar extraer texto de otros elementos de bloque comunes
    if not paragraphs:
        # print("⚠️ No se encontraron <p> directos. Intentando otros elementos de bloque.") # Depuración, opcional
        block_elements = content_element.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'li', 'blockquote', 'pre', 'div'], limit=20) # Añadir otros elementos relevantes
        if block_elements:
             # Concatenar el texto de los elementos encontrados, añadiendo saltos de línea para simular estructura
             content_text = "\n\n".join(elem.get_text(strip=True) for elem in block_elements)
             if len(content_text) > 100: # Mínimo de caracteres para considerar que hay contenido
                  # print(f"✅ Contenido extraído de elementos de bloque: {len(content_text)} chars") # Depuración, opcional
                  return content_text
             else:
                  # print("⚠️ Contenido extraído de elementos de bloque muy corto.") # Depuración, opcional
                  return None

    # Si se encontraron párrafos, unirlos
    if paragraphs:
        content_text = ' '.join(p.get_text(strip=True) for p in paragraphs) # Usar strip=True para limpiar espacios en blanco
        if len(content_text) > 100:
            # print(f"✅ Contenido extraído de <p>: {len(content_text)} chars") # Depuración, opcional
            return content_text
        else:
             # print("⚠️ Contenido extraído de <p> muy corto.") # Depuración, opcional
             return None

    # Si no se encontró contenido significativo por ninguno de los métodos
    # print("❌ No se pudo extraer contenido significativo.") # Depuración, opcional
    return None


def fetch_and_extract_content(url, timeout=15):
    """
    Descarga el HTML de una URL y extrae el contenido principal del artículo.
    Función de conveniencia para usar en otros módulos.
    Retorna el texto extraído o None si falla o el contenido es insuficiente.
    """
    try:
        # Headers más amigables
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'} # User-Agent más común

        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status() # Lanza excepción para errores HTTP (4xx, 5xx)

        # Usar response.content y especificar encoding si es posible
        soup = BeautifulSoup(response.content, 'html.parser')

        # Usamos la función de extracción mejorada
        content = extract_article_content(soup)

        # Umbral mínimo de texto extraído y verificación de contenido no deseado (ej: mensajes de cookie)
        if not content or len(content) < 200 or "aceptar cookies" in content.lower() or "suscribete" in content.lower()[:200]: # Aumentado umbral, añadido filtro básico
             # print(f"⚠️ Contenido extraído muy corto ({len(content) if content else 0} chars) o sospechoso de {url[:60]}...") # Depuración, opcional
             return None

        # Limpieza final de texto (ej: eliminar espacios excesivos)
        content = ' '.join(content.split()).strip() # Reemplazar múltiples espacios/saltos por uno solo

        # print(f"✅ Contenido extraído y limpio de {url[:60]}... ({len(content)} chars)") # Depuración, opcional
        return content

    except requests.exceptions.RequestException as e:
        # print(f"⚠️ Error de red o HTTP al descargar {url[:60]}...: {str(e)}") # Depuración, opcional
        return None
    except Exception as e:
        print(f"⚠️ Error general al descargar y extraer de {url[:60]}...: {str(e)}")
        return None


# === NUEVA FUNCIÓN: Búsqueda de Imágenes en Unsplash ===
def find_free_images(query, num_results=3):
    """
    Busca imágenes en Unsplash API basadas en una query.

    Args:
        query (str): Término de búsqueda (ej: tema del artículo, tags).
        num_results (int): Número máximo de resultados a obtener (max 30 por página en Unsplash).

    Returns:
        list: Lista de diccionarios con metadata de imagen, o lista vacía si falla.
              Ej: [{'url': '...', 'alt_text': '...', 'author': '...', 'license': '...', 'author_url': '...', 'source_page_url': '...'}]
    """
    if not UNSPLASH_ACCESS_KEY or UNSPLASH_ACCESS_KEY == "TU_UNSPLASH_ACCESS_KEY":
        print("❌ Error: UNSPLASH_ACCESS_KEY no configurada. No se puede buscar imágenes.")
        return []

    search_url = f"{UNSPLASH_API_URL}search/photos"
    headers = {
        "Authorization": f"Client-ID {UNSPLASH_ACCESS_KEY}",
        "Accept-Version": "v1" # Requerido por la API de Unsplash
    }
    params = {
        "query": query,
        "per_page": min(num_results, 30), # Unsplash API tiene un límite de 30 por página
        "orientation": "landscape", # Buen formato para blogs
        "content_filter": "high", # O "low", dependiendo de la tolerancia a contenido sensible
        "lang": "es" # Si la API soporta lenguaje para la búsqueda
    }

    print(f"\n📸 Buscando imágenes en Unsplash para: '{query}'...")

    response = None # Inicializar response a None

    try:
        response = requests.get(search_url, headers=headers, params=params, timeout=10)
        response.raise_for_status() # Lanza excepción para errores HTTP (4xx, 5xx)

        data = response.json()

        if not data or 'results' not in data or not data['results']:
            print(f"⚠️ Búsqueda de imágenes para '{query}' no retornó resultados.")
            return []

        images_metadata = []
        for item in data['results']:
            # Extraer info relevante. Los campos pueden variar, revisar docs de Unsplash API.
            image_info = {
                # Usamos 'regular' o 'small' size para previews. 'full' o 'raw' son demasiado grandes.
                'url': item['urls'].get('regular') or item['urls'].get('small'),
                # Alt text: intentar descripción, alt_description, o un default
                'alt_text': item.get('alt_description') or item.get('description') or f"Imagen sobre {query}",
                # Caption: puede ser similar al alt_text o más detallado si existe
                'caption': item.get('description') or item.get('alt_description'),
                'author': item['user'].get('name', 'Unsplash'),
                'author_url': item['user'].get('links', {}).get('html'), # URL del perfil del autor para atribución
                'source_page_url': item['links'].get('html'), # URL de la página de la imagen en Unsplash (para atribución)
                'license': 'Unsplash License' # Generalmente todas son así en la API pública
            }
            # Filtrar si la URL de la imagen no existe o es None
            if image_info['url']:
                 images_metadata.append(image_info)
                 # print(f"   - Encontrada imagen: {image_info['url'][:60]}...") # Depuración, opcional

        print(f"✅ Encontradas {len(images_metadata)} imágenes para '{query}'.")
        return images_metadata

    except requests.exceptions.RequestException as e:
        print(f"❌ Error de red o HTTP al buscar imágenes en Unsplash: {str(e)}")
        print(f"   Detalles: URL={search_url}, Query='{query}'")
        if response is not None:
             print(f"   Status Code: {response.status_code}")
             try: # Intenta imprimir el cuerpo del error si es JSON
                 error_json = response.json()
                 import json
                 print(f"   Error body (JSON): {json.dumps(error_json, indent=2)[:500]}...")
             except json.JSONDecodeError: # Si no es JSON, imprime texto
                 error_body = response.text
                 if len(error_body) < 500:
                      print(f"   Response body (text): {error_body}")
                 else:
                      print(f"   Response body (text, first 500 chars): {error_body[:500]}...")
             except Exception as inner_e:
                 print(f"   Error imprimiendo cuerpo de respuesta: {inner_e}")
        return []
    except Exception as e:
        print(f"❌ Error general al buscar imágenes en Unsplash: {str(e)}")
        return []


# Bloque __main__ para pruebas independientes (opcional)
if __name__ == "__main__":
    print("--- Probando web_tools.py ---")

    # --- Prueba de Búsqueda y Extracción de Contenido ---
    test_urls = [
        "https://www.example.com/article-about-technology", # Reemplaza con URL de prueba real si tienes
        "https://www.bbc.com/news/world-europe-67890123", # Ejemplo de URL real
        "https://www.nytimes.com/2024/01/01/technology/ai-advances.html" # Ejemplo de URL real
    ]

    print("\n--- Probando fetch_and_extract_content ---")
    # Puedes descomentar esto y poner URLs reales para probar
    # for url in test_urls:
    #     print(f"\nIntentando descargar y extraer: {url}")
    #     content = fetch_and_extract_content(url)
    #     if content:
    #         print(f"Contenido extraído (primeros 500 chars):\n{content[:500]}...")
    #     else:
    #         print("Fallo la extracción.")

    # --- Prueba de Búsqueda de Imágenes ---
    print("\n--- Probando find_free_images (Requiere UNSPLASH_ACCESS_KEY) ---")
    test_query_image = "Inteligencia Artificial en Medicina"
    if UNSPLASH_ACCESS_KEY != "TU_UNSPLASH_ACCESS_KEY":
        images = find_free_images(test_query_image, num_results=2)
        if images:
            print(f"\nResultados de imágenes para '{test_query_image}':")
            for i, img in enumerate(images):
                print(f"  Imagen {i+1}:")
                print(f"    URL: {img.get('url')[:80]}...")
                print(f"    Alt Text: {img.get('alt_text')}")
                print(f"    Autor: {img.get('author')}")
                print(f"    Licencia: {img.get('license')}")
                print(f"    URL Autor: {img.get('author_url')}")
                print(f"    URL Página: {img.get('source_page_url')}")
        else:
            print(f"No se encontraron imágenes para '{test_query_image}'.")
    else:
        print("Saltando prueba de imágenes: UNSPLASH_ACCESS_KEY no configurada.")


    # --- Prueba de Selenium Driver y Redirección (Opcional, requiere Chrome instalado) ---
    # print("\n--- Probando setup_driver y get_final_url ---")
    # try:
    #     driver = setup_driver()
    #     if driver:
    #         ddg_url_redirect_example = "https://duckduckgo.com/r/?context=images&k=1&uddg=https%3A%2F%2Fwww.example.com%2Fsome-image-page" # Ejemplo de URL de redirección de DDG
    #         print(f"\nIntentando resolver redirección: {ddg_url_redirect_example}")
    #         final_url_resolved = get_final_url(ddg_url_redirect_example, driver)
    #         if final_url_resolved:
    #             print(f"URL Resuelta: {final_url_resolved}")
    #         else:
    #             print("Fallo la resolución de la URL.")
    #     else:
    #         print("Fallo la configuración del driver.")
    # except Exception as e:
    #      print(f"Error en la prueba del driver: {e}")
    # finally:
    #     if driver:
    #         driver.quit()
    #         print("\nDriver de Selenium cerrado.")


    print("\n--- Fin de la prueba de web_tools.py ---")
