#!/usr/bin/env python3
"""
Initialize Database - Setup SQLite database with tables

Usage:
    python scripts/init_db.py
    python scripts/init_db.py --drop  # Drop existing tables first
    python scripts/init_db.py --seed  # Add seed data
"""
import sys
import os
import argparse
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.repositories.sqlite_repository import SQLiteRepository
from app.services.deduplication_service import DeduplicationService
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def drop_tables(db_path: str):
    """
    Drop all tables (DESTRUCTIVE)
    
    Args:
        db_path: Path to database file
    """
    import sqlite3
    
    logger.warning(f"🗑️  Dropping all tables from {db_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    
    for table in tables:
        table_name = table[0]
        logger.info(f"Dropping table: {table_name}")
        cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
    
    conn.commit()
    conn.close()
    
    logger.info("✅ All tables dropped")


def init_database(db_path: str):
    """
    Initialize database with tables
    
    Args:
        db_path: Path to database file
    """
    logger.info(f"📦 Initializing database: {db_path}")
    
    # Create data directory if needed
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    # Initialize repository (creates tables)
    repository = SQLiteRepository(db_path=db_path)
    
    logger.info("✅ Database initialized successfully")
    
    # Show table info
    import sqlite3
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    
    logger.info("\n📋 Tables created:")
    for table in tables:
        table_name = table[0]
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]
        logger.info(f"  - {table_name}: {count} rows")
    
    conn.close()


def seed_database(db_path: str):
    """
    Add seed/sample data to database
    
    Args:
        db_path: Path to database file
    """
    logger.info("🌱 Seeding database with sample data...")
    
    repository = SQLiteRepository(db_path=db_path)
    
    # Sample papers
    sample_papers = [
        {
            'title': 'Deep Learning for Image Classification',
            'authors': 'John Doe, Jane Smith',
            'abstract': 'This paper presents a novel approach to image classification using deep neural networks.',
            'doi': '10.1234/example.001',
            'url': 'https://example.com/paper1',
            'date': '2023-01-15',
            'type': 'article',
            'source': 'arxiv',
            'content_hash': 'hash001'
        },
        {
            'title': 'Natural Language Processing with Transformers',
            'authors': 'Alice Johnson, Bob Williams',
            'abstract': 'We explore the application of transformer models to various NLP tasks.',
            'doi': '10.1234/example.002',
            'url': 'https://example.com/paper2',
            'date': '2023-02-20',
            'type': 'article',
            'source': 'semantic_scholar',
            'content_hash': 'hash002'
        },
        {
            'title': 'Reinforcement Learning in Robotics',
            'authors': 'Charlie Brown, Diana Prince',
            'abstract': 'This research investigates the use of reinforcement learning for robot control.',
            'doi': '10.1234/example.003',
            'url': 'https://example.com/paper3',
            'date': '2023-03-10',
            'type': 'conference',
            'source': 'crossref',
            'content_hash': 'hash003'
        },
        {
            'title': 'Quantum Computing Applications',
            'authors': 'Eve Anderson, Frank Miller',
            'abstract': 'We present novel applications of quantum computing in optimization problems.',
            'doi': '10.1234/example.004',
            'url': 'https://example.com/paper4',
            'date': '2023-04-05',
            'type': 'article',
            'source': 'pubmed',
            'content_hash': 'hash004'
        },
        {
            'title': 'Climate Change Modeling with Machine Learning',
            'authors': 'Grace Lee, Henry Davis',
            'abstract': 'This study applies machine learning techniques to climate change prediction.',
            'doi': '10.1234/example.005',
            'url': 'https://example.com/paper5',
            'date': '2023-05-12',
            'type': 'article',
            'source': 'openalex',
            'content_hash': 'hash005'
        }
    ]
    
    # Add papers
    added = repository.add_papers_batch(sample_papers)
    logger.info(f"✅ Added {added} sample papers")
    
    # Add sample search history
    search_entries = [
        ('machine learning', 'AI', 'en', 0.70, 15, 234.5),
        ('neural networks', 'Deep Learning', 'en', 0.75, 8, 156.3),
        ('natural language processing', 'NLP', 'en', 0.70, 12, 189.7),
    ]
    
    for entry in search_entries:
        repository.log_search(*entry)
    
    logger.info(f"✅ Added {len(search_entries)} search history entries")
    
    logger.info("🌱 Database seeding completed")


def show_stats(db_path: str):
    """
    Show database statistics
    
    Args:
        db_path: Path to database file
    """
    repository = SQLiteRepository(db_path=db_path)
    
    logger.info("\n📊 Database Statistics:")
    logger.info(f"  Total papers: {repository.get_total_papers()}")
    
    source_counts = repository.get_papers_by_source_count()
    logger.info("\n  Papers by source:")
    for source, count in source_counts.items():
        logger.info(f"    - {source}: {count}")
    
    search_stats = repository.get_search_stats()
    logger.info(f"\n  Search statistics:")
    logger.info(f"    - Total searches: {search_stats.get('total_searches', 0)}")
    logger.info(f"    - Avg search time: {search_stats.get('avg_search_time_ms', 0):.2f}ms")
    logger.info(f"    - Avg results: {search_stats.get('avg_results_count', 0):.2f}")
    
    db_size = repository.get_db_size_mb()
    logger.info(f"\n  Database size: {db_size:.2f} MB")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Initialize xplagiax database'
    )
    
    parser.add_argument(
        '--db-path',
        default='data/xplagiax.db',
        help='Path to database file (default: data/xplagiax.db)'
    )
    
    parser.add_argument(
        '--drop',
        action='store_true',
        help='Drop existing tables before creating new ones (DESTRUCTIVE)'
    )
    
    parser.add_argument(
        '--seed',
        action='store_true',
        help='Add seed/sample data after initialization'
    )
    
    parser.add_argument(
        '--stats',
        action='store_true',
        help='Show database statistics'
    )
    
    args = parser.parse_args()
    
    try:
        # Drop tables if requested
        if args.drop:
            response = input("⚠️  This will DELETE all data. Continue? (yes/no): ")
            if response.lower() != 'yes':
                logger.info("Aborted.")
                return
            
            drop_tables(args.db_path)
        
        # Initialize database
        init_database(args.db_path)
        
        # Seed data if requested
        if args.seed:
            seed_database(args.db_path)
        
        # Show stats if requested
        if args.stats or args.seed:
            show_stats(args.db_path)
        
        logger.info("\n✅ Database initialization completed successfully!")
    
    except Exception as e:
        logger.error(f"\n❌ Error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()