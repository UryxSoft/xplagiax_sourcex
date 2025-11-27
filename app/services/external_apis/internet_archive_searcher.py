"""
Internet Archive Scholar Searcher - Full-text scholarly articles
"""
from typing import Dict, List, Tuple
from app.services.external_apis.base_searcher import BaseSearcher


class InternetArchiveScholarSearcher(BaseSearcher):
    """
    Searcher for Internet Archive Scholar
    
    Internet Archive Scholar: Full-text search over 25+ million research articles
    https://scholar.archive.org
    """
    
    def get_source_name(self) -> str:
        return "internet_archive"
    
    def build_request(self, query: str, theme: str) -> Tuple[str, Dict, Dict]:
        """
        Build Internet Archive Scholar API request
        
        API Docs: https://scholar.archive.org/api
        """
        url = "https://scholar.archive.org/search"
        
        # Build query
        search_query = f"{theme} {query}"
        
        params = {
            "q": search_query,
            "limit": self.get_max_results()
        }
        
        headers = {}
        
        return url, params, headers
    
    def parse_response(self, data: Dict) -> List[Dict]:
        """
        Parse Internet Archive Scholar response
        
        Response structure:
        {
            "results": [
                {
                    "biblio": {
                        "title": "...",
                        "contrib_names": ["..."],
                        "doi": "...",
                        "year": 2023
                    },
                    "fulltext": {
                        "abstract": "..."
                    },
                    "access": [
                        {
                            "access_url": "..."
                        }
                    ]
                }
            ]
        }
        """
        papers = []
        
        results = data.get('results', [])
        
        for item in results:
            biblio = item.get('biblio', {})
            fulltext = item.get('fulltext', {})
            
            # Extract title
            title = biblio.get('title', 'Untitled')
            
            # Extract authors
            contrib_names = biblio.get('contrib_names', [])
            authors = ", ".join(contrib_names) if contrib_names else "Unknown"
            
            # Extract abstract
            abstract = fulltext.get('abstract', '')
            
            # Extract DOI
            doi = biblio.get('doi', '')
            
            # Extract URL
            access_list = item.get('access', [])
            url = None
            
            if access_list:
                url = access_list[0].get('access_url')
            
            # Fallback to DOI URL
            if not url and doi:
                url = f"https://doi.org/{doi}"
            
            # Extract year
            year = biblio.get('year')
            pub_date = f"{year}-01-01" if year else None
            
            # Document type
            doc_type = biblio.get('type', 'article')
            
            paper = {
                'title': title,
                'authors': authors,
                'abstract': abstract,
                'doi': doi,
                'url': url,
                'date': pub_date,
                'type': doc_type,
                'source': 'internet_archive'
            }
            
            papers.append(paper)
        
        return papers
    
    def get_timeout(self) -> float:
        return 12.0