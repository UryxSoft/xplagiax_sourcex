# Guía de Uso de FAISS

## ¿Qué es FAISS?

FAISS (Facebook AI Similarity Search) es una librería para búsqueda rápida de similitud vectorial. En este proyecto, almacena embeddings de papers académicos para búsquedas ultra-rápidas.

## Flujo de Trabajo

### 1. Primera Búsqueda (Sin FAISS)
```bash
POST /api/similarity-search
{
  "data": ["machine learning", "en", [
    ["page1", "para1", "Neural networks are powerful models"]
  ]]
}
```

**Qué sucede:**
- ✅ Busca en APIs académicas (PubMed, arXiv, etc)
- ✅ Calcula similitudes
- ✅ **GUARDA automáticamente en FAISS** los papers encontrados
- ⏱️ Toma 5-10 segundos

### 2. Búsquedas Siguientes (Con FAISS)
```bash
POST /api/similarity-search
{
  "data": ["machine learning", "en", [
    ["page1", "para1", "Deep learning networks"]
  ]],
  "use_faiss": true  // Por defecto es true
}
```

**Qué sucede:**
- ✅ **Busca primero en FAISS** (local, instantáneo)
- ✅ Si encuentra >5 resultados, los devuelve (50-200ms)
- ✅ Si no, complementa con APIs
- ✅ Nuevos papers se agregan a FAISS
- ⚡ Toma 100-500ms

## Endpoints FAISS

### Ver Estadísticas
```bash
GET /api/faiss/stats

Response:
{
  "total_papers": 1523,
  "dimension": 384,
  "index_size_mb": 2.3,
  "metadata_count": 1523
}
```

### Búsqueda Directa en FAISS
```bash
POST /api/faiss/search
{
  "query": "deep learning neural networks",
  "k": 20,
  "threshold": 0.75
}

Response:
{
  "query": "deep learning neural networks",
  "results": [
    {
      "title": "Deep Learning Book",
      "author": "Goodfellow et al.",
      "porcentaje_match": 89.2,
      "abstract": "...",
      "source": "semantic_scholar"
    }
  ],
  "count": 15
}
```

### Guardar Índice Manualmente
```bash
POST /api/faiss/save

Response:
{
  "message": "Índice guardado exitosamente",
  "stats": {
    "total_papers": 1523
  }
}
```

### Limpiar Índice
```bash
POST /api/faiss/clear

Response:
{
  "message": "Índice FAISS limpiado"
}
```

## Persistencia

### Automática
- FAISS guarda automáticamente después de cada búsqueda
- Al reiniciar el contenedor, carga el índice existente

### Manual
```bash
# Guardar explícitamente
curl -X POST http://localhost:5000/api/faiss/save
```

### Ubicación del Índice
- **Local**: `./data/faiss_index.index` y `./data/faiss_index_metadata.pkl`
- **Docker**: Volume `faiss_data:/app/data`

## Ventajas en tu Caso de Uso

### Detección de Plagio
```bash
# Primera vez: construye base de datos
POST /api/similarity-search
{
  "data": ["plagiarism detection", "en", [
    ["page1", "p1", "Párrafo del documento a verificar"],
    ["page1", "p2", "Otro párrafo del documento"],
    ...
  ]]
}
```

Después de indexar ~1000 papers:

**Sin FAISS**: 10 párrafos × 8s = 80 segundos
**Con FAISS**: 10 párrafos × 0.3s = 3 segundos

### Ventajas:
1. **Velocidad**: 25x más rápido
2. **Escala**: Busca en millones de papers
3. **Offline**: Funciona sin APIs externas
4. **Precisión**: Similitud semántica pura

## Configuración Avanzada

### Cambiar Dimensión (si usas otro modelo)
```python
# En app.py o directamente
init_faiss_index(dimension=768)  # Para modelos BERT grandes
```

### Desactivar FAISS
```bash
POST /api/similarity-search
{
  "data": [...],
  "use_faiss": false  // Solo usa APIs
}
```

## Monitoreo

### Health Check
```bash
GET /api/health

Response:
{
  "status": "healthy",
  "faiss": {
    "total_papers": 1523,
    "dimension": 384,
    "index_size_mb": 2.3
  }
}
```

## Tips

1. **Warm-up**: Haz algunas búsquedas iniciales para poblar FAISS
2. **Backup**: El índice persiste en el volume `faiss_data`
3. **Límites**: FAISS puede manejar millones de vectores en una laptop
4. **GPU**: Para producción, usa `faiss-gpu` (100x más rápido)

## Ejemplo Completo

```python
import requests

# 1. Primera búsqueda (construye índice)
response = requests.post('http://localhost:5000/api/similarity-search', json={
    "data": ["machine learning", "en", [
        ["p1", "1", "Deep learning is a subset of machine learning"],
        ["p1", "2", "Neural networks mimic biological neurons"]
    ]]
})

print(f"Encontrados: {response.json()['count']} papers")
print(f"FAISS activo: {response.json()['faiss_enabled']}")

# 2. Ver estadísticas
stats = requests.get('http://localhost:5000/api/faiss/stats').json()
print(f"Papers indexados: {stats['total_papers']}")

# 3. Búsqueda rápida siguiente
response = requests.post('http://localhost:5000/api/similarity-search', json={
    "data": ["machine learning", "en", [
        ["p2", "1", "Convolutional networks for image recognition"]
    ]]
})
# Esta será mucho más rápida!
```

## Troubleshooting

### "FAISS no disponible"
```bash
pip install faiss-cpu
# O en Docker, ya está en requirements.txt
```

### Índice corrupto
```bash
POST /api/faiss/clear  # Limpiar y reconstruir
```

### Memoria insuficiente
```python
# Usar índice con compresión
# En faiss_service.py, cambiar a:
self.index = faiss.IndexIVFFlat(quantizer, dimension, nlist)
```