# scripts/migrate_to_hnsw.py
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.repositories.faiss_repository import FAISSRepository, FAISSStrategy
from app.core.extensions import get_faiss_index

def migrate():
    """Migrar a HNSW"""
    print("🔄 Migrando a HNSW (ultra-rápido)...")
    
    faiss_repo = get_faiss_index()
    
    if faiss_repo.index.ntotal == 0:
        print("❌ No hay papers en el índice")
        return
    
    print(f"📊 Papers actuales: {faiss_repo.index.ntotal}")
    print(f"📊 Estrategia actual: {faiss_repo.current_strategy}")
    
    # Cambiar a HNSW
    faiss_repo.switch_strategy(FAISSStrategy.HNSW, rebuild=True)
    
    print("✅ Migración completada")
    print(f"   Estrategia: {faiss_repo.current_strategy}")
    print(f"   Papers: {faiss_repo.index.ntotal}")

if __name__ == '__main__':
    migrate()