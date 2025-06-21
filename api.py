# api.py
# Backend API para el Asistente de Contenido Inteligente (SEO-Copilot).
# Expone endpoints para disparar la generación completa, gestionar configuración,
# listar y obtener artículos/fuentes.
# **Versión simplificada sin manejo de errores detallado y con importaciones directas para hackathon.**

import json
import os
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

import refactorizado.database as database
from refactorizado.content_generator import generate_seo_content
from refactorizado.mock_publisher import publish_to_html
from refactorizado.scraper import buscar_noticias
from refactorizado.web_tools import find_free_images

print(">>> API: Módulos importados directamente <<<")


# --- Lifespan para inicializar la DB al inicio de la aplicación ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Función de ciclo de vida para inicializar recursos al iniciar la aplicación FastAPI.
    Inicializa la base de datos. Si falla, la aplicación se romperá aquí al inicio.
    """
    print("🌐 Iniciando API: Ejecutando lifespan startup event...")
    # Inicializar la base de datos. Si falla, la aplicación se romperá aquí al inicio.
    database.inicializar_db()
    print("✅ Base de datos inicializada.")

    yield # La aplicación correrá hasta que la función lifespan retorne

    # Código para ejecutar al cerrar la aplicación (opcional)
    print("Shutting down API...")


# --- Inicializar FastAPI con lifespan ---
app = FastAPI(
    title="SEO-Copilot API",
    description="Backend API para el Asistente de Contenido Inteligente (SEO-Copilot).",
    version="0.1.0",
    lifespan=lifespan # Asociar el lifespan con la aplicación
)

# --- Configurar CORS ---
origins = ["*"]  # Permitir todos los orígenes para la hackathon. Ajustar en producción.
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],  # Permitir GET, POST, PUT, DELETE, etc.
    allow_headers=["*"],  # Permitir cualquier header
)


# --- Endpoint Raíz ---
@app.get("/")
async def read_root():
    """
    Endpoint raíz que retorna un mensaje de bienvenida y enlace a docs.
    """
    print(">>> API: Recibida solicitud GET /")
    return {"message": "SEO-Copilot API is running", "docs_url": "/docs"}


# --- POST /generate ---
@app.post("/generate")
async def generate_article_endpoint(request: Request):
    """
    Inicia el pipeline completo de generación de contenido para un tema/sección.
    Busca fuentes, analiza, genera texto, busca imágenes, guarda todo en DB, marca fuentes.
    **Simplificado: Si falla, se romperá.**
    """
    print("\n>>> API: Recibida solicitud POST /generate <<<")
    request_data: Dict[str, Any] = await request.json()

    # Validar la entrada manualmente
    tema = request_data.get('tema')
    if not isinstance(tema, str) or not tema:
        print(">>> API: Error de validación en POST /generate: 'tema' inválido o faltante")
        raise HTTPException(status_code=400, detail="Invalid input: 'tema' must be a non-empty string")

    print(f">>> API: Generando artículo para el tema: '{tema}'")

    generated_article_id = None # Para almacenar el ID del artículo generado
    generated_article_data = None # Asegurar que está definido

    # --- Obtener configuración para el tema (guardada o por defecto) ---
    # get_config retorna {} si no encuentra config guardada. Los módulos deben manejar defaults.
    # Si falla database.get_config, se romperá aquí.
    config = database.get_config(tema)
    print(f">>> API: Configuración para '{tema}' cargada (encontrada en DB: {bool(config)}).")

    # --- Fase 1: Buscar, Analizar, Guardar Fuentes ---
    print("\n   >>> API: Iniciando Fase 1: Búsqueda y Análisis de Fuentes...")
    # Llamar a scraper.buscar_noticias solo con el tema. Asumir que carga su propia config/defaults.
    # Si falla scraper.buscar_noticias o analyzer o llm_client, se romperá aquí.
    fuentes_analizadas = buscar_noticias(tema) # <-- Llamada asumiendo firma actual

    if fuentes_analizadas:
        print(f"   ✅ Fase 1: Encontradas {len(fuentes_analizadas)} fuentes analizadas. Guardando fuentes...")
        for fuente_meta in fuentes_analizadas:
            # Guardar fuentes encontradas. Si database.guardar_articulo falla, se romperá aquí.
            database.guardar_articulo(fuente_meta) # guardar_articulo ya maneja duplicados
    else:
         print("   ⚠️ Fase 1: No se encontraron fuentes analizadas con score >= 5 o hubo errores en el scraper.")


    # --- Fase 2: Generación de Contenido y Post-procesamiento ---
    print("\n   >>> API: Iniciando Fase 2: Generación de Contenido...")
    # Llamar a content_generator.generate_seo_content solo con el tema/topic.
    # Asumir que carga su propia config/defaults (longitud, tono, prompts).
    # Si falla content_generator.generate_seo_content, se romperá aquí.
    generated_article_data = generate_seo_content(tema) # <-- Llamada asumiendo firma actual

    # --- Verificar si la generación de texto fue exitosa ---
    if generated_article_data:
        print("   ✅ Fase 2: Artículo generado por IA.")
        # Asegurarse de que 'tema' está correctamente en los datos del artículo antes de guardar
        if 'tema' not in generated_article_data or not generated_article_data['tema']:
            generated_article_data['tema'] = tema # Añadir tema si falta
            print(f"   ⚠️ Campo 'tema' faltante o vacío en datos generados. Añadiendo '{tema}'.")


        # Guardar artículo generado en DB. Si database.save_generated_article falla, se romperá aquí.
        print("   💾 Intentando guardar artículo generado en DB...")
        # save_generated_article retorna el ID o None. Si retorna None, la siguiente condición fallará.
        generated_article_id = database.save_generated_article(generated_article_data) # Save generated article FIRST to get ID

        # --- Continuar solo si el artículo generado se guardó con éxito (ID válido) ---
        if generated_article_id:
             print(f"   ✅ Artículo generado guardado con ID {generated_article_id}.")

             # Buscar y guardar imágenes. Si falla web_tools.find_free_images o database.save_image_metadata, se romperá aquí.
             # num_results debe venir de config o defaults. Asumimos web_tools lo maneja o usamos default aquí
             num_imagenes_buscar = config.get('num_imagenes_buscar', 2) # Usar num_imagenes_buscar de la config cargada o default si config es {}
             print(f"\n   🖼️ Buscando y guardando imágenes ({num_imagenes_buscar})...")

             image_search_query = generated_article_data.get('title', tema)
             tags_list = generated_article_data.get('tags', [])
             if isinstance(tags_list, list) and tags_list:
                 image_search_query += " " + " ".join(tags_list)
             image_search_query = image_search_query[:150].strip()

             imagenes_encontradas = find_free_images(image_search_query, num_results=num_imagenes_buscar) # <-- Llamada con num_results

             if imagenes_encontradas:
                  print(f"   💾 Guardando metadata de {len(imagenes_encontradas)} imágenes encontradas en DB...")
                  # Verificar de nuevo si el ID generado es válido antes de asociar imágenes
                  # Esta verificación es un poco redundante aquí porque ya estamos dentro del `if generated_article_id:`
                  # Pero la mantengo por si acaso la función save_generated_article tiene un comportamiento inesperado.
                  if generated_article_id is not None:
                      for img_meta in imagenes_encontradas:
                          # save_image_metadata espera 'articulo_generado_id' en el diccionario
                          img_meta['articulo_generado_id'] = generated_article_id
                          database.save_image_metadata(img_meta) # Si falla, se romperá aquí.
                  else:
                       print("   ⚠️ No se pudo obtener generated_article_id. No se guardará metadata de imágenes.")


             # Marcar fuentes utilizadas. Si database.mark_source_used falla, se romperá aquí.
             print("\n   🔄 Marcando fuentes utilizadas como usadas...")
             # Asumiendo generate_seo_content añade 'fuente_ids_usadas' a los datos retornados
             source_ids_actually_used = generated_article_data.get('fuente_ids_usadas', [])
             if source_ids_actually_used:
                 for source_id in source_ids_actually_used:
                     database.mark_source_used(source_id) # Si falla, se romperá aquí.
                 print(f"   ✅ {len(source_ids_actually_used)} fuentes marcadas como usadas.")
             else:
                  print("   ⚠️ No se obtuvieron IDs de fuentes utilizadas del artículo generado. No se marcará ninguna como usada.")


             # Simular Publicación (Generar HTML para previsualización). Si mock_publisher.publish_to_html falla, se romperá aquí.
             print("\n   🚀 Llamando a mock_publisher (HTML local)...")
             # Mock publisher needs article_data and images data
             # Usamos la lista de imágenes encontradas (metadata)
             publish_to_html(generated_article_data, image_data=imagenes_encontradas)
             print("   ✅ mock_publisher llamado.")


        else: # Si database.save_generated_article retornó None
            print(f"❌ Falló el guardado del artículo generado en la base de datos para tema '{tema}'. Pipeline detenido.")
            # Lanzamos una excepción para que el frontend sepa que algo salió mal
            raise HTTPException(status_code=500, detail=f"Failed to save generated article for theme '{tema}'")


    else: # Si content_generator.generate_seo_content devolvió None
        print(f"❌ La generación de contenido (texto) falló para tema '{tema}'. Pipeline detenido.")
        # Lanzamos una excepción para que el frontend sepa que algo salió mal
        raise HTTPException(status_code=500, detail=f"Content generation failed for theme '{tema}'")


    print(f"\n>>> API: Pipeline COMPLETO para '{tema}' finalizado exitosamente. Artículo ID: {generated_article_id} <<<")
    # Retornar el ID del artículo generado para que el frontend pueda cargarlo en el Canvas
    return {"message": "Generation pipeline completed successfully", "article_id": generated_article_id}


# --- GET /config/{tema} ---
@app.get("/config/{tema}")
async def get_config_endpoint(tema: str):
    """
    Endpoint para obtener la configuración guardada o por defecto para un tema.
    """
    if not isinstance(tema, str) or not tema:
        raise HTTPException(status_code=400, detail="Invalid path parameter: 'tema' must be a non-empty string")
    print(f"\n>>> API: Recibida solicitud GET /config/{tema} para tema: '{tema}' <<<")
    config = database.get_config(tema) # get_config retorna {} si no encuentra. Si falla, se romperá.
    print(f"✅ API: Retornando configuración para tema '{tema}'. Encontrada en DB: {bool(config)}")
    return config # Retorna el dict encontrado o {}


# --- PUT /config ---
@app.put("/config")
async def update_config_endpoint(request: Request):
    """
    Endpoint para guardar o actualizar la configuración para un tema.
    Payload debe ser un diccionario con campos de configuración e incluir 'tema'.
    **Simplificado: Si falla, se romperá.**
    """
    print("\n>>> API: Recibida solicitud PUT /config <<<")
    config_data: Dict[str, Any] = await request.json()

    # Validar la entrada manualmente
    tema = config_data.get('tema')
    if not isinstance(tema, str) or not tema:
        print(">>> API: Error de validación en PUT /config: 'tema' inválido o faltante en payload")
        raise HTTPException(status_code=400, detail="Invalid input: 'tema' must be a non-empty string in payload")

    print(f">>> API: Recibida solicitud para guardar configuración para tema: '{tema}' <<<")
    # Llamar a database.save_config directamente con el dict recibido. Si falla, se romperá.
    database.save_config(config_data) # database.save_config ya valida campos válidos y tema
    print(f"✅ API: Configuración para '{tema}' guardada con éxito.")
    return {"message": "Configuration saved successfully"}


# --- GET /articles ---
@app.get("/articles")
async def list_articles_endpoint(tema: Optional[str] = None, estado: Optional[str] = None):
    """
    Endpoint para obtener todos los artículos generados, opcionalmente filtrados por tema o estado.
    """
    print(f"\n>>> API: Recibida solicitud GET /articles (Tema: {tema}, Estado: {estado}) <<<")
    # database.get_all_generated_articles ya acepta tema y estado como Optional. Si falla, se romperá.
    articles = database.get_all_generated_articles(tema=tema, estado=estado)
    print(f"✅ API: Retornando {len(articles)} artículos generados.")
    return articles


# --- GET /articles/{article_id} ---
@app.get("/articles/{article_id}")
async def get_article_endpoint(article_id: int):
    """
    Endpoint para obtener detalles completos de un artículo generado, incluyendo imágenes asociadas.
    """
    print(f"\n>>> API: Recibida solicitud GET /articles/{article_id} <<<")
    # database.get_generated_article_by_id retorna dict o None. Si falla, se romperá.
    article = database.get_generated_article_by_id(article_id)
    if article:
        print(f"✅ API: Retornando detalles para artículo ID {article_id}.")
        # database.get_generated_article_by_id ya debería convertir tags a lista
        return article
    else:
        print(f">>> API: Artículo con ID {article_id} no encontrado.")
        raise HTTPException(status_code=404, detail="Article not found")


# --- PUT /articles/{article_id} ---
@app.put("/articles/{article_id}")
async def update_article_endpoint(article_id: int, request: Request):
    """
    Endpoint para actualizar campos de un artículo generado (título, meta, body, tags, estado).
    Payload debe ser un diccionario con los campos a actualizar.
    **Simplificado: Si falla, se romperá.**
    """
    print(f"\n>>> API: Recibida solicitud PUT /articles/{article_id} <<<")
    updated_data: Dict[str, Any] = await request.json()

    # Validar la entrada manualmente
    if not isinstance(updated_data, dict) or not updated_data:
        print(f">>> API: Error de validación en PUT /articles/{article_id}: datos de actualización inválidos o vacíos")
        raise HTTPException(status_code=400, detail="Invalid input: request body must be a non-empty dictionary")

    # database.update_generated_article ya maneja la conversion de tags si se le pasa lista.
    # database.update_generated_article ya valida los campos permitidos y el ID. Si falla, se romperá.
    print(f">>> API: Actualizando artículo ID {article_id} con campos: {list(updated_data.keys())}")
    success = database.update_generated_article(article_id, updated_data)

    if success:
        print(f"✅ API: Artículo ID {article_id} actualizado con éxito.")
        return {"message": "Article updated successfully"}
    else:
        # Si database.update_generated_article retorna False (ej: ID no encontrado o fallo DB)
        print(f">>> API: Falló al actualizar el artículo con ID {article_id}. database.update_generated_article retornó False.")
        # En una versión robusta, verificar si el artículo existe primero para dar 404 si no.
        # Aquí, asumimos que False para un ID válido significa un error DB o validación interna fallida.
        raise HTTPException(status_code=500, detail=f"Failed to update article with ID {article_id}")


# --- POST /chat ---
# Este endpoint existe pero su lógica de Copiloto está marcada como TODO
# No hay manejo de errores detallado dentro de la lógica mock.
@app.post("/chat")
async def chat_with_copilot_endpoint(request: Request):
    """
    Endpoint para interactuar con el SEO-Copilot conversacional.
    Lógica de Copiloto es TODO.
    **Simplificado: Si falla el parsing JSON, se romperá. Lógica interna es mock.**
    """
    print("\n>>> API: Recibida solicitud POST /chat <<<")
    chat_request_data: Dict[str, Any] = await request.json()

    # Validar la entrada manualmente (mensaje y contexto)
    user_message = chat_request_data.get('user_message')
    article_id = chat_request_data.get('article_id')
    tema = chat_request_data.get('tema')

    if not isinstance(user_message, str) or not user_message:
         print(">>> API: Error de validación en POST /chat: 'user_message' inválido o faltante")
         raise HTTPException(status_code=400, detail="Invalid input: 'user_message' must be a non-empty string")
    # Requiere article_id O un tema válido para contexto
    if article_id is None and (not isinstance(tema, str) or not tema):
        print(">>> API: Error de validación en POST /chat: se requiere 'article_id' o 'tema' válido para contexto")
        raise HTTPException(status_code=400, detail="Invalid input: must provide either 'article_id' or a non-empty 'tema' for context.")

    print(f">>> API: Mensaje de chat recibido para contexto (ArtID: {article_id}, Tema: {tema}): '{user_message}'")

    # --- TODO: Implementar la lógica real del Copiloto en copilot.py ---
    # Cargar contexto completo (articulo, config) y llamar a copilot.process_chat_message
    # Por ahora, simplemente retornamos una respuesta mock.
    copilot_response_text = "SEO-Copilot (mock) recibió tu mensaje. La lógica real se implementará pronto."
    if article_id is not None:
         copilot_response_text += f" Contexto: Artículo ID {article_id}."
    elif tema:
         copilot_response_text += f" Contexto: Tema '{tema}'."
    copilot_response_text += f" Mensaje: '{user_message}'"
    # --- Fin respuesta mock ---

    print(f"✅ API: Retornando respuesta mock del chat: '{copilot_response_text[:100]}...'")
    return {"response": copilot_response_text}


# --- GET /admin/sources ---
@app.get("/admin/sources")
async def list_sources_endpoint():
    """
    Endpoint para obtener todos los artículos fuente scrapeados.
    """
    print("\n>>> API: Recibida solicitud GET /admin/sources <<<")
    # database.get_all_sources() asumiendo que acepta 0 args
    sources = database.et_all_sources()
    print(f"✅ API: Retornando {len(sources)} fuentes.")
    return sources


# --- GET /temas-secciones ---
@app.get("/temas-secciones")
async def list_temas_secciones_endpoint():
    """
    Endpoint para obtener los temas/secciones disponibles (con configuración guardada).
    """
    print("\n>>> API: Recibida solicitud GET /temas-secciones <<<")
    # database.get_available_temas_secciones() asumiendo que acepta 0 args
    temas = database.get_available_temas_secciones()
    print(f"✅ API: Retornando {len(temas)} temas/secciones con configuración.")
    return temas

# TODO: Añadir otros endpoints si son necesarios (ej: eliminar artículo/fuente, etc.)
