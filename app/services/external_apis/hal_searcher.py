"""
HAL Searcher - French open science repository
"""
from typing import Dict, List, Tuple
from app.services.external_apis.base_searcher import BaseSearcher


class HALSearcher(BaseSearcher):
    """
    Searcher for HAL (Hyper Articles en Ligne)
    
    HAL: French national open archive for research publications
    https://hal.science
    """
    
    def get_source_name(self) -> str:
        return "hal"
    
    def build_request(self, query: str, theme: str) -> Tuple[str, Dict, Dict]:
        """
        Build HAL API request
        
        API Docs: https://api.archives-ouvertes.fr/docs
        """
        url = "https://api.archives-ouvertes.fr/search/"
        
        # Build query
        search_query = f"{theme} {query}"
        
        params = {
            "q": search_query,
            "rows": self.get_max_results(),
            "wt": "json",  # Response format
            "fl": "title_s,authFullName_s,abstract_s,doiId_s,uri_s,producedDateY_i"
        }
        
        headers = {}
        
        return url, params, headers
    
    def parse_response(self, data: Dict) -> List[Dict]:
        """
        Parse HAL response
        
        Response structure:
        {
            "response": {
                "docs": [
                    {
                        "title_s": ["..."],
                        "authFullName_s": ["...", "..."],
                        "abstract_s": ["..."],
                        "doiId_s": "...",
                        "uri_s": "...",
                        "producedDateY_i": 2023
                    }
                ]
            }
        }
        """
        papers = []
        
        response = data.get('response', {})
        docs = response.get('docs', [])
        
        for item in docs:
            # Extract title (can be array)
            title_list = item.get('title_s', [])
            title = title_list[0] if title_list else 'Untitled'
            
            # Extract authors (array)
            author_list = item.get('authFullName_s', [])
            authors = ", ".join(author_list) if author_list else "Unknown"
            
            # Extract abstract (can be array)
            abstract_list = item.get('abstract_s', [])
            abstract = abstract_list[0] if abstract_list else ''
            
            # Extract DOI
            doi = item.get('doiId_s', '')
            
            # Extract URL
            url = item.get('uri_s', '')
            
            # Extract year
            year = item.get('producedDateY_i')
            pub_date = f"{year}-01-01" if year else None
            
            # Document type
            doc_type = item.get('docType_s', 'article')
            
            paper = {
                'title': title,
                'authors': authors,
                'abstract': abstract,
                'doi': doi,
                'url': url,
                'date': pub_date,
                'type': doc_type,
                'source': 'hal'
            }
            
            papers.append(paper)
        
        return papers
    
    def get_timeout(self) -> float:
        return 12.0