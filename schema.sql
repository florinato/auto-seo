
PRAGMA foreign_keys = ON; -- Asegurar que las claves foráneas están activadas

-- Tabla para los artículos fuente (noticias scrapeadas)
CREATE TABLE IF NOT EXISTS articulos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    titulo TEXT NOT NULL,
    url TEXT UNIQUE NOT NULL,
    score INTEGER CHECK (score BETWEEN 1 AND 10),
    resumen TEXT,
    fuente TEXT,
    fecha_publicacion_fuente TEXT, -- Renombrado para claridad
    fecha_scraping TEXT DEFAULT CURRENT_TIMESTAMP,
    usada_para_generar INTEGER DEFAULT 0 -- Nuevo campo (0=No, 1=Sí)
);

-- Tabla para los tags (pueden ser usados por fuentes o generados)
CREATE TABLE IF NOT EXISTS tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tag TEXT UNIQUE
);

-- Relación many-to-many entre artículos fuente y tags
CREATE TABLE IF NOT EXISTS articulos_fuente_tags ( -- Renombrada para claridad
    articulo_fuente_id INTEGER,
    tag_id INTEGER,
    FOREIGN KEY (articulo_fuente_id) REFERENCES articulos(id),
    FOREIGN KEY (tag_id) REFERENCES tags(id),
    PRIMARY KEY (articulo_fuente_id, tag_id)
);

-- Nueva Tabla para los artículos GENERADOS por la IA
CREATE TABLE IF NOT EXISTS articulos_generados (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tema TEXT NOT NULL,
    titulo TEXT NOT NULL,
    meta_description TEXT,
    body TEXT, -- El contenido completo del artículo
    tags TEXT, -- Guardar tags como texto (ej: JSON o coma-separado)
    fecha_generacion TEXT DEFAULT CURRENT_TIMESTAMP,
    fecha_publicacion_destino TEXT, -- Fecha en que se publicó en el blog destino
    estado TEXT DEFAULT 'generado', -- 'generado', 'pendiente_revision', 'publicado', 'descartado'
    score_fuentes_promedio REAL -- Opcional: score promedio de las fuentes usadas
);

-- Nueva Tabla para las imágenes asociadas a artículos GENERADOS
CREATE TABLE IF NOT EXISTS imagenes_generadas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    articulo_generado_id INTEGER NOT NULL, -- Clave foránea al artículo generado
    url TEXT NOT NULL, -- URL o path de la imagen
    alt_text TEXT,
    caption TEXT,
    licencia TEXT,
    autor TEXT,
    FOREIGN KEY (articulo_generado_id) REFERENCES articulos_generados(id)
);

-- Nueva Tabla: Configuracion por Tema y Prompts
CREATE TABLE IF NOT EXISTS configuracion (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tema TEXT UNIQUE NOT NULL, -- El TEMA al que aplica esta configuración
    min_score_fuente INTEGER DEFAULT 5, -- Score mínimo para fuentes en Fase 1 (Scraper)
    num_fuentes_scraper INTEGER DEFAULT 10, -- Cuántas fuentes intentar buscar en Fase 1
    num_resultados_scraper INTEGER DEFAULT 5, -- Cuántas fuentes analizar y considerar guardar en Fase 1
    min_score_generador INTEGER DEFAULT 7, -- Score mínimo para fuentes a USAR en Fase 2 (Generador)
    num_fuentes_generador INTEGER DEFAULT 3, -- Cuántas fuentes USAR en Fase 2
    longitud_texto TEXT DEFAULT 'media', -- 'corta', 'media', 'larga' para el generador
    tono_texto TEXT DEFAULT 'neutral', -- 'formal', 'informal', etc. para el generador
    num_imagenes_buscar INTEGER DEFAULT 2, -- Cuántas imágenes buscar para el generado
    -- Plantillas de Prompt (TEXT para almacenar strings largos)
    prompt_analyzer_template TEXT, -- Plantilla para el prompt de análisis de fuentes
    prompt_generator_template TEXT, -- Plantilla para el prompt de generación de texto
    prompt_copilot_template TEXT, -- Plantilla base para la conversación con el Copiloto
    -- Otros campos de configuración específicos que puedan surgir
    fecha_creacion TEXT DEFAULT CURRENT_TIMESTAMP,
    fecha_actualizacion TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Nueva Tabla para gestionar las tareas de generación de contenido
CREATE TABLE IF NOT EXISTS generacion_tareas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tema TEXT NOT NULL,
    estado TEXT NOT NULL DEFAULT 'pendiente', -- 'pendiente', 'en_progreso', 'completado', 'error'
    configuracion_id INTEGER, -- Opcional, para asociar una config específica si no se usa la del tema
    articulo_generado_id INTEGER, -- Para enlazar con el artículo una vez generado
    mensaje_error TEXT, -- Para guardar detalles si la tarea falla
    fecha_solicitud TEXT DEFAULT CURRENT_TIMESTAMP,
    fecha_actualizacion TEXT DEFAULT CURRENT_TIMESTAMP, -- Para rastrear cuándo se actualizó el estado
    fecha_finalizacion TEXT,
    FOREIGN KEY (configuracion_id) REFERENCES configuracion(id),
    FOREIGN KEY (articulo_generado_id) REFERENCES articulos_generados(id)
);