#!/usr/bin/env python3
"""
Generate Test Data - Create sample papers and embeddings for testing

Usage:
    python scripts/generate_test_data.py --papers 100
    python scripts/generate_test_data.py --papers 1000 --output test_data.json
    python scripts/generate_test_data.py --load-to-faiss test_data.json
"""
import sys
import os
import json
import argparse
from pathlib import Path
from datetime import datetime, timedelta
import random

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Sample data for generation
TOPICS = [
    "machine learning", "deep learning", "natural language processing",
    "computer vision", "reinforcement learning", "neural networks",
    "artificial intelligence", "data mining", "big data",
    "cloud computing", "cybersecurity", "blockchain",
    "quantum computing", "robotics", "bioinformatics"
]

TITLES_TEMPLATES = [
    "A Novel Approach to {topic} using {method}",
    "Improving {topic} with {method}",
    "Deep {method} for {topic}",
    "{method}-based {topic}: A Comprehensive Study",
    "Advances in {topic} through {method}",
    "Scalable {topic} using {method}",
    "Efficient {method} for {topic} Applications"
]

METHODS = [
    "Convolutional Networks", "Transformer Models", "Graph Neural Networks",
    "Generative Adversarial Networks", "Attention Mechanisms",
    "Transfer Learning", "Meta-Learning", "Few-Shot Learning",
    "Federated Learning", "Self-Supervised Learning"
]

FIRST_NAMES = [
    "John", "Jane", "Alice", "Bob", "Charlie", "Diana",
    "Eve", "Frank", "Grace", "Henry", "Iris", "Jack",
    "Kate", "Leo", "Mary", "Nick", "Olivia", "Peter"
]

LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia",
    "Miller", "Davis", "Rodriguez", "Martinez", "Hernandez",
    "Lopez", "Wilson", "Anderson", "Thomas", "Taylor"
]

SOURCES = [
    "arxiv", "semantic_scholar", "crossref", "pubmed",
    "openalex", "europepmc", "doaj", "zenodo"
]

ABSTRACT_TEMPLATES = [
    "This paper presents a comprehensive study of {topic}. We propose a novel {method} approach that significantly improves performance over existing methods. Our experiments demonstrate state-of-the-art results on multiple benchmark datasets.",
    "We introduce a new framework for {topic} based on {method}. The proposed approach addresses key challenges in the field and shows promising results in various applications. Extensive evaluation confirms the effectiveness of our method.",
    "In this work, we investigate the application of {method} to {topic}. We develop a scalable solution that handles large-scale data efficiently. Experimental results show substantial improvements in accuracy and computational efficiency.",
]


def generate_paper(paper_id: int) -> dict:
    """
    Generate a single fake paper
    
    Args:
        paper_id: Paper ID number
    
    Returns:
        Paper dict with metadata
    """
    # Random selections
    topic = random.choice(TOPICS)
    method = random.choice(METHODS)
    source = random.choice(SOURCES)
    
    # Generate title
    title_template = random.choice(TITLES_TEMPLATES)
    title = title_template.format(topic=topic.title(), method=method)
    
    # Generate authors (1-4 authors)
    num_authors = random.randint(1, 4)
    authors = []
    for _ in range(num_authors):
        first = random.choice(FIRST_NAMES)
        last = random.choice(LAST_NAMES)
        authors.append(f"{first} {last}")
    
    authors_str = ", ".join(authors)
    
    # Generate abstract
    abstract_template = random.choice(ABSTRACT_TEMPLATES)
    abstract = abstract_template.format(topic=topic, method=method.lower())
    
    # Generate DOI
    doi = f"10.{random.randint(1000, 9999)}/test.{paper_id:06d}"
    
    # Generate URL
    url = f"https://example.com/papers/{paper_id}"
    
    # Generate publication date (last 5 years)
    days_ago = random.randint(0, 365 * 5)
    pub_date = (datetime.now() - timedelta(days=days_ago)).strftime('%Y-%m-%d')
    
    # Document type
    doc_type = random.choice(['article', 'conference', 'preprint'])
    
    # Content hash
    import hashlib
    content_hash = hashlib.sha256(
        f"{title}{authors_str}".encode()
    ).hexdigest()
    
    return {
        'id': paper_id,
        'title': title,
        'authors': authors_str,
        'abstract': abstract,
        'doi': doi,
        'url': url,
        'date': pub_date,
        'type': doc_type,
        'source': source,
        'content_hash': content_hash
    }


