#!/usr/bin/env python3
"""
Script para migrar FAISS metadata de pickle a msgpack

# Hacer backup y migrar
python scripts/migrate_faiss_msgpack.py --backup

# Solo migrar sin reemplazar
python scripts/migrate_faiss_msgpack.py --input data/faiss_index_metadata.pkl --output data/faiss_msgpack.pkl
"""
import os
import sys
import pickle
import argparse

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.utils.serialization import dumps_msgpack
from app.models.enums import FAISSStrategy

def migrate_faiss_metadata(old_path: str, new_path: str):
    """Migrar metadata de pickle a msgpack"""
    
    print(f"🔄 Migrando FAISS metadata...")
    print(f"   Origen: {old_path}")
    print(f"   Destino: {new_path}")
    
    try:
        # Leer pickle viejo
        with open(old_path, 'rb') as f:
            old_data = pickle.load(f)
        
        print(f"✅ Pickle cargado: {len(old_data.get('metadata', {}))} entries")
        
        # Convertir a formato msgpack
        new_data = {
            'metadata': {
                str(k): v for k, v in old_data.get('metadata', {}).items()
            },
            'strategy': old_data.get('strategy', FAISSStrategy.FLAT_IDMAP.value),
            'dimension': old_data.get('dimension', 384),
            'version': '2.1.0'
        }
        
        # Guardar con msgpack
        with open(new_path, 'wb') as f:
            f.write(dumps_msgpack(new_data))
        
        print(f"✅ Migración completada")
        print(f"   Papers: {len(new_data['metadata'])}")
        print(f"   Strategy: {new_data['strategy']}")
        print(f"   Dimension: {new_data['dimension']}")
        
        # Comparar tamaños
        old_size = os.path.getsize(old_path)
        new_size = os.path.getsize(new_path)
        reduction = (1 - new_size/old_size) * 100
        
        print(f"\n📊 Comparación de tamaño:")
        print(f"   Pickle: {old_size/1024/1024:.2f} MB")
        print(f"   Msgpack: {new_size/1024/1024:.2f} MB")
        print(f"   Reducción: {reduction:.1f}%")
        
        return True
    
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Migrate FAISS metadata to msgpack')
    parser.add_argument('--input', default='data/faiss_index_metadata.pkl')
    parser.add_argument('--output', default='data/faiss_index_metadata_new.pkl')
    parser.add_argument('--backup', action='store_true', help='Backup old file')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.input):
        print(f"❌ File not found: {args.input}")
        sys.exit(1)
    
    # Migrar
    success = migrate_faiss_metadata(args.input, args.output)
    
    if success and args.backup:
        backup_path = args.input + '.backup'
        os.rename(args.input, backup_path)
        os.rename(args.output, args.input)
        print(f"✅ Backup creado: {backup_path}")
        print(f"✅ Archivo reemplazado: {args.input}")
    
    sys.exit(0 if success else 1)