"""
FAISS Service CORREGIDO - Sin duplicados, con IndexIDMap y hashing
"""
import os
import pickle
import gc
import logging
import hashlib
from typing import List, Dict, Optional, Set
import numpy as np
import threading

try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False

from utils import get_model

logger = logging.getLogger(__name__)


class FAISSIndex:
    """
    Índice FAISS con deduplicación por hash de contenido
    
    CORRECCIONES:
    1. Usa IndexIDMap para permitir reemplazo de vectores
    2. Mantiene Set de hashes de abstracts para dedup rápida O(1)
    3. Lock thread-safe para escrituras concurrentes
    4. Metadata sincronizada con índice mediante dict {id: metadata}
    """
    
    def __init__(self, dimension: int = 384, index_path: str = "data/faiss_index"):
        if not FAISS_AVAILABLE:
            raise ImportError("FAISS no está instalado")
        
        self.dimension = dimension
        self.index_path = index_path
        self.metadata_path = f"{index_path}_metadata.pkl"
        
        # ✅ NUEVO: IndexIDMap para permitir updates
        base_index = faiss.IndexFlatIP(dimension)
        self.index = faiss.IndexIDMap(base_index)
        
        # ✅ NUEVO: Metadata como dict {faiss_id: metadata}
        self.metadata: Dict[int, Dict] = {}
        
        # ✅ NUEVO: Set de hashes para dedup rápida
        self.content_hashes: Set[str] = set()
        
        # ✅ NUEVO: Lock para thread-safety
        self.lock = threading.RLock()
        
        self.current_strategy = "flat_idmap"
        self._corrupted = False
        self._next_id = 0
        
        # Intentar cargar índice existente
        self.load()
        
        logger.info(f"FAISS inicializado con IndexIDMap", extra={
            "dimension": dimension,
            "papers": self.index.ntotal,
            "unique_hashes": len(self.content_hashes)
        })
    
    def _hash_content(self, text: str) -> str:
        """
        Genera hash único del contenido
        
        Args:
            text: Abstract o contenido a hashear
        
        Returns:
            Hash SHA256 truncado (16 bytes)
        """
        # Normalizar texto antes de hashear
        normalized = text.lower().strip()
        normalized = ' '.join(normalized.split())  # Normalizar espacios
        
        return hashlib.sha256(normalized.encode('utf-8')).hexdigest()[:32]
    
    def _content_exists(self, text: str) -> bool:
        """
        Verifica si el contenido ya existe (O(1))
        
        Args:
            text: Abstract a verificar
        
        Returns:
            True si ya existe
        """
        content_hash = self._hash_content(text)
        return content_hash in self.content_hashes
    
    def add_papers(self, abstracts: List[str], metadata: List[Dict], force: bool = False):
        """
        Agrega papers con deduplicación automática
        
        CORRECCIONES:
        - Verifica duplicados por hash antes de agregar
        - Usa lock para thread-safety
        - Sincroniza metadata con índice
        - Retorna stats de cuántos se agregaron vs duplicados
        
        Args:
            abstracts: Lista de abstracts
            metadata: Lista de metadata
            force: Si True, omite deduplicación
        
        Returns:
            Dict con stats: {added, duplicates, total}
        """
        if not abstracts or not metadata:
            logger.warning("add_papers llamado sin datos")
            return {"added": 0, "duplicates": 0, "total": 0}
        
        if len(abstracts) != len(metadata):
            raise ValueError("abstracts y metadata deben tener misma longitud")
        
        with self.lock:
            # Filtrar duplicados
            unique_abstracts = []
            unique_metadata = []
            duplicate_count = 0
            
            for abstract, meta in zip(abstracts, metadata):
                if force or not self._content_exists(abstract):
                    unique_abstracts.append(abstract)
                    unique_metadata.append(meta)
                else:
                    duplicate_count += 1
                    logger.debug(f"Duplicado detectado: {meta.get('title', 'Unknown')[:50]}")
            
            if not unique_abstracts:
                logger.info(f"Todos duplicados: {duplicate_count} papers")
                return {"added": 0, "duplicates": duplicate_count, "total": len(abstracts)}
            
            logger.info(f"Agregando {len(unique_abstracts)} papers únicos ({duplicate_count} duplicados filtrados)")
            
            try:
                model = get_model()
                
                # Generar embeddings solo de papers únicos
                embeddings = model.encode(
                    unique_abstracts,
                    convert_to_tensor=False,
                    show_progress_bar=False,
                    batch_size=64,
                    normalize_embeddings=True
                )
                
                embeddings = np.array(embeddings, dtype=np.float32)
                faiss.normalize_L2(embeddings)
                
                # Generar IDs únicos
                new_ids = np.arange(
                    self._next_id,
                    self._next_id + len(embeddings),
                    dtype=np.int64
                )
                
                # Agregar a índice con IDs
                self.index.add_with_ids(embeddings, new_ids)
                
                # Actualizar metadata y hashes
                for idx, (paper_id, meta, abstract) in enumerate(zip(new_ids, unique_metadata, unique_abstracts)):
                    self.metadata[int(paper_id)] = meta
                    content_hash = self._hash_content(abstract)
                    self.content_hashes.add(content_hash)
                
                self._next_id += len(embeddings)
                
                logger.info(f"Papers agregados exitosamente", extra={
                    "added": len(unique_abstracts),
                    "duplicates": duplicate_count,
                    "total_indexed": self.index.ntotal
                })
                
                return {
                    "added": len(unique_abstracts),
                    "duplicates": duplicate_count,
                    "total": len(abstracts)
                }
            
            except Exception as e:
                logger.error("Error agregando papers", extra={"error": str(e)})
                raise
    
    def search(self, query: str, k: int = 10, threshold: float = 0.7) -> List[Dict]:
        """Búsqueda con metadata correcta"""
        if self.index.ntotal == 0:
            return []
        
        try:
            with self.lock:
                model = get_model()
                
                query_emb = model.encode(
                    [query],
                    convert_to_tensor=False,
                    show_progress_bar=False,
                    normalize_embeddings=True
                )
                
                query_emb = np.array(query_emb, dtype=np.float32)
                faiss.normalize_L2(query_emb)
                
                k_search = min(k, self.index.ntotal)
                scores, indices = self.index.search(query_emb, k_search)
                
                results = []
                for score, idx in zip(scores[0], indices[0]):
                    if idx == -1:
                        continue
                    
                    similarity = float(score)
                    if similarity >= threshold:
                        # ✅ CORREGIDO: Obtener metadata por ID
                        meta = self.metadata.get(int(idx), {})
                        
                        result = {
                            **meta,
                            'porcentaje_match': round(similarity * 100, 1),
                            'faiss_similarity': similarity,
                            'faiss_id': int(idx)
                        }
                        results.append(result)
                
                return results
        
        except Exception as e:
            logger.error("Error en búsqueda", extra={"error": str(e)})
            return []
    
    def search_batch(self, queries: List[str], k: int = 10, threshold: float = 0.7) -> List[List[Dict]]:
        """Búsqueda batch optimizada"""
        if self.index.ntotal == 0:
            return [[] for _ in queries]
        
        try:
            with self.lock:
                model = get_model()
                
                query_embs = model.encode(
                    queries,
                    convert_to_tensor=False,
                    show_progress_bar=False,
                    batch_size=64,
                    normalize_embeddings=True
                )
                
                query_embs = np.array(query_embs, dtype=np.float32)
                faiss.normalize_L2(query_embs)
                
                k_search = min(k, self.index.ntotal)
                scores, indices = self.index.search(query_embs, k_search)
                
                all_results = []
                for query_scores, query_indices in zip(scores, indices):
                    query_results = []
                    for score, idx in zip(query_scores, query_indices):
                        if idx == -1:
                            continue
                        
                        similarity = float(score)
                        if similarity >= threshold:
                            meta = self.metadata.get(int(idx), {})
                            
                            result = {
                                **meta,
                                'porcentaje_match': round(similarity * 100, 1),
                                'faiss_similarity': similarity,
                                'faiss_id': int(idx)
                            }
                            query_results.append(result)
                    
                    all_results.append(query_results)
                
                return all_results
        
        except Exception as e:
            logger.error("Error en búsqueda batch", extra={"error": str(e)})
            return [[] for _ in queries]
    
    def remove_duplicates(self) -> int:
        """
        Elimina duplicados del índice existente
        
        Returns:
            Número de duplicados eliminados
        """
        if self.index.ntotal == 0:
            return 0
        
        logger.info("Iniciando limpieza de duplicados")
        
        with self.lock:
            # Reconstruir desde cero
            unique_ids = []
            unique_embeddings = []
            unique_metadata = []
            seen_hashes = set()
            duplicates = 0
            
            # Iterar sobre todos los vectores
            for idx in range(self.index.ntotal):
                try:
                    # Obtener vector y metadata
                    vector = self.index.reconstruct(idx)
                    meta = self.metadata.get(idx, {})
                    abstract = meta.get('abstract', '')
                    
                    if not abstract:
                        continue
                    
                    content_hash = self._hash_content(abstract)
                    
                    if content_hash not in seen_hashes:
                        seen_hashes.add(content_hash)
                        unique_ids.append(idx)
                        unique_embeddings.append(vector)
                        unique_metadata.append(meta)
                    else:
                        duplicates += 1
                
                except Exception as e:
                    logger.warning(f"Error procesando vector {idx}: {e}")
                    continue
            
            if duplicates == 0:
                logger.info("No se encontraron duplicados")
                return 0
            
            # Crear nuevo índice limpio
            logger.info(f"Reconstruyendo índice: {len(unique_embeddings)} únicos, {duplicates} duplicados")
            
            base_index = faiss.IndexFlatIP(self.dimension)
            new_index = faiss.IndexIDMap(base_index)
            
            if unique_embeddings:
                embeddings_array = np.array(unique_embeddings, dtype=np.float32)
                ids_array = np.array(range(len(unique_embeddings)), dtype=np.int64)
                
                new_index.add_with_ids(embeddings_array, ids_array)
                
                # Reconstruir metadata
                new_metadata = {i: meta for i, meta in enumerate(unique_metadata)}
                
                # Reemplazar índice
                self.index = new_index
                self.metadata = new_metadata
                self.content_hashes = seen_hashes
                self._next_id = len(unique_embeddings)
            
            logger.info(f"Limpieza completada: {duplicates} duplicados eliminados")
            
            # Guardar índice limpio
            self.save()
            
            return duplicates
    
    def save(self):
        """Guarda índice + metadata"""
        try:
            with self.lock:
                os.makedirs(os.path.dirname(self.index_path) if os.path.dirname(self.index_path) else '.', exist_ok=True)
                
                # Guardar índice FAISS
                faiss.write_index(self.index, f"{self.index_path}.index")
                
                # Guardar metadata + hashes
                save_data = {
                    'metadata': self.metadata,
                    'content_hashes': self.content_hashes,
                    'next_id': self._next_id,
                    'strategy': self.current_strategy,
                    'dimension': self.dimension
                }
                
                with open(self.metadata_path, 'wb') as f:
                    pickle.dump(save_data, f, protocol=pickle.HIGHEST_PROTOCOL)
                
                logger.info("Índice FAISS guardado", extra={
                    "papers": self.index.ntotal,
                    "unique_hashes": len(self.content_hashes)
                })
        
        except Exception as e:
            logger.error("Error guardando índice", extra={"error": str(e)})
            raise
    
    def load(self):
        """Carga índice + metadata"""
        try:
            index_file = f"{self.index_path}.index"
            
            if not os.path.exists(index_file) or not os.path.exists(self.metadata_path):
                logger.info("No se encontró índice existente")
                return False
            
            with self.lock:
                # Cargar índice
                self.index = faiss.read_index(index_file)
                
                # Cargar metadata
                with open(self.metadata_path, 'rb') as f:
                    save_data = pickle.load(f)
                
                self.metadata = save_data.get('metadata', {})
                self.content_hashes = save_data.get('content_hashes', set())
                self._next_id = save_data.get('next_id', self.index.ntotal)
                self.current_strategy = save_data.get('strategy', 'flat_idmap')
                
                logger.info("Índice FAISS cargado", extra={
                    "papers": self.index.ntotal,
                    "metadata_entries": len(self.metadata),
                    "unique_hashes": len(self.content_hashes)
                })
                
                # Validar consistencia
                if self.index.ntotal != len(self.metadata):
                    logger.warning("Inconsistencia detectada, intentando reparar")
                    self.auto_repair()
                
                return True
        
        except Exception as e:
            logger.error("Error cargando índice", extra={"error": str(e)})
            self._corrupted = True
            return False
    
    def clear(self):
        """Limpia completamente el índice"""
        with self.lock:
            logger.warning("Limpiando índice FAISS completamente")
            
            base_index = faiss.IndexFlatIP(self.dimension)
            self.index = faiss.IndexIDMap(base_index)
            self.metadata = {}
            self.content_hashes = set()
            self._next_id = 0
            self._corrupted = False
    
    def auto_repair(self):
        """Repara índice corrupto"""
        logger.warning("Intentando reparar índice")
        
        with self.lock:
            # Si metadata tiene más entradas, truncar
            if len(self.metadata) > self.index.ntotal:
                valid_ids = set(range(self.index.ntotal))
                self.metadata = {k: v for k, v in self.metadata.items() if k in valid_ids}
                logger.info(f"Metadata truncada a {len(self.metadata)} entradas")
            
            # Reconstruir content_hashes desde metadata
            self.content_hashes = set()
            for meta in self.metadata.values():
                if 'abstract' in meta:
                    self.content_hashes.add(self._hash_content(meta['abstract']))
            
            self._corrupted = False
            self.save()
            logger.info("Reparación completada")
    
    def get_stats(self) -> Dict:
        """Estadísticas del índice"""
        with self.lock:
            return {
                "total_papers": self.index.ntotal,
                "dimension": self.dimension,
                "metadata_count": len(self.metadata),
                "unique_hashes": len(self.content_hashes),
                "strategy": self.current_strategy,
                "corrupted": self._corrupted,
                "has_duplicates": self.index.ntotal > len(self.content_hashes)
            }


# Instancia global
_faiss_index: Optional[FAISSIndex] = None


def get_faiss_index() -> Optional[FAISSIndex]:
    """Retorna instancia global"""
    global _faiss_index
    
    if not FAISS_AVAILABLE:
        return None
    
    return _faiss_index


def init_faiss_index(dimension: int = 384, index_path: str = "data/faiss_index") -> Optional[FAISSIndex]:
    """Inicializa índice FAISS"""
    global _faiss_index
    
    if not FAISS_AVAILABLE:
        logger.error("FAISS no disponible")
        return None
    
    try:
        _faiss_index = FAISSIndex(dimension=dimension, index_path=index_path)
        logger.info("FAISS inicializado correctamente")
        return _faiss_index
    except Exception as e:
        logger.error("Error inicializando FAISS", extra={"error": str(e)})
        return None