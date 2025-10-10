"""
FAISS Service OPTIMIZADO con HNSW + IVF + PQ
"""
import os
import pickle
from typing import List, Dict, Optional
import numpy as np

try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False

from utils import get_model


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
            raise ImportError("FAISS no está instalado")
        
        self.dimension = dimension
        self.index_path = index_path
        self.metadata_path = f"{index_path}_metadata.pkl"
        
        # Iniciar con índice pequeño
        self.index = self._create_small_index()
        self.metadata = []
        self.current_strategy = "flat"
        
        self.load()
    
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
        if current_size < 10000 and self.current_strategy != "flat":
            return  # Ya está bien
        
        elif 10000 <= current_size < 100000 and self.current_strategy == "flat":
            print(f"🔄 Upgrade a HNSW ({current_size} vectores)")
            self._migrate_to_hnsw()
        
        elif 100000 <= current_size < 1000000 and self.current_strategy in ["flat", "hnsw"]:
            print(f"🔄 Upgrade a IVF+Flat ({current_size} vectores)")
            self._migrate_to_ivf_flat()
        
        elif current_size >= 1000000 and self.current_strategy != "ivf_pq":
            print(f"🔄 Upgrade a IVF+PQ ({current_size} vectores)")
            self._migrate_to_ivf_pq()
    
    def _migrate_to_hnsw(self):
        """Migra de Flat a HNSW"""
        old_index = self.index
        new_index = self._create_hnsw_index()
        
        # Copiar vectores
        if old_index.ntotal > 0:
            vectors = old_index.reconstruct_n(0, old_index.ntotal)
            new_index.add(vectors)
        
        self.index = new_index
        self.current_strategy = "hnsw"
        print(f"✅ Migrado a HNSW: {self.index.ntotal} vectores")
    
    def _migrate_to_ivf_flat(self):
        """Migra a IVF+Flat"""
        old_index = self.index
        nlist = min(int(np.sqrt(old_index.ntotal)), 1000)
        new_index = self._create_ivf_flat_index(nlist)
        
        # Entrenar con sample
        if old_index.ntotal >= 100:
            if hasattr(old_index, 'reconstruct_n'):
                train_data = old_index.reconstruct_n(0, min(10000, old_index.ntotal))
            else:
                # HNSW no tiene reconstruct, usar metadata
                print("⚠️ Reentrenamiento desde metadata (puede ser lento)")
                return
            
            new_index.train(train_data)
            
            # Agregar todos los vectores
            if old_index.ntotal > 0:
                all_vectors = old_index.reconstruct_n(0, old_index.ntotal)
                new_index.add(all_vectors)
        
        self.index = new_index
        self.current_strategy = "ivf_flat"
        print(f"✅ Migrado a IVF+Flat: {self.index.ntotal} vectores")
    
    def _migrate_to_ivf_pq(self):
        """Migra a IVF+PQ (máxima compresión)"""
        old_index = self.index
        nlist = min(int(np.sqrt(old_index.ntotal)), 4000)
        new_index = self._create_ivf_pq_index(nlist)
        
        # Similar a IVF+Flat pero con PQ
        if old_index.ntotal >= 1000:
            try:
                train_data = old_index.reconstruct_n(0, min(50000, old_index.ntotal))
                new_index.train(train_data)
                
                all_vectors = old_index.reconstruct_n(0, old_index.ntotal)
                new_index.add(all_vectors)
                
                self.index = new_index
                self.current_strategy = "ivf_pq"
                print(f"✅ Migrado a IVF+PQ: {self.index.ntotal} vectores (compresión 32x)")
            except:
                print("❌ No se pudo migrar a IVF+PQ, manteniendo índice actual")
    
    def add_papers(self, abstracts: List[str], metadata: List[Dict]):
        """Agrega papers con auto-upgrade"""
        if not abstracts:
            return
        
        try:
            model = get_model()
            embeddings = model.encode(
                abstracts,
                convert_to_tensor=False,
                show_progress_bar=False,
                batch_size=64  # Aumentado para mejor throughput
            )
            
            embeddings = np.array(embeddings, dtype=np.float32)
            faiss.normalize_L2(embeddings)
            
            # Entrenar si es IVF y es primera vez
            if self.current_strategy.startswith("ivf") and not self.index.is_trained:
                if len(embeddings) >= 100:
                    print("🎓 Entrenando índice IVF...")
                    self.index.train(embeddings)
            
            self.index.add(embeddings)
            self.metadata.extend(metadata)
            
            # Auto-upgrade si es necesario
            self._auto_upgrade_index()
            
            print(f"✅ Agregados {len(abstracts)} papers. Total: {self.index.ntotal} (estrategia: {self.current_strategy})")
            
        except MemoryError:
            print("❌ Error de memoria. Forzando upgrade a IVF+PQ...")
            self._migrate_to_ivf_pq()
            # Reintentar
            try:
                self.add_papers(abstracts, metadata)
            except:
                print("❌ Error crítico de memoria")
        except Exception as e:
            print(f"❌ Error agregando papers: {e}")
    
    def search_batch(self, queries: List[str], k: int = 10, threshold: float = 0.7) -> List[List[Dict]]:
        """Búsqueda batch optimizada con prefetching"""
        if self.index.ntotal == 0:
            return [[] for _ in queries]
        
        try:
            model = get_model()
            
            # Batch encoding optimizado
            query_embs = model.encode(
                queries,
                convert_to_tensor=False,
                show_progress_bar=False,
                batch_size=64
            )
            
            query_embs = np.array(query_embs, dtype=np.float32)
            faiss.normalize_L2(query_embs)
            
            # Búsqueda batch (FAISS optimizado internamente)
            k_search = min(k, self.index.ntotal)
            scores, indices = self.index.search(query_embs, k_search)
            
            # Construir resultados
            all_results = []
            for query_scores, query_indices in zip(scores, indices):
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
            
            return all_results
            
        except Exception as e:
            print(f"❌ Error en búsqueda batch: {e}")
            return [[] for _ in queries]
    
    def save(self):
        """Guarda índice + estrategia"""
        try:
            os.makedirs(os.path.dirname(self.index_path) if os.path.dirname(self.index_path) else '.', exist_ok=True)
            
            faiss.write_index(self.index, f"{self.index_path}.index")
            
            # Guardar metadata + estrategia
            save_data = {
                'metadata': self.metadata,
                'strategy': self.current_strategy
            }
            with open(self.metadata_path, 'wb') as f:
                pickle.dump(save_data, f, protocol=pickle.HIGHEST_PROTOCOL)
            
            print(f"💾 Índice guardado: {self.index.ntotal} papers (estrategia: {self.current_strategy})")
        except Exception as e:
            print(f"❌ Error guardando: {e}")
    
    def load(self):
        """Carga índice + estrategia"""
        try:
            index_file = f"{self.index_path}.index"
            
            if os.path.exists(index_file) and os.path.exists(self.metadata_path):
                self.index = faiss.read_index(index_file)
                
                with open(self.metadata_path, 'rb') as f:
                    save_data = pickle.load(f)
                
                self.metadata = save_data.get('metadata', [])
                self.current_strategy = save_data.get('strategy', 'flat')
                
                print(f"📂 Índice cargado: {self.index.ntotal} papers (estrategia: {self.current_strategy})")
                return True
        except Exception as e:
            print(f"⚠️ No se pudo cargar: {e}")
        
        return False
    
    def get_stats(self) -> Dict:
        """Estadísticas detalladas"""
        size_mb = self.index.ntotal * self.dimension * 4 / (1024 * 1024)
        
        # Calcular compresión según estrategia
        if self.current_strategy == "ivf_pq":
            size_mb = self.index.ntotal * 48 / (1024 * 1024)  # PQ comprimido
        
        return {
            "total_papers": self.index.ntotal,
            "dimension": self.dimension,
            "index_size_mb": round(size_mb, 2),
            "metadata_count": len(self.metadata),
            "strategy": self.current_strategy,
            "is_trained": self.index.is_trained if hasattr(self.index, 'is_trained') else True,
            "estimated_search_ms": self._estimate_search_time()
        }
    
    def _estimate_search_time(self) -> float:
        """Estima tiempo de búsqueda"""
        size = self.index.ntotal
        
        if self.current_strategy == "flat":
            return 0.01 * size / 1000  # ~10ms por 1k vectores
        elif self.current_strategy == "hnsw":
            return 0.5  # ~0.5ms constante
        elif self.current_strategy == "ivf_flat":
            return 2.0  # ~2ms
        else:  # ivf_pq
            return 5.0  # ~5ms (por compresión)


# Instancia global
_faiss_index: Optional[FAISSIndex] = None


def get_faiss_index() -> Optional[FAISSIndex]:
    """Retorna instancia optimizada"""
    global _faiss_index
    
    if not FAISS_AVAILABLE:
        return None
    
    if _faiss_index is None:
        try:
           _faiss_index = FAISSIndex()
        except Exception as e:
            print(f"❌ Error inicializando FAISS optimizado: {e}")
            return None
    
    return _faiss_index


def init_faiss_index(dimension: int = 384, index_path: str = "data/faiss_index"):
    """Inicializa índice optimizado"""
    global _faiss_index
    
    if not FAISS_AVAILABLE:
        print("⚠️ FAISS no disponible")
        return None
    
    try:
        _faiss_index = FAISSIndex(dimension=dimension, index_path=index_path)
        print("✅ FAISS optimizado inicializado")
        return _faiss_index
    except Exception as e:
        print(f"❌ Error: {e}")
        return None