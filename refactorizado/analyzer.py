# analyzer.py
import json
import re

# Importamos el cliente LLM básico
import llm_client


def analyze_with_gemini(tema, text):
    """
    Analiza el contenido con Gemini usando el cliente LLM y un prompt específico.
    Contiene el prompt y la lógica de parseo y manejo de errores específica para el análisis.
    """
    # Definición del prompt específico para la tarea de análisis - Copiado exacto del original
    prompt = f"""
Evalúa este artículo sobre '{tema}' y devuelve SOLO un JSON válido con:
- "score": 1-10 (1=irrelevante, 10=excelente)
- "reason": Explicación concisa
- "resumen": Resumen breve (máx. 100 caracteres)
- "tags": 3-5 palabras clave relevantes

Criterios:
1. Relevancia: ¿Aborda directamente "{tema}"?
2. Autoridad: ¿Fuente confiable/citada?
3. Actualidad: ¿Menciona fechas recientes (2024-2025)?
4. Utilidad: ¿Contiene datos/ejemplos concretos?

Texto del artículo:
{text[:8000]}
"""

    try:
        # Usamos el cliente LLM para generar el texto crudo
        # Si generate_raw_content lanza una excepción, esta será capturada aquí
        response_text = llm_client.generate_raw_content(prompt)

        # Mantenemos la lógica original para extraer y parsear el JSON
        json_str_match = re.search(r'\{.*\}', response_text, re.DOTALL)

        if json_str_match:
            json_str = json_str_match.group()
            # Mantenemos la lógica original de parseo que puede lanzar JSONDecodeError
            return json.loads(json_str)
        else:
            # Si no se encuentra un JSON válido, manejamos como en el original
            print(f"⚠️ Gemini no retornó estructura JSON esperada para tema '{tema}'. Inicio respuesta: {response_text[:200]}...")
            # Retornamos el mismo diccionario de error por defecto del original
            return {"score": 1, "reason": "Error de análisis", "tags": []}

    except Exception as e:
        # Capturamos cualquier excepción (incluyendo la de generate_raw_content o json.loads)
        # Imprimimos el mensaje de error como en el original
        print(f"⚠️ Error en Gemini: {str(e)}")
        # Retornamos el mismo diccionario de error por defecto del original
        return {"score": 1, "reason": "Error de análisis", "tags": []}

