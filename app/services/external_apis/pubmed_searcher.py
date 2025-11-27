"""
PubMed Searcher - Implementation for PubMed API
"""
from typing import Dict, List, Tuple
from app.services.external_apis.base_searcher import BaseSearcher


class PubMedSearcher(BaseSearcher):
    """Searcher for PubMed API"""
    
    def get_source_name(self) -> str:
        return "pubmed"
    
    def build_request(self, query: str, theme: str) -> Tuple[str, Dict, Dict]:
        url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
        
        params = {
            "db": "pubmed",
            "term": f"{theme} {query}",
            "retmax": self.get_max_results(),
            "retmode": "json"
        }
        
        headers = {}
        
        return url, params, headers
    
    def parse_response(self, data: Dict) -> List[Dict]:
        papers = []
        
        id_list = data.get('esearchresult', {}).get('idlist', [])
        
        # Note: This is simplified. Full implementation would:
        # 1. Call efetch.fcgi with these IDs to get full details
        # 2. Parse XML response for abstracts, authors, etc.
        
        for pmid in id_list:
            paper = {
                'title': f"PubMed Article {pmid}",
                'authors': "Unknown",
                'abstract': '',
                'doi': '',
                'url': f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                'date': None,
                'type': 'article',
                'source': 'pubmed'
            }
            
            papers.append(paper)
        
        return papers
    
    def get_timeout(self) -> float:
        return 15.0  # PubMed can be slower