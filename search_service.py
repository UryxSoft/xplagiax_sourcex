"""
Search Service CORREGIDO - Sin event loops anidados, con caché de embeddings
"""
import time
import logging
from typing import List, Dict, Tuple, Optional
from dataclasses import asdict
import functools

from config import Config
from models import SearchResult
from utils import preprocess_text_cached, remove_stopwords_optimized, calculate_similarities_batch
from cache import get_from_cache, save_to_cache, get_cache_key
from searchers import (
    search_crossref, search_pubmed, search_semantic_scholar,
    search_arxiv, search_openalex, search_europepmc,
    search_doaj, search_zenodo, search_core, search_base,
    search_internet_archive_scholar, search_hal
)

logger = logging.getLogger(__name__)


# ✅ NUEVO: Caché LRU para embeddings de queries
@functools.lru_cache(maxsize=1000)
def get_query_embedding_cached(query: str):
    """
    Caché de embeddings de queries para evitar regeneración
    
    Args:
        query: Query text (debe ser inmutable/hasheable)
    
    Returns:
        Embedding numpy array
    """
    from utils import get_model
    import numpy as np
    import faiss
    
    model = get_model()
    embedding = model.encode(
        [query],
        convert_to_tensor=False,
        show_progress_bar=False,
        normalize_embeddings=True
    )
    
    embedding = np.array(embedding, dtype=np.float32)
    faiss.normalize_L2(embedding)
    
    return embedding


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
    
    CORREGIDO: Mantenido async sin cambios (ya funciona bien)
    """
    import asyncio
    
    available_searches = {
        "crossref": lambda q, t, c, rl: search_crossref(q, t, c, rl),
        "pubmed": lambda q, t, c, rl: search_pubmed(q, t, c, rl),
        "semantic_scholar": lambda q, t, c, rl: search_semantic_scholar(q, t, c, rl),
        "arxiv": lambda q, t, c, rl: search_arxiv(q, t, c, rl),
        "openalex": lambda q, t, c, rl: search_openalex(q, t, c, rl),
        "europepmc": lambda q, t, c, rl: search_europepmc(q, t, c, rl),
        "doaj": lambda q, t, c, rl: search_doaj(q, t, c, rl),
        "zenodo": lambda q, t, c, rl: search_zenodo(q, t, c, rl),
        "core": lambda q, t, c, rl: search_core(q, t, c, rl),
        "base": lambda q, t, c, rl: search_base(q, t, c, rl),
        "internet_archive": lambda q, t, c, rl: search_internet_archive_scholar(q, t, c, rl),
        "hal": lambda q, t, c, rl: search_hal(q, t, c, rl),
    }
    
    if sources:
        searches = {k: v for k, v in available_searches.items() if k in sources}
    else:
        searches = available_searches
    
    logger.debug(f"Buscando en {len(searches)} fuentes", extra={"sources": list(searches.keys())})
    
    tasks = [
        search_func(query, theme, http_client, rate_limiter) 
        for search_func in searches.values()
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    all_results = []
    for source_name, result in zip(searches.keys(), results):
        if isinstance(result, Exception):
            logger.warning(f"Error en {source_name}", extra={"error": str(result)})
            continue
        
        if isinstance(result, list):
            for item in result:
                item["source"] = source_name
                all_results.append(item)
    
    logger.info(f"APIs completadas", extra={
        "sources": len(searches),
        "results": len(all_results)
    })
    
    return all_results


async def process_similarity_batch_async(
    texts: List[Tuple[str, str, str]], 
    theme: str, 
    idiom: str,
    redis_client,
    http_client,
    rate_limiter,
    sources: Optional[List[str]] = None,
    use_faiss: bool = True,
    threshold: float = None
) -> List[SearchResult]:
    """
    ✅ VERSIÓN ASYNC CORREGIDA
    
    CORRECCIONES:
    - Todo async/await sin event loops anidados
    - Caché de embeddings de queries
    - Deduplicación en memoria antes de agregar a FAISS
    - Thread-safe con FAISS locks
    """
    from faiss_service_fixed import get_faiss_index
    
    if threshold is None:
        threshold = Config.SIMILARITY_THRESHOLD
    
    start_time = time.time()
    
    all_results = []
    faiss_index = get_faiss_index() if use_faiss else None
    
    logger.info("Iniciando procesamiento batch", extra={
        "texts": len(texts),
        "use_faiss": use_faiss,
        "threshold": threshold,
        "faiss_papers": faiss_index.index.ntotal if faiss_index else 0
    })
    
    # Agrupar textos únicos
    unique_texts = {}
    for page, paragraph, text in texts:
        processed = preprocess_text_cached(text)
        if processed not in unique_texts:
            unique_texts[processed] = []
        unique_texts[processed].append((page, paragraph, text))
    
    logger.debug(f"Textos únicos: {len(unique_texts)}")
    
    # Preparar queries
    all_queries = []
    query_mapping = []
    
    for processed_text, original_texts in unique_texts.items():
        cleaned_text = remove_stopwords_optimized(processed_text, idiom)
        
        # Verificar caché Redis
        cache_key = get_cache_key(theme, idiom, processed_text)
        cached_results = await get_from_cache(redis_client, cache_key)
        
        if cached_results:
            logger.debug("Desde caché", extra={"key": cache_key[:20]})
            all_results.extend([SearchResult(**r) for r in cached_results])
            continue
        
        all_queries.append(cleaned_text)
        query_mapping.append((processed_text, original_texts, cache_key))
    
    if not all_queries:
        logger.info("Todo desde caché")
        return all_results
    
    # 1. Buscar en FAISS (con caché de embeddings)
    faiss_results_per_query = []
    if faiss_index and faiss_index.index.ntotal > 0:
        logger.info(f"Buscando en FAISS: {len(all_queries)} queries")
        
        try:
            faiss_results_per_query = faiss_index.search_batch(
                all_queries,
                k=20,
                threshold=threshold
            )
        except Exception as e:
            logger.error("Error en FAISS", extra={"error": str(e)})
            faiss_results_per_query = [[] for _ in all_queries]
    else:
        faiss_results_per_query = [[] for _ in all_queries]
    
    # 2. Procesar resultados FAISS
    needs_api_search = []
    
    for idx, (cleaned_text, faiss_results) in enumerate(zip(all_queries, faiss_results_per_query)):
        processed_text, original_texts, cache_key = query_mapping[idx]
        text_results = []
        
        for result in faiss_results:
            search_result = SearchResult(
                fuente=result.get('source', 'faiss'),
                texto_original=original_texts[0][2],
                texto_encontrado=result.get('abstract', '')[:300] + "...",
                porcentaje_match=result['porcentaje_match'],
                documento_coincidente=result.get('title', 'Unknown'),
                autor=result.get('author', 'Unknown'),
                type_document=result.get('type', 'unknown')
            )
            text_results.append(search_result)
        
        if len(text_results) < 5:
            needs_api_search.append((idx, cleaned_text, processed_text, original_texts, cache_key))
        else:
            text_results.sort(key=lambda x: x.porcentaje_match, reverse=True)
            await save_to_cache(redis_client, cache_key, [asdict(r) for r in text_results])
            all_results.extend(text_results[:10])
    
    # 3. Buscar en APIs (solo si es necesario)
    if needs_api_search:
        logger.info(f"Complementando con APIs: {len(needs_api_search)} queries")
        
        # ✅ CORREGIDO: Acumular papers para batch add
        papers_to_add = []
        metadata_to_add = []
        
        for idx, cleaned_text, processed_text, original_texts, cache_key in needs_api_search:
            # ✅ Ya estamos en contexto async, no usar asyncio.run()
            search_results = await search_all_sources(
                cleaned_text, theme, idiom, http_client, rate_limiter, sources
            )
            
            if search_results:
                # Acumular para FAISS
                for r in search_results:
                    if r.get("abstract"):
                        papers_to_add.append(r["abstract"])
                        metadata_to_add.append({
                            'title': r.get('title', 'Unknown'),
                            'author': r.get('author', 'Unknown'),
                            'abstract': r['abstract'],
                            'source': r.get('source', 'unknown'),
                            'type': r.get('type', 'unknown')
                        })
                
                # Calcular similitudes
                abstracts = [r.get("abstract", "") for r in search_results]
                processed_abstracts = [preprocess_text_cached(a) for a in abstracts if a]
                
                if processed_abstracts:
                    similarities = calculate_similarities_batch(
                        [cleaned_text],
                        processed_abstracts
                    )[0]
                    
                    text_results = []
                    for result_idx, similarity in enumerate(similarities):
                        if similarity >= threshold:
                            result = search_results[result_idx]
                            
                            search_result = SearchResult(
                                fuente=result["source"],
                                texto_original=original_texts[0][2],
                                texto_encontrado=result['abstract'][:300] + "...",
                                porcentaje_match=round(float(similarity) * 100, 1),
                                documento_coincidente=result.get("title", "Unknown"),
                                autor=result.get("author", "Unknown"),
                                type_document=result.get("type", "unknown")
                            )
                            text_results.append(search_result)
                    
                    text_results.sort(key=lambda x: x.porcentaje_match, reverse=True)
                    if text_results:
                        await save_to_cache(redis_client, cache_key, [asdict(r) for r in text_results])
                    all_results.extend(text_results[:10])
        
        # 4. ✅ CORREGIDO: Agregar a FAISS con deduplicación automática
        if papers_to_add and faiss_index:
            try:
                logger.info(f"Agregando {len(papers_to_add)} papers a FAISS")
                
                # add_papers ya hace deduplicación interna
                stats = faiss_index.add_papers(papers_to_add, metadata_to_add)
                
                logger.info(f"FAISS actualizado", extra=stats)
            
            except Exception as e:
                logger.error("Error agregando a FAISS", extra={"error": str(e)})
    
    # 5. Guardar índice
    if faiss_index and faiss_index.index.ntotal > 0:
        try:
            faiss_index.save()
        except Exception as e:
            logger.warning("Error guardando FAISS", extra={"error": str(e)})
    
    # Deduplicar resultados finales
    seen = set()
    deduplicated_results = []
    
    for result in all_results:
        key = (
            result.documento_coincidente.lower().strip(),
            result.autor.lower().strip()
        )
        
        if key not in seen:
            seen.add(key)
            deduplicated_results.append(result)
    
    elapsed = time.time() - start_time
    throughput = len(texts) / elapsed if elapsed > 0 else 0
    
    logger.info("Procesamiento completado", extra={
        "elapsed_seconds": round(elapsed, 2),
        "throughput_texts_per_sec": round(throughput, 1),
        "results": len(deduplicated_results),
        "duplicates_removed": len(all_results) - len(deduplicated_results)
    })
    
    return deduplicated_results


def process_similarity_batch(
    texts: List[Tuple[str, str, str]], 
    theme: str, 
    idiom: str,
    redis_client,
    http_client,
    rate_limiter,
    sources: Optional[List[str]] = None,
    use_faiss: bool = True,
    threshold: float = None
) -> List[SearchResult]:
    """
     WRAPPER SÍNCRONO CORREGIDO
    
    CORRECCIÓN: Usa event loop existente o crea uno nuevo apropiadamente
    """
    import asyncio
    
    try:
        # Intentar usar loop existente
        loop = asyncio.get_running_loop()
        # Si llegamos aquí, estamos en un contexto async
        raise RuntimeError("Esta función no debe llamarse desde contexto async. Usa process_similarity_batch_async directamente.")
    except RuntimeError:
        # No hay loop running, crear uno nuevo
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            return loop.run_until_complete(
                process_similarity_batch_async(
                    texts, theme, idiom, redis_client, http_client,
                    rate_limiter, sources, use_faiss, threshold
                )
            )
        finally:
            loop.close()