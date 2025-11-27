#!/usr/bin/env python3
"""
Migrate FAISS Index - Rebuild, upgrade, or convert FAISS index

Usage:
    python scripts/migrate_faiss.py rebuild
    python scripts/migrate_faiss.py upgrade --strategy ivf_pq
    python scripts/migrate_faiss.py backup
    python scripts/migrate_faiss.py restore --backup backups/faiss_20231201_120000
"""
import sys
import os
import argparse
import shutil
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.services.faiss_service import FAISSService
from app.services.text_processing.embeddings import EmbeddingService
from app.repositories.faiss_repository import FAISSRepository
from app.models.enums import FAISSStrategy
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def backup_index(
    index_path: str = 'data/faiss_index.index',
    metadata_path: str = 'data/faiss_index_metadata.pkl',
    backup_dir: str = 'backups'
):
    """
    Create backup of FAISS index
    
    Args:
        index_path: Path to FAISS index file
        metadata_path: Path to metadata file
        backup_dir: Directory to store backups
    
    Returns:
        Path to backup directory
    """
    # Create backup directory with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = os.path.join(backup_dir, f'faiss_{timestamp}')
    
    os.makedirs(backup_path, exist_ok=True)
    
    logger.info(f"📦 Creating backup: {backup_path}")
    
    # Copy index file
    if os.path.exists(index_path):
        shutil.copy2(index_path, backup_path)
        logger.info(f"  ✅ Copied {index_path}")
    else:
        logger.warning(f"  ⚠️  Index file not found: {index_path}")
    
    # Copy metadata file
    if os.path.exists(metadata_path):
        shutil.copy2(metadata_path, backup_path)
        logger.info(f"  ✅ Copied {metadata_path}")
    else:
        logger.warning(f"  ⚠️  Metadata file not found: {metadata_path}")
    
    logger.info(f"✅ Backup created: {backup_path}")
    
    return backup_path


def restore_index(
    backup_path: str,
    index_path: str = 'data/faiss_index.index',
    metadata_path: str = 'data/faiss_index_metadata.pkl'
):
    """
    Restore FAISS index from backup
    
    Args:
        backup_path: Path to backup directory
        index_path: Destination path for index file
        metadata_path: Destination path for metadata file
    """
    logger.info(f"📥 Restoring from backup: {backup_path}")
    
    # Restore index file
    backup_index = os.path.join(backup_path, os.path.basename(index_path))
    if os.path.exists(backup_index):
        shutil.copy2(backup_index, index_path)
        logger.info(f"  ✅ Restored {index_path}")
    else:
        logger.error(f"  ❌ Backup index not found: {backup_index}")
        return False
    
    # Restore metadata file
    backup_metadata = os.path.join(backup_path, os.path.basename(metadata_path))
    if os.path.exists(backup_metadata):
        shutil.copy2(backup_metadata, metadata_path)
        logger.info(f"  ✅ Restored {metadata_path}")
    else:
        logger.error(f"  ❌ Backup metadata not found: {backup_metadata}")
        return False
    
    logger.info("✅ Restore completed")
    return True


def rebuild_index(
    dimension: int = 384,
    strategy: str = 'flat_idmap'
):
    """
    Rebuild FAISS index from metadata
    
    Args:
        dimension: Embedding dimension
        strategy: FAISS strategy to use
    """
    logger.info(f"🔨 Rebuilding FAISS index...")
    logger.info(f"  Strategy: {strategy}")
    logger.info(f"  Dimension: {dimension}")
    
    # Create backup first
    backup_path = backup_index()
    
    try:
        # Initialize embedding service
        logger.info("📊 Initializing embedding service...")
        embedding_service = EmbeddingService()
        
        # Initialize FAISS service
        faiss_strategy = FAISSStrategy(strategy)
        faiss_service = FAISSService(
            dimension=dimension,
            strategy=faiss_strategy
        )
        
        # Get stats before rebuild
        stats_before = faiss_service.get_stats()
        logger.info(f"\n📈 Stats before rebuild:")
        logger.info(f"  Total papers: {stats_before.get('total_papers', 0)}")
        logger.info(f"  Metadata count: {stats_before.get('metadata_count', 0)}")
        logger.info(f"  Strategy: {stats_before.get('strategy', 'unknown')}")
        
        # Rebuild
        logger.info("\n🔄 Rebuilding index from metadata...")
        
        import asyncio
        success = asyncio.run(faiss_service.rebuild(embedding_service))
        
        if not success:
            logger.error("❌ Rebuild failed")
            logger.info(f"💾 Backup available at: {backup_path}")
            return False
        
        # Get stats after rebuild
        stats_after = faiss_service.get_stats()
        logger.info(f"\n📈 Stats after rebuild:")
        logger.info(f"  Total papers: {stats_after.get('total_papers', 0)}")
        logger.info(f"  Metadata count: {stats_after.get('metadata_count', 0)}")
        logger.info(f"  Strategy: {stats_after.get('strategy', 'unknown')}")
        logger.info(f"  Corrupted: {stats_after.get('corrupted', False)}")
        
        logger.info(f"\n✅ Rebuild completed successfully!")
        logger.info(f"💾 Backup available at: {backup_path}")
        
        return True
    
    except Exception as e:
        logger.error(f"❌ Error during rebuild: {e}", exc_info=True)
        logger.info(f"💾 Backup available at: {backup_path}")
        
        # Ask if user wants to restore
        response = input("\n🔙 Restore from backup? (yes/no): ")
        if response.lower() == 'yes':
            restore_index(backup_path)
        
        return False


