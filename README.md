# xplagiax_sourcex
data source research services

# 1. Construir
docker-compose up --build

# 2. Probar
curl -X POST http://localhost:5000/api/similarity-search \
  -H "Content-Type: application/json" \
  -d '{
    "data": [
      "machine learning",
      "en",
      [
        ["page1", "para1", "Neural networks are computational models"],
        ["page1", "para2", "Deep learning uses multiple layers"]
      ]
    ]
  }'

# 3. Ver estadísticas FAISS
curl http://localhost:5000/api/faiss/stats


# Búsqueda básica
curl -X POST http://localhost:5000/api/similarity-search \
  -H "Content-Type: application/json" \
  -d '{
    "data": [
      "machine learning",
      "en",
      [
        ["page1", "para1", "Neural networks are computational models inspired by biological neurons"],
        ["page1", "para2", "Deep learning uses multiple layers to extract features"],
        ["page2", "para1", "Convolutional networks excel at image recognition tasks"]
      ]
    ]
  }'

# Búsqueda con fuentes específicas
curl -X POST http://localhost:5000/api/similarity-search \
  -H "Content-Type: application/json" \
  -d '{
    "data": [
      "artificial intelligence",
      "en",
      [
        ["page1", "para1", "AI systems can learn from data"]
      ]
    ],
    "sources": ["semantic_scholar", "arxiv", "pubmed"]
  }'

# Búsqueda sin FAISS (solo APIs)
curl -X POST http://localhost:5000/api/similarity-search \
  -H "Content-Type: application/json" \
  -d '{
    "data": [
      "quantum computing",
      "en",
      [
        ["page1", "para1", "Quantum computers use qubits"]
      ]
    ],
    "use_faiss": false
  }'

# Búsqueda en español
curl -X POST http://localhost:5000/api/similarity-search \
  -H "Content-Type: application/json" \
  -d '{
    "data": [
      "aprendizaje automático",
      "es",
      [
        ["pagina1", "parrafo1", "Las redes neuronales son modelos computacionales"],
        ["pagina1", "parrafo2", "El aprendizaje profundo utiliza múltiples capas"]
      ]
    ]
  }'


# Búsqueda simple
curl -X POST http://localhost:5000/api/faiss/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "deep learning neural networks"
  }'

# Búsqueda con parámetros personalizados
curl -X POST http://localhost:5000/api/faiss/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "convolutional neural networks image recognition",
    "k": 20,
    "threshold": 0.75
  }'



  ┌─────────────────────────────────────────────────────────────────┐
