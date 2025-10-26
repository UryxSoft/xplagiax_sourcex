"""
FAISS Service OPTIMIZADO con HNSW + IVF + PQ - VERSIÓN CORREGIDA
"""
import os
import pickle
import gc
import logging
from typing import List, Dict, Optional
import numpy as np

try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False

from utils import get_model

logger = logging.getLogger(__name__)


class FAISSIndex:
    """
    Índice FAISS con selección automática de estrategia según tamaño
    
    Estrategias:
    - <10k vectores: IndexFlatIP (exacto, rápido)
    - 10k-100k: HNSW (grafos jerárquicos, ~95% recall)
    - 100k-1M: IVF + Flat (clusters + búsqueda exacta)
    - >1M: IVF + PQ (clusters + cuantización)
    """
    
    def __init__(self, dimension: int = 384, index_path: str = "data/faiss_index"):
        if not FAISS_AVAILABLE:
            raise ImportError("FAISS no está instalado. Ejecute: pip install faiss-cpu")
        
        self.dimension = dimension
        self.index_path = index_path
        self.metadata_path = f"{index_path}_metadata.pkl"
        
        # Iniciar con índice pequeño
        self.index = self._create_small_index()
        self.metadata = []
        self.current_strategy = "flat"
        self._corrupted = False
        
        # Intentar cargar índice existente
        self.load()
        
        logger.info(f"FAISS inicializado", extra={
            "dimension": dimension,
            "strategy": self.current_strategy,
            "papers": self.index.ntotal
        })
    
    def _create_small_index(self):
        """Índice para <10k vectores (exacto)"""
        return faiss.IndexFlatIP(self.dimension)
    
    def _create_hnsw_index(self):
        """Índice HNSW para 10k-100k vectores (rápido, ~95% recall)"""
        index = faiss.IndexHNSWFlat(self.dimension, 32)  # 32 = M (conexiones por nodo)
        index.hnsw.efConstruction = 40  # Calidad de construcción
        index.hnsw.efSearch = 16  # Velocidad de búsqueda
        return index
    
    def _create_ivf_flat_index(self, nlist: int = 100):
        """Índice IVF+Flat para 100k-1M vectores"""
        quantizer = faiss.IndexFlatIP(self.dimension)
        index = faiss.IndexIVFFlat(quantizer, self.dimension, nlist)
        index.nprobe = 10  # Clusters a visitar (10 = buen balance)
        return index
    
    def _create_ivf_pq_index(self, nlist: int = 1000):
        """Índice IVF+PQ para >1M vectores (máxima compresión)"""
        quantizer = faiss.IndexFlatIP(self.dimension)
        # PQ: 48 bytes por vector (vs 384*4=1536 bytes)
        m = 48  # Subvectores
        nbits = 8  # Bits por subvector
        index = faiss.IndexIVFPQ(quantizer, self.dimension, nlist, m, nbits)
        index.nprobe = 20
        return index
    
    def _auto_upgrade_index(self):
        """Actualiza automáticamente el índice según el tamaño"""
        current_size = self.index.ntotal
        
        # Estrategia según tamaño
        if current_size < 10000:
            if self.current_strategy != "flat":
                return  # Ya está bien
        
        elif 10000 <= current_size < 100000:
            if self.current_strategy == "flat":
                logger.info(f"Auto-upgrade a HNSW iniciado ({current_size} vectores)")
                self._migrate_to_hnsw()
        
        elif 100000 <= current_size < 1000000:
            if self.current_strategy in ["flat", "hnsw"]:
                logger.info(f"Auto-upgrade a IVF+Flat iniciado ({current_size} vectores)")
                self._migrate_to_ivf_flat()
        
        elif current_size >= 1000000:
            if self.current_strategy != "ivf_pq":
                logger.info(f"Auto-upgrade a IVF+PQ iniciado ({current_size} vectores)")
                self._migrate_to_ivf_pq()
    
    def _migrate_to_hnsw(self):
        """Migra de Flat a HNSW con gestión de memoria"""
        old_index = self.index
        old_total = old_index.ntotal
        
        new_index = self._create_hnsw_index()
        
        if old_total > 0:
            # Migrar en batches para evitar duplicar toda la memoria
            batch_size = 10000
            logger.info(f"Migrando {old_total} vectores en batches de {batch_size}")
            
            for start in range(0, old_total, batch_size):
                end = min(start + batch_size, old_total)
                try:
                    vectors = old_index.reconstruct_n(start, end - start)
                    new_index.add(vectors)
                    del vectors  # Liberar inmediatamente
                except Exception as e:
                    logger.error(f"Error migrando batch {start}-{end}", extra={"error": str(e)})
                    raise
        
        # Liberar old_index antes de reasignar
        del old_index
        gc.collect()
        
        self.index = new_index
        self.current_strategy = "hnsw"
        logger.info(f"Migración a HNSW completada: {self.index.ntotal} vectores")
    
    def _migrate_to_ivf_flat(self):
        """Migra a IVF+Flat con gestión de memoria"""
        old_index = self.index
        old_total = old_index.ntotal
        
        # Calcular número óptimo de clusters
        nlist = min(int(np.sqrt(old_total)), 1000)
        new_index = self._create_ivf_flat_index(nlist)
        
        if old_total >= 100:
            try:
                # Entrenar con muestra
                train_size = min(10000, old_total)
                logger.info(f"Entrenando IVF+Flat con {train_size} vectores")
                
                if hasattr(old_index, 'reconstruct_n'):
                    train_data = old_index.reconstruct_n(0, train_size)
                    new_index.train(train_data)
                    del train_data
                    gc.collect()
                    
                    # Agregar todos los vectores en batches
                    batch_size = 10000
                    for start in range(0, old_total, batch_size):
                        end = min(start + batch_size, old_total)
                        vectors = old_index.reconstruct_n(start, end - start)
                        new_index.add(vectors)
                        del vectors
                        gc.collect()
                else:
                    logger.warning("Índice anterior no soporta reconstruct_n, manteniendo estrategia actual")
                    return
            
            except Exception as e:
                logger.error(f"Error migrando a IVF+Flat", extra={"error": str(e)})
                return
        
        # Liberar old_index
        del old_index
        gc.collect()
        
        self.index = new_index
        self.current_strategy = "ivf_flat"
        logger.info(f"Migración a IVF+Flat completada: {self.index.ntotal} vectores")
    
    def _migrate_to_ivf_pq(self):
        """Migra a IVF+PQ (máxima compresión) con gestión de memoria"""
        old_index = self.index
        old_total = old_index.ntotal
        
        # Calcular número óptimo de clusters
        nlist = min(int(np.sqrt(old_total)), 4000)
        new_index = self._create_ivf_pq_index(nlist)
        
        if old_total >= 1000:
            try:
                # Entrenar con muestra grande
                train_size = min(50000, old_total)
                logger.info(f"Entrenando IVF+PQ con {train_size} vectores (puede tomar tiempo)")
                
                train_data = old_index.reconstruct_n(0, train_size)
                new_index.train(train_data)
                del train_data
                gc.collect()
                
                # Agregar en batches
                batch_size = 10000
                for start in range(0, old_total, batch_size):
                    end = min(start + batch_size, old_total)
                    vectors = old_index.reconstruct_n(start, end - start)
                    new_index.add(vectors)
                    del vectors
                    gc.collect()
                
                # Liberar old_index
                del old_index
                gc.collect()
                
                self.index = new_index
                self.current_strategy = "ivf_pq"
                logger.info(f"Migración a IVF+PQ completada: {self.index.ntotal} vectores (compresión 32x)")
            
            except Exception as e:
                logger.error("No se pudo migrar a IVF+PQ, manteniendo índice actual", extra={"error": str(e)})
    
    def add_papers(self, abstracts: List[str], metadata: List[Dict]):
        """Agrega papers con auto-upgrade y gestión de memoria"""
        if not abstracts or not metadata:
            logger.warning("add_papers llamado sin abstracts o metadata")
            return
        
        if len(abstracts) != len(metadata):
            logger.error("Longitud de abstracts y metadata no coincide")
            raise ValueError("abstracts y metadata deben tener la misma longitud")
        
        try:
            model = get_model()
            
            # Batch encoding optimizado
            embeddings = model.encode(
                abstracts,
                convert_to_tensor=False,
                show_progress_bar=False,
                batch_size=64,
                normalize_embeddings=True  # Normalización automática
            )
            
            embeddings = np.array(embeddings, dtype=np.float32)
            
            # Normalización adicional para inner product
            faiss.normalize_L2(embeddings)
            
            # Entrenar si es IVF y es primera vez
            if self.current_strategy.startswith("ivf") and not self.index.is_trained:
                if len(embeddings) >= 100:
                    logger.info("Entrenando índice IVF por primera vez")
                    self.index.train(embeddings)
                else:
                    logger.warning(f"Solo {len(embeddings)} vectores, se necesitan ≥100 para entrenar IVF")
            
            # Agregar al índice
            self.index.add(embeddings)
            self.metadata.extend(metadata)
            
            logger.info(f"Papers agregados exitosamente", extra={
                "added": len(abstracts),
                "total": self.index.ntotal,
                "strategy": self.current_strategy
            })
            
            # Auto-upgrade si es necesario
            self._auto_upgrade_index()
            
        except MemoryError:
            logger.error("Error de memoria detectado, forzando upgrade a IVF+PQ")
            self._migrate_to_ivf_pq()
            # Reintentar con nuevo índice
            try:
                self.add_papers(abstracts, metadata)
            except MemoryError:
                logger.critical("Error crítico de memoria, no se pudieron agregar papers")
                raise
        
        except Exception as e:
            logger.error("Error agregando papers", extra={"error": str(e), "type": type(e).__name__})
            raise
    
    def search(self, query: str, k: int = 10, threshold: float = 0.7) -> List[Dict]:
        """Búsqueda simple de un query"""
        if self.index.ntotal == 0:
            logger.warning("Búsqueda en índice vacío")
            return []
        
        try:
            model = get_model()
            
            # Embedding del query
            query_emb = model.encode(
                [query],
                convert_to_tensor=False,
                show_progress_bar=False,
                normalize_embeddings=True
            )
            
            query_emb = np.array(query_emb, dtype=np.float32)
            faiss.normalize_L2(query_emb)
            
            # Búsqueda
            k_search = min(k, self.index.ntotal)
            scores, indices = self.index.search(query_emb, k_search)
            
            # Construir resultados
            results = []
            for score, idx in zip(scores[0], indices[0]):
                if idx == -1:
                    continue
                
                similarity = float(score)
                if similarity >= threshold:
                    result = {
                        **self.metadata[int(idx)],
                        'porcentaje_match': round(similarity * 100, 1),
                        'faiss_similarity': similarity
                    }
                    results.append(result)
            
            logger.debug(f"Búsqueda completada", extra={"query": query[:50], "results": len(results)})
            return results
        
        except Exception as e:
            logger.error("Error en búsqueda", extra={"error": str(e)})
            return []
    
    def search_batch(self, queries: List[str], k: int = 10, threshold: float = 0.7) -> List[List[Dict]]:
        """Búsqueda batch optimizada con prefetching"""
        if self.index.ntotal == 0:
            logger.warning("Búsqueda batch en índice vacío")
            return [[] for _ in queries]
        
        try:
            model = get_model()
            
            # Batch encoding optimizado
            query_embs = model.encode(
                queries,
                convert_to_tensor=False,
                show_progress_bar=False,
                batch_size=64,
                normalize_embeddings=True
            )
            
            query_embs = np.array(query_embs, dtype=np.float32)
            faiss.normalize_L2(query_embs)
            
            # Búsqueda batch (FAISS optimizado internamente)
            k_search = min(k, self.index.ntotal)
            scores, indices = self.index.search(query_embs, k_search)
            
            # Construir resultados
            all_results = []
            for query_idx, (query_scores, query_indices) in enumerate(zip(scores, indices)):
                query_results = []
                for score, idx in zip(query_scores, query_indices):
                    if idx == -1:
                        continue
                    
                    similarity = float(score)
                    if similarity >= threshold:
                        result = {
                            **self.metadata[int(idx)],
                            'porcentaje_match': round(similarity * 100, 1),
                            'faiss_similarity': similarity
                        }
                        query_results.append(result)
                
                all_results.append(query_results)
            
            logger.debug(f"Búsqueda batch completada", extra={
                "queries": len(queries),
                "total_results": sum(len(r) for r in all_results)
            })
            
            return all_results
        
        except Exception as e:
            logger.error("Error en búsqueda batch", extra={"error": str(e)})
            return [[] for _ in queries]
    
    def save(self):
        """Guarda índice + estrategia en disco"""
        try:
            # Crear directorio si no existe
            os.makedirs(os.path.dirname(self.index_path) if os.path.dirname(self.index_path) else '.', exist_ok=True)
            
            # Guardar índice FAISS
            faiss.write_index(self.index, f"{self.index_path}.index")
            
            # Guardar metadata + estrategia
            save_data = {
                'metadata': self.metadata,
                'strategy': self.current_strategy,
                'dimension': self.dimension
            }
            
            with open(self.metadata_path, 'wb') as f:
                pickle.dump(save_data, f, protocol=pickle.HIGHEST_PROTOCOL)
            
            logger.info("Índice FAISS guardado", extra={
                "papers": self.index.ntotal,
                "strategy": self.current_strategy,
                "path": self.index_path
            })
        
        except Exception as e:
            logger.error("Error guardando índice FAISS", extra={"error": str(e)})
            raise
    
    def load(self):
        """Carga índice + estrategia desde disco"""
        try:
            index_file = f"{self.index_path}.index"
            
            if not os.path.exists(index_file) or not os.path.exists(self.metadata_path):
                logger.info("No se encontró índice existente, iniciando con índice vacío")
                return False
            
            # Cargar índice FAISS
            self.index = faiss.read_index(index_file)
            
            # Cargar metadata
            with open(self.metadata_path, 'rb') as f:
                save_data = pickle.load(f)
            
            self.metadata = save_data.get('metadata', [])
            self.current_strategy = save_data.get('strategy', 'flat')
            
            # Validar consistencia
            if self.index.ntotal != len(self.metadata):
                logger.warning("Inconsistencia detectada entre índice y metadata", extra={
                    "index_size": self.index.ntotal,
                    "metadata_size": len(self.metadata)
                })
                self._corrupted = True
            
            logger.info("Índice FAISS cargado exitosamente", extra={
                "papers": self.index.ntotal,
                "strategy": self.current_strategy
            })
            
            return True
        
        except Exception as e:
            logger.error("Error cargando índice FAISS", extra={"error": str(e)})
            self._corrupted = True
            return False
    
    def clear(self):
        """Limpia completamente el índice"""
        logger.warning("Limpiando índice FAISS completamente")
        
        self.index = self._create_small_index()
        self.metadata = []
        self.current_strategy = "flat"
        self._corrupted = False
        
        logger.info("Índice FAISS limpiado")
    
    def is_corrupted(self) -> bool:
        """Verifica si el índice está corrupto"""
        if self._corrupted:
            return True
        
        # Verificar consistencia
        if self.index.ntotal != len(self.metadata):
            self._corrupted = True
            return True
        
        return False
    
    def auto_repair(self):
        """Intenta reparar índice corrupto"""
        if not self.is_corrupted():
            logger.info("Índice no está corrupto, no es necesario reparar")
            return
        
        logger.warning("Intentando reparar índice corrupto")
        
        # Si hay más metadata que vectores, truncar metadata
        if len(self.metadata) > self.index.ntotal:
            logger.info(f"Truncando metadata de {len(self.metadata)} a {self.index.ntotal}")
            self.metadata = self.metadata[:self.index.ntotal]
        
        # Si hay más vectores que metadata, eliminar índice y reconstruir
        elif self.index.ntotal > len(self.metadata):
            logger.warning("Más vectores que metadata, limpiando índice")
            self.clear()
        
        self._corrupted = False
        self.save()
        logger.info("Reparación completada")
    
    def get_stats(self) -> Dict:
        """Estadísticas detalladas del índice"""
        # Calcular tamaño estimado
        if self.current_strategy == "ivf_pq":
            size_mb = self.index.ntotal * 48 / (1024 * 1024)  # PQ comprimido
        else:
            size_mb = self.index.ntotal * self.dimension * 4 / (1024 * 1024)
        
        is_trained = True
        if hasattr(self.index, 'is_trained'):
            is_trained = self.index.is_trained
        
        return {
            "total_papers": self.index.ntotal,
            "dimension": self.dimension,
            "index_size_mb": round(size_mb, 2),
            "metadata_count": len(self.metadata),
            "strategy": self.current_strategy,
            "is_trained": is_trained,
            "corrupted": self._corrupted,
            "estimated_search_ms": self._estimate_search_time()
        }
    
    def _estimate_search_time(self) -> float:
        """Estima tiempo de búsqueda en ms"""
        size = self.index.ntotal
        
        if self.current_strategy == "flat":
            return round(0.01 * size / 1000, 2)  # ~10ms por 1k vectores
        elif self.current_strategy == "hnsw":
            return 0.5  # ~0.5ms constante
        elif self.current_strategy == "ivf_flat":
            return 2.0  # ~2ms
        else:  # ivf_pq
            return 5.0  # ~5ms (por compresión)


# Instancia global
_faiss_index: Optional[FAISSIndex] = None


def get_faiss_index() -> Optional[FAISSIndex]:
    """Retorna instancia global del índice FAISS"""
    global _faiss_index
    
    if not FAISS_AVAILABLE:
        logger.warning("FAISS no está disponible")
        return None
    
    if _faiss_index is None:
        logger.warning("FAISS no ha sido inicializado, llame a init_faiss_index() primero")
    
    return _faiss_index


def init_faiss_index(dimension: int = 384, index_path: str = "data/faiss_index") -> Optional[FAISSIndex]:
    """Inicializa índice FAISS optimizado"""
    global _faiss_index
    
    if not FAISS_AVAILABLE:
        logger.error("FAISS no disponible. Instale con: pip install faiss-cpu")
        return None
    
    try:
        _faiss_index = FAISSIndex(dimension=dimension, index_path=index_path)
        logger.info("FAISS inicializado correctamente")
        return _faiss_index
    except Exception as e:
        logger.error("Error inicializando FAISS", extra={"error": str(e)})
        return None