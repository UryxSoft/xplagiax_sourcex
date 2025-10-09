"""
Servicio principal de búsqueda
"""
import asyncio
import time
from typing import List, Dict, Tuple, Optional
from dataclasses import asdict

from config import Config
from models import SearchResult
from utils import preprocess_text_cached, remove_stopwords_optimized, calculate_similarities_batch
from cache import get_from_cache, save_to_cache, get_cache_key
from searchers import (
    search_crossref, search_pubmed, search_semantic_scholar,
    search_arxiv, search_openalex, search_europepmc,
    search_doaj, search_zenodo
)


async def search_all_sources(
    query: str, 
    theme: str, 
    idiom: str, 
    http_client,
    rate_limiter,
    sources: Optional[List[str]] = None
) -> List[Dict]:
    """
    Busca en todas las fuentes en paralelo
    """
    available_searches = {
        "crossref": lambda q, t, c: search_crossref(q, t, c, rate_limiter),
        "pubmed": lambda q, t, c: search_pubmed(q, t, c, rate_limiter),
        "semantic_scholar": lambda q, t, c: search_semantic_scholar(q, t, c, rate_limiter),
        "arxiv": lambda q, t, c: search_arxiv(q, t, c, rate_limiter),
        "openalex": lambda q, t, c: search_openalex(q, t, c, rate_limiter),
        "europepmc": lambda q, t, c: search_europepmc(q, t, c, rate_limiter),
        "doaj": lambda q, t, c: search_doaj(q, t, c, rate_limiter),
        "zenodo": lambda q, t, c: search_zenodo(q, t, c, rate_limiter),
    }
    
    # Filtrar fuentes
    if sources:
        searches = {k: v for k, v in available_searches.items() if k in sources}
    else:
        searches = available_searches
    
    # Ejecutar búsquedas en paralelo
    tasks = [search_func(query, theme, http_client) for search_func in searches.values()]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    all_results = []
    for source_name, result in zip(searches.keys(), results):
        if isinstance(result, list):
            for item in result:
                item["source"] = source_name
                all_results.append(item)
    
    return all_results


def process_similarity_batch(
    texts: List[Tuple[str, str, str]], 
    theme: str, 
    idiom: str,
    redis_client,
    http_client,
    rate_limiter,
    sources: Optional[List[str]] = None
) -> List[SearchResult]:
    """
    Procesa batch de textos con vectorización completa
    """
    start_time = time.time()
    
    all_results = []
    
    # Agrupar textos únicos para evitar búsquedas duplicadas
    unique_texts = {}
    for page, paragraph, text in texts:
        processed = preprocess_text_cached(text)
        if processed not in unique_texts:
            unique_texts[processed] = []
        unique_texts[processed].append((page, paragraph, text))
    
    print(f"📊 Procesando {len(texts)} textos ({len(unique_texts)} únicos)")
    
    for processed_text, original_texts in unique_texts.items():
        cleaned_text = remove_stopwords_optimized(processed_text, idiom)
        
        # Verificar caché
        cache_key = get_cache_key(theme, idiom, processed_text)
        cached_results = asyncio.run(get_from_cache(redis_client, cache_key))
        
        if cached_results:
            all_results.extend([SearchResult(**r) for r in cached_results])
            continue
        
        # Buscar en fuentes
        search_results = asyncio.run(
            search_all_sources(cleaned_text, theme, idiom, http_client, rate_limiter, sources)
        )
        
        if not search_results:
            continue
        
        # Calcular similitudes en batch
        abstracts = [r.get("abstract", "") for r in search_results]
        processed_abstracts = [preprocess_text_cached(a) for a in abstracts if a]
        
        if not processed_abstracts:
            continue
        
        similarities = calculate_similarities_batch(
            [cleaned_text],
            processed_abstracts
        )[0]
        
        # Filtrar por threshold
        text_results = []
        for idx, similarity in enumerate(similarities):
            if similarity >= Config.SIMILARITY_THRESHOLD:
                result = search_results[idx]
                abstract = result.get("abstract", "")
                
                search_result = SearchResult(
                    fuente=result["source"],
                    texto_original=original_texts[0][2],
                    texto_encontrado=abstract[:300] + "..." if len(abstract) > 300 else abstract,
                    porcentaje_match=round(float(similarity) * 100, 1),
                    documento_coincidente=result.get("title", "Unknown"),
                    autor=result.get("author", "Unknown"),
                    type_document=result.get("type", "unknown")
                )
                text_results.append(search_result)
        
        # Ordenar por similitud
        text_results.sort(key=lambda x: x.porcentaje_match, reverse=True)
        
        # Guardar en caché
        if text_results:
            asyncio.run(save_to_cache(redis_client, cache_key, [asdict(r) for r in text_results]))
        
        all_results.extend(text_results[:10])
    
    # Métricas
    elapsed = time.time() - start_time
    print(f"⚡ Procesamiento completado en {elapsed:.2f}s")
    print(f"📈 Throughput: {len(texts)/elapsed:.1f} textos/s")
    
    return all_results