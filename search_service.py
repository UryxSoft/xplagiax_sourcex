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
from faiss_service import get_faiss_index


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
    from searchers import (
        search_crossref, search_pubmed, search_semantic_scholar,
        search_arxiv, search_openalex, search_europepmc,
        search_doaj, search_zenodo
    )
    
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
    
    # Filtrar fuentes
    if sources:
        searches = {k: v for k, v in available_searches.items() if k in sources}
    else:
        searches = available_searches
    
    # Ejecutar búsquedas en paralelo
    tasks = [search_func(query, theme, http_client, rate_limiter) for search_func in searches.values()]
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
    sources: Optional[List[str]] = None,
    use_faiss: bool = True
) -> List[SearchResult]:
    """
    Procesa batch de textos con vectorización completa
    Ahora con soporte FAISS para búsqueda rápida
    """
    start_time = time.time()
    
    all_results = []
    faiss_index = get_faiss_index() if use_faiss else None
    
    # Verificar salud del índice FAISS
    if faiss_index and faiss_index.is_corrupted():
        print("⚠️ Índice FAISS corrupto detectado, reparando...")
        faiss_index.auto_repair()
    
    # Agrupar textos únicos para evitar búsquedas duplicadas
    unique_texts = {}
    for page, paragraph, text in texts:
        processed = preprocess_text_cached(text)
        if processed not in unique_texts:
            unique_texts[processed] = []
        unique_texts[processed].append((page, paragraph, text))
    
    print(f"📊 Procesando {len(texts)} textos ({len(unique_texts)} únicos)")
    
    # Preparar queries para búsqueda en batch
    all_queries = []
    query_mapping = []  # Mapeo de query a texto original
    
    for processed_text, original_texts in unique_texts.items():
        cleaned_text = remove_stopwords_optimized(processed_text, idiom)
        
        # Verificar caché Redis
        cache_key = get_cache_key(theme, idiom, processed_text)
        cached_results = asyncio.run(get_from_cache(redis_client, cache_key))
        
        if cached_results:
            all_results.extend([SearchResult(**r) for r in cached_results])
            continue
        
        all_queries.append(cleaned_text)
        query_mapping.append((processed_text, original_texts, cache_key))
    
    if not all_queries:
        print("✅ Todos los resultados desde caché")
        return all_results
    
    # 1. Buscar en FAISS en batch (ultra-rápido)
    faiss_results_per_query = []
    if faiss_index and faiss_index.index.ntotal > 0:
        print(f"🔍 Buscando {len(all_queries)} queries en FAISS: {faiss_index.index.ntotal} papers indexados")
        try:
            faiss_results_per_query = faiss_index.search_batch(
                all_queries,
                k=20,
                threshold=Config.SIMILARITY_THRESHOLD
            )
            print(f"✅ Búsqueda FAISS completada")
        except Exception as e:
            print(f"⚠️ Error en búsqueda FAISS: {e}")
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
        else:
            # Suficientes resultados desde FAISS
            text_results.sort(key=lambda x: x.porcentaje_match, reverse=True)
            asyncio.run(save_to_cache(redis_client, cache_key, [asdict(r) for r in text_results]))
            all_results.extend(text_results[:10])
    
    # 3. Buscar en APIs solo para queries que necesitan más resultados
    if needs_api_search:
        print(f"🌐 Complementando {len(needs_api_search)} queries con búsqueda en APIs...")
        
        for idx, cleaned_text, processed_text, original_texts, cache_key in needs_api_search:
            # Buscar en APIs
            search_results = asyncio.run(
                search_all_sources(cleaned_text, theme, idiom, http_client, rate_limiter, sources)
            )
            
            if search_results:
                # Agregar nuevos papers a FAISS para futuras búsquedas
                if faiss_index:
                    try:
                        abstracts = [r.get("abstract", "") for r in search_results if r.get("abstract")]
                        if abstracts:
                            faiss_metadata = [
                                {
                                    'title': r.get('title', 'Unknown'),
                                    'author': r.get('author', 'Unknown'),
                                    'abstract': r.get('abstract', ''),
                                    'source': r.get('source', 'unknown'),
                                    'type': r.get('type', 'unknown')
                                }
                                for r in search_results if r.get("abstract")
                            ]
                            faiss_index.add_papers(abstracts, faiss_metadata)
                            print(f"➕ Agregados {len(abstracts)} papers a FAISS")
                    except MemoryError:
                        print("⚠️ Memoria insuficiente, FAISS manejando automáticamente...")
                    except Exception as e:
                        print(f"⚠️ Error agregando a FAISS: {e}")
                
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
                        if similarity >= Config.SIMILARITY_THRESHOLD:
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
    
    # 4. Guardar índice FAISS actualizado
    if faiss_index and faiss_index.index.ntotal > 0:
        try:
            faiss_index.save()
        except Exception as e:
            print(f"⚠️ Error guardando FAISS: {e}")
    
    # Métricas
    elapsed = time.time() - start_time
    print(f"⚡ Procesamiento completado en {elapsed:.2f}s")
    print(f"📈 Throughput: {len(texts)/elapsed:.1f} textos/s")
    if faiss_index:
        print(f"💾 FAISS: {faiss_index.index.ntotal} papers indexados")
    
    return all_results