def upgrade_strategy(
    new_strategy: str,
    dimension: int = 384
):
    """
    Upgrade FAISS index to new strategy
    
    Args:
        new_strategy: New FAISS strategy
        dimension: Embedding dimension
    """
    logger.info(f"⬆️  Upgrading FAISS index to strategy: {new_strategy}")
    
    # Validate strategy
    try:
        strategy_enum = FAISSStrategy(new_strategy)
    except ValueError:
        logger.error(f"❌ Invalid strategy: {new_strategy}")
        logger.info(f"Valid strategies: {[s.value for s in FAISSStrategy]}")
        return False
    
    # Create backup first
    backup_path = backup_index()
    
    try:
        # Load current index
        logger.info("📂 Loading current index...")
        current_repo = FAISSRepository()
        current_repo.load()
        
        stats = current_repo.get_stats()
        logger.info(f"\n📊 Current index:")
        logger.info(f"  Papers: {stats['total_papers']}")
        logger.info(f"  Strategy: {stats['strategy']}")
        
        # Get all papers and embeddings
        logger.info("\n📥 Extracting papers and embeddings...")
        all_papers = current_repo.get_all_papers()
        
        if not all_papers:
            logger.warning("⚠️  No papers found in index")
            return False
        
        # Generate embeddings
        logger.info("🔢 Regenerating embeddings...")
        embedding_service = EmbeddingService()
        
        texts = [
            p.get('abstract', p.get('title', ''))
            for p in all_papers
        ]
        
        embeddings = embedding_service.encode(texts, show_progress=True)
        
        # Create new index with new strategy
        logger.info(f"\n🔨 Creating new index with strategy: {new_strategy}")
        new_repo = FAISSRepository(
            dimension=dimension,
            strategy=strategy_enum
        )
        
        # Add papers
        logger.info("📝 Adding papers to new index...")
        new_repo.add(embeddings, all_papers)
        
        # Save new index
        logger.info("💾 Saving new index...")
        new_repo.save()
        
        # Show new stats
        new_stats = new_repo.get_stats()
        logger.info(f"\n📊 New index:")
        logger.info(f"  Papers: {new_stats['total_papers']}")
        logger.info(f"  Strategy: {new_stats['strategy']}")
        
        logger.info(f"\n✅ Upgrade completed successfully!")
        logger.info(f"💾 Backup available at: {backup_path}")
        
        return True
    
    except Exception as e:
        logger.error(f"❌ Error during upgrade: {e}", exc_info=True)
        logger.info(f"💾 Backup available at: {backup_path}")
        
        response = input("\n🔙 Restore from backup? (yes/no): ")
        if response.lower() == 'yes':
            restore_index(backup_path)
        
        return False


def show_info():
    """Show FAISS index information"""
    try:
        repository = FAISSRepository()
        repository.load()
        
        stats = repository.get_stats()
        
        logger.info("\n📊 FAISS Index Information:")
        logger.info(f"  Total papers: {stats['total_papers']}")
        logger.info(f"  Dimension: {stats['dimension']}")
        logger.info(f"  Metadata count: {stats['metadata_count']}")
        logger.info(f"  Strategy: {stats['strategy']}")
        logger.info(f"  Supports removal: {stats['supports_removal']}")
        logger.info(f"  Is approximate: {stats['is_approximate']}")
        logger.info(f"  Corrupted: {stats['corrupted']}")
        
        # File sizes
        index_path = repository.index_path
        metadata_path = repository.metadata_path
        
        if os.path.exists(index_path):
            index_size = os.path.getsize(index_path) / (1024 * 1024)
            logger.info(f"\n  Index file: {index_size:.2f} MB")
        
        if os.path.exists(metadata_path):
            metadata_size = os.path.getsize(metadata_path) / (1024 * 1024)
            logger.info(f"  Metadata file: {metadata_size:.2f} MB")
        
        return True
    
    except Exception as e:
        logger.error(f"❌ Error loading index: {e}")
        return False


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Migrate FAISS index'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Rebuild command
    rebuild_parser = subparsers.add_parser('rebuild', help='Rebuild index from metadata')
    rebuild_parser.add_argument('--strategy', default='flat_idmap', help='FAISS strategy')
    rebuild_parser.add_argument('--dimension', type=int, default=384, help='Embedding dimension')
    
    # Upgrade command
    upgrade_parser = subparsers.add_parser('upgrade', help='Upgrade to new strategy')
    upgrade_parser.add_argument('--strategy', required=True, help='New FAISS strategy')
    upgrade_parser.add_argument('--dimension', type=int, default=384, help='Embedding dimension')
    
    # Backup command
    backup_parser = subparsers.add_parser('backup', help='Create backup')
    
    # Restore command
    restore_parser = subparsers.add_parser('restore', help='Restore from backup')
    restore_parser.add_argument('--backup', required=True, help='Backup directory path')
    
    # Info command
    info_parser = subparsers.add_parser('info', help='Show index information')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        if args.command == 'rebuild':
            success = rebuild_index(
                dimension=args.dimension,
                strategy=args.strategy
            )
            sys.exit(0 if success else 1)
        
        elif args.command == 'upgrade':
            success = upgrade_strategy(
                new_strategy=args.strategy,
                dimension=args.dimension
            )
            sys.exit(0 if success else 1)
        
        elif args.command == 'backup':
            backup_path = backup_index()
            logger.info(f"\n✅ Backup created: {backup_path}")
        
        elif args.command == 'restore':
            success = restore_index(args.backup)
            sys.exit(0 if success else 1)
        
        elif args.command == 'info':
            success = show_info()
            sys.exit(0 if success else 1)
    
    except Exception as e:
        logger.error(f"\n❌ Error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()