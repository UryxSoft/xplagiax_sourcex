"""
Servicio de búsqueda vectorial con FAISS
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
    print("⚠️ FAISS no disponible. Instalar con: pip install faiss-cpu")

from utils import get_model


class FAISSIndex:
    """
    Índice FAISS para búsqueda rápida de similitud vectorial
    """
    def __init__(self, dimension: int = 384, index_path: str = "faiss_index", use_compression: bool = False):
        """
        Args:
            dimension: Dimensión de los embeddings (384 para all-MiniLM-L6-v2)
            index_path: Ruta para guardar/cargar el índice
            use_compression: Usar compresión para ahorrar memoria
        """
        if not FAISS_AVAILABLE:
            raise ImportError("FAISS no está instalado")
        
        self.dimension = dimension
        self.index_path = index_path
        self.metadata_path = f"{index_path}_metadata.pkl"
        self.use_compression = use_compression
        
        # Seleccionar tipo de índice según memoria disponible
        if use_compression:
            # Índice con compresión (ahorra 4x memoria)
            print("🗜️ Usando índice FAISS con compresión")
            nlist = 100  # Número de clusters
            quantizer = faiss.IndexFlatIP(dimension)
            self.index = faiss.IndexIVFFlat(quantizer, dimension, nlist)
            self.needs_training = True
        else:
            # Índice simple y rápido
            self.index = faiss.IndexFlatIP(dimension)
            self.needs_training = False
        
        self.metadata = []  # Lista de diccionarios con info de papers
        
        # Cargar índice existente si está disponible
        self.load()
    
    def add_papers(self, abstracts: List[str], metadata: List[Dict]):
        """
        Agrega papers al índice FAISS
        
        Args:
            abstracts: Lista de abstracts/textos
            metadata: Lista de diccionarios con info (title, author, source, etc)
        """
        if not abstracts:
            return
        
        try:
            # Generar embeddings
            model = get_model()
            embeddings = model.encode(
                abstracts,
                convert_to_tensor=False,
                show_progress_bar=False
            )
            
            # Normalizar para similitud coseno
            embeddings = np.array(embeddings, dtype=np.float32)
            faiss.normalize_L2(embeddings)
            
            # Entrenar índice si es necesario (solo primera vez con compresión)
            if self.needs_training and self.index.ntotal == 0:
                if len(embeddings) >= 100:
                    print("🎓 Entrenando índice FAISS...")
                    self.index.train(embeddings)
                    self.needs_training = False
                else:
                    print(f"⚠️ Necesita al menos 100 vectores para entrenar, tienes {len(embeddings)}")
                    return
            
            # Agregar al índice
            self.index.add(embeddings)
            self.metadata.extend(metadata)
            
            print(f"✅ Agregados {len(abstracts)} papers. Total: {self.index.ntotal}")
            
        except MemoryError:
            print("❌ Error de memoria. Limpiando índice y cambiando a modo compresión...")
            self.handle_memory_error()
        except Exception as e:
            print(f"❌ Error agregando papers: {e}")
    
    def handle_memory_error(self):
        """Maneja errores de memoria automáticamente"""
        print("🔧 Reconstruyendo índice con compresión...")
        
        # Guardar metadata actual
        old_metadata = self.metadata.copy()
        
        # Recrear índice con compresión
        nlist = 100
        quantizer = faiss.IndexFlatIP(self.dimension)
        self.index = faiss.IndexIVFFlat(quantizer, self.dimension, nlist)
        self.use_compression = True
        self.needs_training = True
        self.metadata = []
        
        # Intentar re-agregar datos en lotes
        batch_size = 100
        for i in range(0, len(old_metadata), batch_size):
            batch_meta = old_metadata[i:i+batch_size]
            abstracts = [m.get('abstract', '') for m in batch_meta if m.get('abstract')]
            if abstracts:
                try:
                    self.add_papers(abstracts, batch_meta)
                except:
                    print(f"⚠️ No se pudo recuperar batch {i}-{i+batch_size}")
                    break
        
        print(f"✅ Índice reconstruido con {self.index.ntotal} papers")
    
    def search(self, query: str, k: int = 10, threshold: float = 0.7) -> List[Dict]:
        """
        Busca los k papers más similares
        
        Args:
            query: Texto de búsqueda
            k: Número de resultados
            threshold: Umbral mínimo de similitud (0-1)
        
        Returns:
            Lista de diccionarios con resultados y scores
        """
        if self.index.ntotal == 0:
            return []
        
        try:
            # Generar embedding de la query
            model = get_model()
            query_emb = model.encode(
                [query],
                convert_to_tensor=False,
                show_progress_bar=False
            )
            
            # Normalizar
            query_emb = np.array(query_emb, dtype=np.float32)
            faiss.normalize_L2(query_emb)
            
            # Buscar en FAISS
            k_search = min(k, self.index.ntotal)
            scores, indices = self.index.search(query_emb, k_search)
            
            # Construir resultados
            results = []
            for score, idx in zip(scores[0], indices[0]):
                if idx == -1:  # FAISS retorna -1 si no hay suficientes resultados
                    continue
                
                similarity = float(score)
                
                # Filtrar por threshold
                if similarity >= threshold:
                    result = {
                        **self.metadata[int(idx)],
                        'porcentaje_match': round(similarity * 100, 1),
                        'faiss_similarity': similarity
                    }
                    results.append(result)
            
            return results
            
        except Exception as e:
            print(f"❌ Error en búsqueda FAISS: {e}")
            return []
    
    def search_batch(self, queries: List[str], k: int = 10, threshold: float = 0.7) -> List[List[Dict]]:
        """
        Busca múltiples queries en batch (más eficiente)
        
        Args:
            queries: Lista de textos de búsqueda
            k: Número de resultados por query
            threshold: Umbral mínimo de similitud
        
        Returns:
            Lista de listas con resultados por query
        """
        if self.index.ntotal == 0:
            return [[] for _ in queries]
        
        try:
            # Generar embeddings en batch
            model = get_model()
            query_embs = model.encode(
                queries,
                convert_to_tensor=False,
                show_progress_bar=False,
                batch_size=32
            )
            
            # Normalizar
            query_embs = np.array(query_embs, dtype=np.float32)
            faiss.normalize_L2(query_embs)
            
            # Buscar en FAISS (batch)
            k_search = min(k, self.index.ntotal)
            scores, indices = self.index.search(query_embs, k_search)
            
            # Construir resultados por query
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
            print(f"❌ Error en búsqueda batch FAISS: {e}")
            return [[] for _ in queries]
    
    def save(self):
        """Guarda el índice y metadata en disco"""
        try:
            # Crear directorio si no existe
            os.makedirs(os.path.dirname(self.index_path) if os.path.dirname(self.index_path) else '.', exist_ok=True)
            
            # Guardar índice FAISS
            faiss.write_index(self.index, f"{self.index_path}.index")
            
            # Guardar metadata
            with open(self.metadata_path, 'wb') as f:
                pickle.dump(self.metadata, f, protocol=pickle.HIGHEST_PROTOCOL)
            
            print(f"💾 Índice guardado: {self.index.ntotal} papers")
        except Exception as e:
            print(f"❌ Error guardando índice: {e}")
    
    def load(self):
        """Carga el índice y metadata desde disco"""
        try:
            index_file = f"{self.index_path}.index"
            
            if os.path.exists(index_file) and os.path.exists(self.metadata_path):
                # Cargar índice FAISS
                self.index = faiss.read_index(index_file)
                self.needs_training = False
                
                # Cargar metadata
                with open(self.metadata_path, 'rb') as f:
                    self.metadata = pickle.load(f)
                
                print(f"📂 Índice cargado: {self.index.ntotal} papers")
                return True
        except Exception as e:
            print(f"⚠️ No se pudo cargar índice: {e}")
            print("🔨 Creando índice nuevo...")
        
        return False
    
    def clear(self):
        """Limpia el índice completamente"""
        if self.use_compression:
            nlist = 100
            quantizer = faiss.IndexFlatIP(self.dimension)
            self.index = faiss.IndexIVFFlat(quantizer, self.dimension, nlist)
            self.needs_training = True
        else:
            self.index = faiss.IndexFlatIP(self.dimension)
            self.needs_training = False
        
        self.metadata = []
        print("🗑️ Índice limpiado")
    
    def is_corrupted(self) -> bool:
        """Verifica si el índice está corrupto"""
        try:
            if self.index.ntotal != len(self.metadata):
                print(f"⚠️ Desincronización: {self.index.ntotal} vectores vs {len(self.metadata)} metadata")
                return True
            return False
        except:
            return True
    
    def auto_repair(self):
        """Repara automáticamente el índice si está corrupto"""
        if self.is_corrupted():
            print("🔧 Reparando índice corrupto...")
            self.clear()
            print("✅ Índice reparado. Se reconstruirá con nuevas búsquedas.")
    
    def get_stats(self) -> Dict:
        """Retorna estadísticas del índice"""
        return {
            "total_papers": self.index.ntotal,
            "dimension": self.dimension,
            "index_size_mb": round(self.index.ntotal * self.dimension * 4 / (1024 * 1024), 2),
            "metadata_count": len(self.metadata),
            "compression_enabled": self.use_compression,
            "is_trained": not self.needs_training if self.use_compression else True,
            "corrupted": self.is_corrupted()
        }


# Instancia global
_faiss_index: Optional[FAISSIndex] = None


def get_faiss_index() -> Optional[FAISSIndex]:
    """Retorna instancia global de FAISS"""
    global _faiss_index
    
    if not FAISS_AVAILABLE:
        return None
    
    if _faiss_index is None:
        try:
            _faiss_index = FAISSIndex()
            # Auto-reparar si está corrupto
            if _faiss_index.is_corrupted():
                _faiss_index.auto_repair()
        except Exception as e:
            print(f"❌ Error inicializando FAISS: {e}")
            return None
    
    return _faiss_index


def init_faiss_index(dimension: int = 384, index_path: str = "data/faiss_index", use_compression: bool = False):
    """Inicializa el índice FAISS global"""
    global _faiss_index
    
    if not FAISS_AVAILABLE:
        print("⚠️ FAISS no disponible")
        return None
    
    try:
        _faiss_index = FAISSIndex(dimension=dimension, index_path=index_path, use_compression=use_compression)
        
        # Auto-reparar si está corrupto
        if _faiss_index.is_corrupted():
            _faiss_index.auto_repair()
        
        print("✅ FAISS inicializado")
        return _faiss_index
    except Exception as e:
        print(f"❌ Error inicializando FAISS: {e}")
        return None