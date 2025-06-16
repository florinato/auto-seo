# llm_client.py
import os

import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
# Configurar la API de Gemini con la clave de entorno
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def generate_raw_content(prompt, model_name="gemini-2.0-flash-lite-preview-02-05"):
    """
    Genera contenido crudo usando el modelo Gemini.
    Esta función es un wrapper simple de la llamada generate_content.
    No maneja prompts específicos ni parsing de resultados.
    """
    try:
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(prompt)
        # Devuelve solo el texto, como en el código original
        return response.text
    except Exception as e:
        # Relanzar la excepción para que el llamador la maneje
        raise e
