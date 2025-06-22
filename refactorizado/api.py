# refactorizado/api.py
import database
import database as database
import orquestador as orquestador
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware  # Importa CORSMiddleware
from models import (ArticleGeneratedResponse, GenerationParameters,
                    ThemeConfiguration)

app = FastAPI()

# Configuración CORS
origins = [
    "http://localhost:8000",  # Reemplaza con el origen de tu frontend
    "http://localhost",
    # Puedes agregar otros orígenes aquí, por ejemplo:
    # "http://example.com",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],  # Permite todos los métodos (GET, POST, PUT, DELETE, OPTIONS, etc.)
    allow_headers=["*"],  # Permite todos los encabezados
)

@app.post("/generate", response_model=ArticleGeneratedResponse)
async def generate_article(params: GenerationParameters):
    """
    Endpoint para generar un artículo.

    Args:
        params (GenerationParameters): Parámetros de generación.

    Returns:
        ArticleGeneratedResponse: El artículo generado.
    """
    # TODO: Implementar la lógica del endpoint
    try:
        # 1. Cargar la configuración predefinida para el tema
        #    (Usar database.get_theme_config(params.tema))
        # 2. Combinar los parámetros recibidos con la configuración predefinida
        #    (Sobrescribiendo los valores predefinidos con los recibidos)
        # 3. Llamar al orquestador.procesar_tema()
        # 4. Retornar el resultado (o un error si algo falla)
        try:
            theme_config: ThemeConfiguration = database.get_theme_config(params.tema)
            # TODO: Implementar la combinación de parámetros y configuración
            # combined_params = ...
            # result = orquestador.procesar_tema(combined_params)
            # return result
            return ArticleGeneratedResponse(
                id=1,
                tema=params.tema,
                titulo="Título de ejemplo",
                meta_description="Descripción de ejemplo",
                body="Cuerpo del artículo de ejemplo",
                tags=["tag1", "tag2"],
            fecha_generacion="2024-01-01",
            estado="generado",
        )  # Reemplazar con la lógica real
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error al obtener la configuración del tema: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/config/{tema}", response_model=ThemeConfiguration)
async def get_theme_config(tema: str):
    """
    Endpoint para obtener la configuración de un tema.

    Args:
        tema (str): El nombre del tema.

    Returns:
        ThemeConfiguration: La configuración del tema.
    """
    try:
        config = database.get_theme_config(tema)
        return config
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Configuración del tema '{tema}' no encontrada")

@app.put("/config/{tema}", response_model=ThemeConfiguration)
async def update_theme_config(tema: str, config: ThemeConfiguration):
    """
    Endpoint para actualizar la configuración de un tema.

    Args:
        tema (str): El nombre del tema.
        config (ThemeConfiguration): La nueva configuración del tema.

    Returns:
        ThemeConfiguration: La configuración actualizada del tema.
    """
    try:
        updated_config = database.update_theme_config(tema, config)
        return updated_config
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"No se pudo actualizar la configuración del tema '{tema}': {str(e)}")

# TODO: Implementar endpoints para:
# - GET /config/{tema}: Obtener la configuración de un tema.
# - PUT /config/{tema}: Actualizar la configuración de un tema.