│ USUARIO ENVÍA REQUEST                                           │
│ POST /api/similarity-search                                     │
│ {                                                               │
│   "data": [                                                     │
│     "machine learning",                                         │
│     "en",                                                       │
│     [                                                           │
│       ["page1", "para1", "Neural networks are models"],        │
│       ["page1", "para2", "Deep learning uses layers"]          │
│     ]                                                           │
│   ]                                                             │
│ }                                                               │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ PASO 1: Flask recibe el request                                │
│ Archivo: app.py línea 43                                       │
│ Función: @app.route('/api/similarity-search')                  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ PASO 2: Validación de datos                                    │
│ Archivo: app.py líneas 51-77                                   │
│                                                                 │
│ ✓ Verifica que exista campo 'data'                            │
│ ✓ Extrae: theme = "machine learning"                          │
│ ✓ Extrae: idiom = "en"                                        │
│ ✓ Extrae: texts = [[page, para, text], ...]                  │
│ ✓ Extrae: sources = None (opcional)                           │
│ ✓ Extrae: use_faiss = True (default)                          │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ PASO 3: Llama al procesador principal                          │
│ Archivo: app.py línea 80                                       │
│                                                                 │
│ process_similarity_batch(                                       │
│   texts,              # Los párrafos a buscar                  │
│   theme,              # "machine learning"                     │
│   idiom,              # "en"                                   │
│   redis_client,       # Para caché                             │
│   http_client,        # Para APIs                              │
│   rate_limiter,       # Control de rate limits                 │
│   sources,            # APIs a usar                            │
│   use_faiss           # Si usar FAISS o no                     │
│ )                                                               │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ PASO 4: Inicio del procesamiento batch                         │
│ Archivo: search_service.py línea 49                            │
│ Función: process_similarity_batch()                            │
│                                                                 │
│ • Inicia timer para métricas                                   │
│ • Verifica salud del índice FAISS                             │
│ • Agrupa textos únicos (deduplicación)                        │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ PASO 5: Preprocesamiento de textos                            │
│ Archivo: search_service.py líneas 61-80                       │
│                                                                 │
│ Para cada texto:                                               │
│   1. preprocess_text_cached()                                  │
│      • Convierte a minúsculas                                  │
│      • Elimina caracteres especiales                           │
│      • Normaliza espacios                                      │
│                                                                 │
│   Entrada: "Neural networks are computational Models!"         │
│   Salida: "neural networks are computational models"           │
│                                                                 │
│   2. remove_stopwords_optimized()                              │
│      • Tokeniza el texto                                       │
│      • Elimina palabras comunes (are, the, is...)             │
│                                                                 │
│   Entrada: "neural networks are computational models"          │
│   Salida: "neural networks computational models"               │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ PASO 6: Verificar caché Redis                                  │
│ Archivo: search_service.py línea 70                            │
│                                                                 │
│ • Genera clave única: hash(theme + idiom + texto)             │
│ • Busca en Redis: "search:abc123..."                          │
│                                                                 │
│ SI ENCUENTRA en caché:                                         │
│   → Retorna resultados inmediatamente ✅                       │
│   → Salta al PASO 14                                           │
│                                                                 │
│ SI NO ENCUENTRA:                                               │
│   → Continúa al PASO 7 ⏬                                       │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ PASO 7: Búsqueda en FAISS (si disponible)                     │
│ Archivo: search_service.py líneas 85-100                      │
│                                                                 │
│ SI FAISS tiene papers indexados:                               │
│   1. Llama a faiss_index.search_batch()                       │
│      • Genera embeddings de las queries                        │
│      • Busca vectores similares en el índice                   │
│      • Retorna top 20 por query                                │
│                                                                 │
│   Ejemplo:                                                      │
│   Query: "neural networks computational models"                │
│   ↓                                                             │
│   Embedding: [0.12, -0.45, 0.78, ..., 0.34] (384 dims)       │
│   ↓                                                             │
│   FAISS busca vectores similares                               │
│   ↓                                                             │
│   Encuentra:                                                    │
│     - "Deep Learning Book" (89.2% match)                       │
│     - "Neural Network Basics" (85.7% match)                    │
│     - "CNN Tutorial" (82.1% match)                             │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ PASO 8: Evaluar resultados de FAISS                           │
│ Archivo: search_service.py líneas 102-122                     │
│                                                                 │
│ Para cada query:                                               │
│   SI encontró ≥5 resultados en FAISS:                         │
│     → Convierte a SearchResult                                 │
│     → Guarda en caché                                          │
│     → Marca como "completo" ✅                                 │
│                                                                 │
│   SI encontró <5 resultados:                                   │
│     → Marca para buscar en APIs 🌐                            │
│     → Continúa al PASO 9 ⏬                                    │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ PASO 9: Búsqueda en APIs externas (si es necesario)             │
│ Archivo: search_service.py línea 127                            │
│ Función: search_all_sources()                                   │
│                                                                 │
│ Busca en PARALELO en todas las APIs:                            │
│   • Crossref                                                    │
│   • PubMed                                                      │
│   • Semantic Scholar                                            │
│   • arXiv                                                       │
│   • OpenAlex                                                    │
│   • Europe PMC                                                  │
│   • DOAJ                                                        │
│   • Zenodo                                                      │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ PASO 10: Detalle de búsqueda en UNA API (ej: Semantic Scholar)  │
│ Archivo: searchers.py línea 112                                 │
│ Función: search_semantic_scholar()                              │
│                                                                 │
│ 1. Verifica rate limit (100 req/min)                            │
│    SI excede límite → Retorna [] vacío                          │
│                                                                 │
│ 2. Construye request HTTP:                                      │
│    GET https://api.semanticscholar.org/graph/v1/paper/search    │
│    params: {                                                    │
│      query: "machine learning neural networks models",          │
│      limit: 5,                                                  │
│      fields: "title,abstract,authors,publicationTypes"          │
│    }                                                            │
│                                                                 │
│ 3. Espera respuesta (timeout 8s)                                │
│                                                                 │
│ 4. Parsea JSON:                                                 │
│    {                                                            │
│      "data": [                                                  │
│        {                                                        │
│          "title": "Deep Learning",                              │
│          "abstract": "This paper presents...",                  │
│          "authors": [{"name": "Goodfellow"}],                   │
│          "publicationTypes": ["JournalArticle"]                 │
│        },                                                       │
│        ...                                                      │
│      ]                                                          │
│    }                                                            │
│                                                                 │
│ 5. Retorna lista de papers:                                     │
│    [                                                            │
│      {                                                          │
│        "title": "Deep Learning",                                │
│        "abstract": "This paper presents...",                    │
│        "author": "Goodfellow",                                  │
│        "type": "JournalArticle"                                 │
│      }                                                          │
│    ]                                                            │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ PASO 11: Agregar papers nuevos a FAISS                        │
│ Archivo: search_service.py líneas 133-148                     │
│                                                                 │
│ Para cada paper encontrado en APIs:                            │
│   1. Extrae abstract                                           │
│   2. Genera metadata:                                          │
│      {                                                          │
│        "title": "Deep Learning",                               │
│        "author": "Goodfellow",                                 │
│        "abstract": "This paper...",                            │
│        "source": "semantic_scholar",                           │
│        "type": "JournalArticle"                                │
│      }                                                          │
│                                                                 │
│   3. Llama a faiss_index.add_papers()                         │
│      • Genera embeddings de abstracts                          │
│      • Los normaliza (L2)                                      │
│      • Los agrega al índice FAISS                             │
│      • Guarda metadata asociada                                │
│                                                                 │
│ RESULTADO: Papers quedan guardados para futuras búsquedas 💾  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ PASO 12: Calcular similitud con embeddings                    │
│ Archivo: search_service.py línea 151                          │
│ Función: calculate_similarities_batch()                        │
│                                                                 │
│ 1. Preprocesa abstracts de papers encontrados                 │
│    Abstract: "This paper presents deep learning methods..."    │
│    →                                                            │
│    Procesado: "paper presents deep learning methods"           │
│                                                                 │
│ 2. Genera embeddings en BATCH (rápido):                       │
│    Query: [0.12, -0.45, 0.78, ..., 0.34]                     │
│    Papers: [                                                   │
│      [0.15, -0.42, 0.81, ..., 0.31],  ← Paper 1              │
│      [0.08, -0.52, 0.65, ..., 0.29],  ← Paper 2              │
│      [-0.20, 0.15, -0.10, ..., 0.45]  ← Paper 3              │
│    ]                                                            │
│                                                                 │
│ 3. Calcula similitud coseno (NumPy vectorizado):              │
│    similarities = cosine_similarity(query, papers)             │
│    → [0.892, 0.857, 0.234]  # Paper 1=89%, Paper 2=85%, ...  │
│                                                                 │
│ 4. Filtra por threshold (70%):                                │
│    Papers con similitud ≥70%:                                 │
│      ✅ Paper 1: 89.2%                                         │
│      ✅ Paper 2: 85.7%                                         │
│      ❌ Paper 3: 23.4% (descartado)                           │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ PASO 13: Construir objetos SearchResult                       │
│ Archivo: search_service.py líneas 153-168                     │
│                                                                 │
│ Para cada paper con similitud ≥70%:                           │
│   SearchResult(                                                │
│     fuente = "semantic_scholar",                               │
│     texto_original = "Neural networks are models",             │
│     texto_encontrado = "This paper presents deep...",          │
│     porcentaje_match = 89.2,                                   │
│     documento_coincidente = "Deep Learning Book",              │
│     autor = "Goodfellow",                                      │
│     type_document = "JournalArticle"                           │
│   )                                                             │
│                                                                 │
│ • Ordena por similitud (descendente)                          │
│ • Toma top 10 por query                                       │
│ • Guarda en caché Redis                                       │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ PASO 14: Guardar índice FAISS actualizado                     │
│ Archivo: search_service.py línea 175                          │
│                                                                 │
│ • Llama a faiss_index.save()                                   │
│ • Guarda índice en: data/faiss_index.index                    │
│ • Guarda metadata en: data/faiss_index_metadata.pkl           │
│                                                                 │
│ AHORA los nuevos papers están disponibles para próximas       │
│ búsquedas sin necesidad de llamar APIs otra vez 🚀            │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ PASO 15: Calcular métricas de performance                     │
│ Archivo: search_service.py líneas 179-183                     │
│                                                                 │
│ elapsed = tiempo_final - tiempo_inicial                        │
│ throughput = textos_procesados / elapsed                       │
│                                                                 │
│ Imprime:                                                         │
│   ⚡ Procesamiento completado en 2.34s                          │
│   📈 Throughput: 4.3 textos/s                                   │
│   💾 FAISS: 1523 papers indexados                               │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ PASO 16: Retornar al endpoint Flask                             │
│ Archivo: search_service.py línea 185                            │
│                                                                 │
│ Retorna lista de SearchResult:                                  │
│   [                                                             │
│     SearchResult(fuente="semantic_scholar", ...),               │
│     SearchResult(fuente="arxiv", ...),                          │
│     SearchResult(fuente="pubmed", ...)                          │
│   ]                                                             │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ PASO 17: Flask convierte a JSON                                 │
│ Archivo: app.py líneas 89-96                                    │
│                                                                 │
│ response = [asdict(r) for r in results]                         │
│                                                                 │
│ Convierte SearchResult → Dict:                                  │
│   {                                                             │
│     "fuente": "semantic_scholar",                               │
│     "texto_original": "Neural networks are models",             │
│     "texto_encontrado": "This paper presents...",               │
│     "porcentaje_match": 89.2,                                   │
│     "documento_coincidente": "Deep Learning Book",              │
│     "autor": "Goodfellow",                                      │
│     "type_document": "JournalArticle"                           │
│   }                                                             │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ PASO 18: Enviar respuesta HTTP                                  │
│ Archivo: app.py líneas 98-102                                   │
│                                                                 │
│ return jsonify({                                                │
│   "results": [                                                  │
│     {                                                           │
│       "fuente": "semantic_scholar",                             │
│       "texto_original": "Neural networks are models",           │
│       "texto_encontrado": "This paper presents deep...",        │
│       "porcentaje_match": 89.2,                                 │
│       "documento_coincidente": "Deep Learning Book",            │
│       "autor": "Goodfellow",                                    │
│       "type_document": "JournalArticle"                         │
│     },                                                          │
│     {                                                           │
│       "fuente": "arxiv",                                        │
│       "texto_original": "Deep learning uses layers",            │
│       "texto_encontrado": "We propose a novel...",              │
│       "porcentaje_match": 85.7,                                 │
│       "documento_coincidente": "CNN Architecture",              │
│       "autor": "LeCun",                                         │
│       "type_document": "preprint"                               │
│     }                                                           │
│   ],                                                            │
│   "count": 2,                                                   │
│   "processed_texts": 2,                                         │
│   "faiss_enabled": true                                         │
│ }), 200                                                         │
│                                                                 │
│ Status: 200 OK                                                  │
│ Content-Type: application/json                                  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ USUARIO RECIBE RESPUESTA                                        │
│                                                                 │
│ JSON con papers similares encontrados ✅                        │
└─────────────────────────────────────────────────────────────────┘