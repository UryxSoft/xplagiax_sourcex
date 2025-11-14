# ingestion_pipeline.py
from celery import Celery
from celery.schedules import crontab

app = Celery('ingestion', broker='redis://localhost:6379/0')

@app.task
def daily_ingestion_job():
    """
    Job diario: Crawl APIs, deduplicación, indexación
    """
    logger.info("Iniciando pipeline de ingesta diaria")
    
    # 1. Crawl APIs académicas
    papers = crawl_all_sources(
        queries=["machine learning", "artificial intelligence", "deep learning"],
        max_papers_per_query=1000
    )
    
    # 2. Deduplicación
    deduplicator = PaperDeduplicator()
    await deduplicator.init_db()
    
    new_papers = []
    for paper in papers:
        if not await deduplicator.exists(paper['title'], paper.get('doi')):
            new_papers.append(paper)
    
    logger.info(f"Papers nuevos: {len(new_papers)} de {len(papers)}")
    
    # 3. Generar embeddings (batch en GPU)
    abstracts = [p['abstract'] for p in new_papers]
    embeddings = generate_embeddings_batch(abstracts, batch_size=256)
    
    # 4. Agregar a índice FAISS temporal
    temp_index = build_faiss_index(embeddings, strategy="ivf_pq")
    
    # 5. Merge con índice global
    global_index = load_global_index()
    merged_index = merge_faiss_indices(global_index, temp_index)
    
    # 6. Guardar papers en PostgreSQL
    for idx, paper in enumerate(new_papers):
        faiss_id = global_index.ntotal + idx
        await deduplicator.add_paper(paper, faiss_id)
    
    # 7. Deploy nuevo índice (blue-green deployment)
    deploy_index(merged_index, version=datetime.now().strftime("%Y%m%d_%H%M"))
    
    logger.info("Pipeline completado exitosamente")

@app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    # Ejecutar diariamente a las 2 AM
    sender.add_periodic_task(
        crontab(hour=2, minute=0),
        daily_ingestion_job.s(),
    )