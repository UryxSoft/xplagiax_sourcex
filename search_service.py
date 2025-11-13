"""
Servicio principal de búsqueda - VERSIÓN CORREGIDA
"""
import asyncio
import time
import logging
from typing import List, Dict, Tuple, Optional
from dataclasses import asdict

from html_cleaner import clean_html

from config import Config
from models import SearchResult
from utils import preprocess_text_cached, remove_stopwords_optimized, calculate_similarities_batch
from cache import get_from_cache, save_to_cache, get_cache_key
from searchers import (
    search_crossref, search_pubmed, search_semantic_scholar,
    search_arxiv, search_openalex, search_europepmc,
    search_doaj, search_zenodo
)
from faiss_service import get_faiss_index

logger = logging.getLogger(__name__)


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
        "crossref": lambda q, t, c, rl: search_crossref(q, t, c, rl),
        "pubmed": lambda q, t, c, rl: search_pubmed(q, t, c, rl),
        "semantic_scholar": lambda q, t, c, rl: search_semantic_scholar(q, t, c, rl),
        "arxiv": lambda q, t, c, rl: search_arxiv(q, t, c, rl),
        "openalex": lambda q, t, c, rl: search_openalex(q, t, c, rl),
        "europepmc": lambda q, t, c, rl: search_europepmc(q, t, c, rl),
        "doaj": lambda q, t, c, rl: search_doaj(q, t, c, rl),
        "zenodo": lambda q, t, c, rl: search_zenodo(q, t, c, rl),
    }
    
    # Filtrar fuentes si se especifican
    if sources:
        searches = {k: v for k, v in available_searches.items() if k in sources}
    else:
        searches = available_searches
    
    logger.debug(f"Buscando en {len(searches)} fuentes", extra={"sources": list(searches.keys())})
    
    # Ejecutar búsquedas en paralelo
    tasks = [
        search_func(query, theme, http_client, rate_limiter) 
        for search_func in searches.values()
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    all_results = []
    for source_name, result in zip(searches.keys(), results):
        if isinstance(result, Exception):
            logger.warning(f"Error en búsqueda de {source_name}", extra={"error": str(result)})
            continue
        
        if isinstance(result, list):
            for item in result:
                item["source"] = source_name
                all_results.append(item)
    
    logger.info(f"Búsqueda en APIs completada", extra={
        "sources": len(searches),
        "results": len(all_results)
    })
    
    return all_results


def process_similarity_batch(
    texts: List[Tuple[str, str, str]], 
    theme: str, 
    idiom: str,
    redis_client,
    http_client,
    rate_limiter,
    sources: Optional[List[str]] = None,
    use_faiss: bool = True,
    threshold: float = None  # ✅ NUEVO parámetro
) -> List[SearchResult]:
    """
    Procesa batch de textos con vectorización completa y FAISS
    """
    if threshold is None:
        threshold = Config.SIMILARITY_THRESHOLD
    
    start_time = time.time()
    
    all_results = []
    faiss_index = get_faiss_index() if use_faiss else None
    
    logger.info("Iniciando procesamiento batch", extra={
        "texts": len(texts),
        "theme": theme,
        "idiom": idiom,
        "use_faiss": use_faiss,
        "threshold": threshold,  # ✅ Log
        "faiss_papers": faiss_index.index.ntotal if faiss_index else 0
    })
    
    # Verificar salud del índice FAISS
    if faiss_index and faiss_index.is_corrupted():
        logger.warning("Índice FAISS corrupto detectado, intentando reparar")
        try:
            faiss_index.auto_repair()
        except Exception as e:
            logger.error("Error reparando FAISS", extra={"error": str(e)})
    
    # Agrupar textos únicos para evitar búsquedas duplicadas
    unique_texts = {}
    for page, paragraph, text in texts:
        processed = preprocess_text_cached(text)
        if processed not in unique_texts:
            unique_texts[processed] = []
        unique_texts[processed].append((page, paragraph, text))
    
    logger.debug(f"Textos únicos después de deduplicación: {len(unique_texts)}")
    
    # Preparar queries para búsqueda en batch
    all_queries = []
    query_mapping = []  # Mapeo de query a texto original
    
    for processed_text, original_texts in unique_texts.items():
        cleaned_text = remove_stopwords_optimized(processed_text, idiom)
        
        # Verificar caché Redis
        cache_key = get_cache_key(theme, idiom, processed_text)
        cached_results = asyncio.run(get_from_cache(redis_client, cache_key))
        
        if cached_results:
            logger.debug("Resultado desde caché", extra={"key": cache_key[:20]})
            all_results.extend([SearchResult(**r) for r in cached_results])
            continue
        
        all_queries.append(cleaned_text)
        query_mapping.append((processed_text, original_texts, cache_key))
    
    if not all_queries:
        logger.info("Todos los resultados desde caché")
        return all_results
    
    logger.info(f"Queries a procesar: {len(all_queries)}")
    
    # 1. Buscar en FAISS en batch (ultra-rápido)
    faiss_results_per_query = []
    if faiss_index and faiss_index.index.ntotal > 0:
        logger.info(f"Buscando en FAISS", extra={
            "queries": len(all_queries),
            "indexed_papers": faiss_index.index.ntotal
        })
        
        try:
            faiss_results_per_query = faiss_index.search_batch(
                all_queries,
                k=20,
                threshold=threshold #Config.SIMILARITY_THRESHOLD
            )
            logger.info("Búsqueda FAISS completada exitosamente")
        except Exception as e:
            logger.error("Error en búsqueda FAISS", extra={"error": str(e)})
            faiss_results_per_query = [[] for _ in all_queries]
    else:
        faiss_results_per_query = [[] for _ in all_queries]
    
    # 2. Procesar resultados y complementar con APIs si es necesario
    needs_api_search = []
    
    for idx, (cleaned_text, faiss_results) in enumerate(zip(all_queries, faiss_results_per_query)):
        processed_text, original_texts, cache_key = query_mapping[idx]
        text_results = []
        
        # Convertir resultados FAISS a SearchResult
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
        
        # Si FAISS no tiene suficientes resultados, marcar para buscar en APIs
        if len(text_results) < 5:
            needs_api_search.append((idx, cleaned_text, processed_text, original_texts, cache_key))
            logger.debug(f"Query {idx} necesita búsqueda en APIs (solo {len(text_results)} resultados en FAISS)")
        else:
            # Suficientes resultados desde FAISS
            text_results.sort(key=lambda x: x.porcentaje_match, reverse=True)
            asyncio.run(save_to_cache(redis_client, cache_key, [asdict(r) for r in text_results]))
            all_results.extend(text_results[:10])
    
    # 3. Buscar en APIs solo para queries que necesitan más resultados
    if needs_api_search:
        logger.info(f"Complementando {len(needs_api_search)} queries con APIs externas")
        
        # Acumular todos los papers para agregar a FAISS en un solo batch
        papers_to_add = []
        metadata_to_add = []
        
        for idx, cleaned_text, processed_text, original_texts, cache_key in needs_api_search:
            # Buscar en APIs
            search_results = asyncio.run(
                search_all_sources(cleaned_text, theme, idiom, http_client, rate_limiter, sources)
            )
            
            if search_results:
                # Acumular papers para FAISS
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
                        if similarity >= threshold: #Config.SIMILARITY_THRESHOLD:
                            result = search_results[result_idx]
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
                    
                    # Ordenar y guardar
                    text_results.sort(key=lambda x: x.porcentaje_match, reverse=True)
                    if text_results:
                        asyncio.run(save_to_cache(redis_client, cache_key, [asdict(r) for r in text_results]))
                    all_results.extend(text_results[:10])
        
        # 4. Agregar todos los papers nuevos a FAISS en UN SOLO BATCH
        if papers_to_add and faiss_index:
            try:
                # AGREGAR: Deduplicar antes de agregar a FAISS
                seen_titles = set()
                unique_papers = []
                unique_metadata = []
                
                for paper, meta in zip(papers_to_add, metadata_to_add):
                    title_key = meta['title'].lower().strip()
                    if title_key not in seen_titles:
                        seen_titles.add(title_key)
                        unique_papers.append(paper)
                        unique_metadata.append(meta)
                
                logger.info(f"Deduplicación antes de FAISS: {len(papers_to_add)} → {len(unique_papers)} papers")
                
                if unique_papers:
                    faiss_index.add_papers(unique_papers, unique_metadata)
            except MemoryError:
                logger.warning("Memoria insuficiente, FAISS manejando automáticamente")
            except Exception as e:
                logger.error("Error agregando papers a FAISS", extra={"error": str(e)})
    
    # 5. Guardar índice FAISS actualizado
    if faiss_index and faiss_index.index.ntotal > 0:
        try:
            faiss_index.save()
        except Exception as e:
            logger.warning("Error guardando FAISS", extra={"error": str(e)})
    
    # Métricas
    elapsed = time.time() - start_time
    throughput = len(texts) / elapsed if elapsed > 0 else 0
    
    logger.info("Procesamiento completado", extra={
        "elapsed_seconds": round(elapsed, 2),
        "throughput_texts_per_sec": round(throughput, 1),
        "total_results": len(all_results),
        "faiss_papers": faiss_index.index.ntotal if faiss_index else 0
    })
    
    # ✅ AGREGAR DEDUPLICACIÓN AQUÍ (antes del return)
    # Deduplicar por título + autor
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
    
    logger.info(f"Deduplicación: {len(all_results)} → {len(deduplicated_results)} resultados")
    
    return deduplicated_results  # ✅ Retornar deduplicados en vez de all_results