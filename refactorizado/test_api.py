import json

import requests


def test_generate_article():
    """
    Prueba el endpoint /generate de la API.
    """
    url = "http://localhost:8000/generate"  # Ajusta la URL si es diferente
    tema = "resumen cientiifico de la IA en 2024"  # Tema de prueba
    payload = {"tema": tema}
    headers = {"Content-Type": "application/json"}

    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        response.raise_for_status()  # Lanza una excepción para errores HTTP

        data = response.json()
        print(f"Respuesta de /generate: {json.dumps(data, indent=2)}")
        # Aquí puedes agregar más aserciones para verificar la respuesta,
        # por ejemplo, que se haya devuelto un article_id.
        if "article_id" in data:
            print("Prueba exitosa: article_id recibido.")
        else:
            print("Prueba fallida: article_id no recibido.")

    except requests.exceptions.RequestException as e:
        print(f"Error en la petición: {e}")
    except json.JSONDecodeError as e:
        print(f"Error al decodificar la respuesta JSON: {e}")
    except Exception as e:
        print(f"Ocurrió un error inesperado: {e}")

if __name__ == "__main__":
    test_generate_article()
