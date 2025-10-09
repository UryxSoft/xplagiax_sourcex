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