def generate_papers(num_papers: int) -> list:
    """
    Generate multiple fake papers
    
    Args:
        num_papers: Number of papers to generate
    
    Returns:
        List of paper dicts
    """
    logger.info(f"🔄 Generating {num_papers} fake papers...")
    
    papers = []
    
    for i in range(num_papers):
        paper = generate_paper(i + 1)
        papers.append(paper)
        
        if (i + 1) % 100 == 0:
            logger.info(f"  Generated {i + 1}/{num_papers} papers...")
    
    logger.info(f"✅ Generated {len(papers)} papers")
    
    return papers


def save_papers(papers: list, output_file: str):
    """
    Save papers to JSON file
    
    Args:
        papers: List of paper dicts
        output_file: Output file path
    """
    logger.info(f"💾 Saving papers to {output_file}...")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(papers, f, indent=2, ensure_ascii=False)
    
    file_size = os.path.getsize(output_file) / (1024 * 1024)
    logger.info(f"✅ Saved {len(papers)} papers ({file_size:.2f} MB)")


def load_papers(input_file: str) -> list:
    """
    Load papers from JSON file
    
    Args:
        input_file: Input file path
    
    Returns:
        List of paper dicts
    """
    logger.info(f"📂 Loading papers from {input_file}...")
    
    with open(input_file, 'r', encoding='utf-8') as f:
        papers = json.load(f)
    
    logger.info(f"✅ Loaded {len(papers)} papers")
    
    return papers


def load_to_faiss(papers: list):
    """
    Load papers into FAISS index
    
    Args:
        papers: List of paper dicts
    """
    from app.services.faiss_service import FAISSService
    from app.services.text_processing.embeddings import EmbeddingService
    import asyncio
    
    logger.info(f"📊 Loading {len(papers)} papers into FAISS...")
    
    # Initialize services
    embedding_service = EmbeddingService()
    faiss_service = FAISSService()
    
    # Generate embeddings
    logger.info("🔢 Generating embeddings...")
    texts = [p['abstract'] for p in papers]
    
    embeddings = embedding_service.encode(
        texts,
        show_progress=True
    )
    
    # Add to FAISS
    logger.info("💾 Adding papers to FAISS...")
    
    async def add_papers():
        return await faiss_service.add_papers(embeddings, papers)
    
    added = asyncio.run(add_papers())
    
    # Save index
    logger.info("💾 Saving FAISS index...")
    faiss_service.save()
    
    # Show stats
    stats = faiss_service.get_stats()
    logger.info(f"\n📊 FAISS Stats:")
    logger.info(f"  Total papers: {stats['total_papers']}")
    logger.info(f"  Dimension: {stats['dimension']}")
    logger.info(f"  Strategy: {stats['strategy']}")
    
    logger.info(f"\n✅ Added {added} papers to FAISS")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Generate test data for xplagiax'
    )
    
    parser.add_argument(
        '--papers',
        type=int,
        default=100,
        help='Number of papers to generate (default: 100)'
    )
    
    parser.add_argument(
        '--output',
        default='test_data/generated_papers.json',
        help='Output file path (default: test_data/generated_papers.json)'
    )
    
    parser.add_argument(
        '--load-to-faiss',
        metavar='FILE',
        help='Load papers from file into FAISS index'
    )
    
    parser.add_argument(
        '--seed',
        type=int,
        help='Random seed for reproducibility'
    )
    
    args = parser.parse_args()
    
    # Set random seed if provided
    if args.seed:
        random.seed(args.seed)
        logger.info(f"🎲 Random seed: {args.seed}")
    
    try:
        if args.load_to_faiss:
            # Load from file and add to FAISS
            papers = load_papers(args.load_to_faiss)
            load_to_faiss(papers)
        else:
            # Generate new papers
            papers = generate_papers(args.papers)
            
            # Create output directory
            os.makedirs(os.path.dirname(args.output), exist_ok=True)
            
            # Save to file
            save_papers(papers, args.output)
            
            logger.info(f"\n✅ Test data generation completed!")
            logger.info(f"📁 Output file: {args.output}")
            logger.info(f"\n💡 To load into FAISS, run:")
            logger.info(f"   python scripts/generate_test_data.py --load-to-faiss {args.output}")
    
    except Exception as e:
        logger.error(f"\n❌ Error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()