"""
Zenodo Searcher - Research outputs repository
"""
from typing import Dict, List, Tuple
from app.services.external_apis.base_searcher import BaseSearcher


class ZenodoSearcher(BaseSearcher):
    """
    Searcher for Zenodo API
    
    Zenodo: General-purpose open repository for research outputs
    https://zenodo.org
    """
    
    def get_source_name(self) -> str:
        return "zenodo"
    
    def build_request(self, query: str, theme: str) -> Tuple[str, Dict, Dict]:
        """
        Build Zenodo API request
        
        API Docs: https://developers.zenodo.org/
        """
        url = "https://zenodo.org/api/records"
        
        # Build query
        search_query = f"{theme} {query}"
        
        params = {
            "q": search_query,
            "size": self.get_max_results(),
            "sort": "bestmatch",
            "type": "publication"  # Only publications
        }
        
        headers = {}
        
        return url, params, headers
    
    def parse_response(self, data: Dict) -> List[Dict]:
        """
        Parse Zenodo response
        
        Response structure:
        {
            "hits": {
                "hits": [
                    {
                        "metadata": {
                            "title": "...",
                            "creators": [...],
                            "description": "...",
                            "doi": "...",
                            "publication_date": "..."
                        },
                        "links": {
                            "html": "..."
                        }
                    }
                ]
            }
        }
        """
        papers = []
        
        hits = data.get('hits', {}).get('hits', [])
        
        for item in hits:
            metadata = item.get('metadata', {})
            
            # Extract title
            title = metadata.get('title', 'Untitled')
            
            # Extract authors
            creators = metadata.get('creators', [])
            authors = ", ".join([
                creator.get('name', '')
                for creator in creators
            ])
            
            if not authors:
                authors = "Unknown"
            
            # Extract abstract/description
            abstract = metadata.get('description', '')
            
            # Extract DOI
            doi = metadata.get('doi', '')
            
            # Extract URL
            links = item.get('links', {})
            url = links.get('html') or links.get('self')
            
            # Extract publication date
            pub_date = metadata.get('publication_date')
            
            # Document type
            doc_type = metadata.get('resource_type', {}).get('type', 'publication')
            
            paper = {
                'title': title,
                'authors': authors,
                'abstract': abstract,
                'doi': doi,
                'url': url,
                'date': pub_date,
                'type': doc_type,
                'source': 'zenodo'
            }
            
            papers.append(paper)
        
        return papers
    
    def get_timeout(self) -> float:
        return 10.0