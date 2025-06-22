# models.py
# Define los modelos de datos (usando Pydantic) para la API de FastAPI.

from typing import List, Optional

from pydantic import BaseModel, Field  # Importa BaseModel y Field de pydantic

# --- Modelos de Datos para la Interfaz API ---

class GenerationParameters(BaseModel):
    """
    Modelo para los parámetros que controlan el proceso de generación de contenido.
    Estos parámetros se enviarán desde el frontend al endpoint /generate.
    """
    tema: str = Field(..., description="Tema o Sección para la generación del artículo.") # ... indica que es requerido
    num_fuentes_generador: int = Field(3, description="Número de fuentes a intentar usar para generar el artículo.") # 3 es el valor por defecto si no se pasa
    min_score_fuentes_generador: int = Field(7, description="Score mínimo requerido para que una fuente sea usada en la generación.")
    num_imagenes_buscar: int = Field(2, description="Número de imágenes candidatas a buscar para el artículo.")
    longitud: str = Field("media", description="Longitud estimada del artículo ('corta', 'media', 'larga').")
    tono: str = Field("neutral", description="Tono del artículo ('neutral', 'formal', 'informal', 'técnico').")
    # TODO: Considerar incluir aquí las plantillas de prompt si se envían con cada solicitud de generación
    # prompt_analyzer_template: Optional[str] = None
    # prompt_generator_template: Optional[str] = None
    # prompt_copilot_template: Optional[str] = None


class ArticleGeneratedResponse(BaseModel):
    """
    Modelo para la respuesta de un artículo generado por ID.
    Usado por el endpoint GET /articles/{article_id}.
    """
    id: int
    tema: str
    titulo: str
    meta_description: str
    body: str
    tags: List[str] # Pydantic puede manejar la conversión de JSON string a List
    fecha_generacion: str # Representar fecha/hora como string ISO 8601
    estado: str
    score_fuentes_promedio: Optional[float] = None
    #imagenes: List[ImageMetadataResponse] = Field(default_factory=list) # Lista de imágenes asociadas


class ImageMetadataResponse(BaseModel):
    """
    Modelo para la metadata de una imagen asociada a un artículo generado.
    Anidado dentro de ArticleGeneratedResponse.
    """
    id: int # Añadir ID si quieres retornarlo
    url: str
    alt_text: Optional[str] = None
    caption: Optional[str] = None
    licencia: Optional[str] = None
    autor: Optional[str] = None
    articulo_generado_id: int # FK


class ArticleListItem(BaseModel):
    """
    Modelo para la respuesta de la lista de artículos generados.
    Usado por el endpoint GET /articles.
    """
    id: int
    tema: str
    titulo: str
    fecha_generacion: str
    estado: str
    score_fuentes_promedio: Optional[float] = None


# TODO: Modelos para configuración (GET /config, PUT /config)
class ThemeConfiguration(BaseModel):
    """
    Modelo para la configuración persistente de un tema/sección.
    """
    tema: str = Field(..., description="Tema o Sección al que aplica esta configuración.", unique=True)
    min_score_fuente: int = Field(5, description="Score mínimo para fuentes en Fase 1.")
    num_fuentes_scraper: int = Field(10, description="Número de fuentes a buscar en Fase 1.")
    num_resultados_scraper: int = Field(5, description="Número de resultados analizados a considerar guardar en Fase 1.")
    min_score_generador: int = Field(7, description="Score mínimo para fuentes a usar en Fase 2.")
    num_fuentes_generador: int = Field(3, description="Número de fuentes a usar en Fase 2.")
    longitud_texto: str = Field("media", description="Longitud estimada por defecto.")
    tono_texto: str = Field("neutral", description="Tono por defecto.")
    num_imagenes_buscar: int = Field(2, description="Número de imágenes a buscar por defecto.")
    prompt_analyzer_template: Optional[str] = Field(None, description="Plantilla de prompt Analyzer (por defecto si es None).")
    prompt_generator_template: Optional[str] = Field(None, description="Plantilla de prompt Generator (por defecto si es None).")
    prompt_copilot_template: Optional[str] = Field(None, description="Plantilla de prompt Copilot (por defecto si es None).")
    # No incluir fechas o ID de DB aquí a menos que sea necesario para la UI


# TODO: Modelos para endpoints admin/explorar DB (opcional)
# class SourceItem(BaseModel):
#     id: int
#     titulo: str
#     url: str
#     score: int
#     fuente: str
#     fecha_scraping: str
#     usada_para_generar: bool # Usar bool para 0/1