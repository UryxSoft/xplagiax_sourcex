"""
DOAJ Searcher - Directory of Open Access Journals
"""
from typing import Dict, List, Tuple
from app.services.external_apis.base_searcher import BaseSearcher


class DOAJSearcher(BaseSearcher):
    """
    Searcher for DOAJ API
    
    DOAJ: Community-curated online directory of open access journals
    https://doaj.org
    """
    
    def get_source_name(self) -> str:
        return "doaj"
    
    def build_request(self, query: str, theme: str) -> Tuple[str, Dict, Dict]:
        """
        Build DOAJ API request
        
        API Docs: https://doaj.org/api/docs
        """
        url = "https://doaj.org/api/search/articles"
        
        # Build query
        search_query = f"{theme} {query}"
        
        params = {
            "q": search_query,
            "pageSize": self.get_max_results(),
            "sort": "relevance"
        }
        
        headers = {}
        
        return url, params, headers
    
    def parse_response(self, data: Dict) -> List[Dict]:
        """
        Parse DOAJ response
        
        Response structure:
        {
            "results": [
                {
                    "bibjson": {
                        "title": "...",
                        "author": [...],
                        "abstract": "...",
                        "identifier": [...],
                        "year": "2023"
                    }
                }
            ]
        }
        """
        papers = []
        
        results = data.get('results', [])
        
        for item in results:
            bibjson = item.get('bibjson', {})
            
            # Extract title
            title = bibjson.get('title', 'Untitled')
            
            # Extract authors
            author_list = bibjson.get('author', [])
            authors = ", ".join([
                author.get('name', '')
                for author in author_list
            ])
            
            if not authors:
                authors = "Unknown"
            
            # Extract abstract
            abstract = bibjson.get('abstract', '')
            
            # Extract DOI from identifiers
            doi = None
            identifiers = bibjson.get('identifier', [])
            
            for identifier in identifiers:
                if identifier.get('type') == 'doi':
                    doi = identifier.get('id')
                    break
            
            # Extract URL
            links = bibjson.get('link', [])
            url = None
            
            for link in links:
                if link.get('type') == 'fulltext':
                    url = link.get('url')
                    break
            
            # Fallback to DOI URL
            if not url and doi:
                url = f"https://doi.org/{doi}"
            
            # Extract publication year
            year = bibjson.get('year')
            pub_date = f"{year}-01-01" if year else None
            
            paper = {
                'title': title,
                'authors': authors,
                'abstract': abstract,
                'doi': doi,
                'url': url,
                'date': pub_date,
                'type': 'article',
                'source': 'doaj'
            }
            
            papers.append(paper)
        
        return papers
    
    def get_timeout(self) -> float:
        return 10.0