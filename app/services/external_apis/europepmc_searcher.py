"""
Europe PMC Searcher - Life sciences literature database
"""
from typing import Dict, List, Tuple
from app.services.external_apis.base_searcher import BaseSearcher


class EuropePMCSearcher(BaseSearcher):
    """
    Searcher for Europe PMC API
    
    Europe PMC: Free full-text archive of life sciences research
    https://europepmc.org
    """
    
    def get_source_name(self) -> str:
        return "europepmc"
    
    def build_request(self, query: str, theme: str) -> Tuple[str, Dict, Dict]:
        """
        Build Europe PMC API request
        
        API Docs: https://europepmc.org/RestfulWebService
        """
        url = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
        
        # Build query
        search_query = f"{theme} {query}"
        
        params = {
            "query": search_query,
            "format": "json",
            "pageSize": self.get_max_results(),
            "resultType": "core",  # Return full records
            "sort": "RELEVANCE"
        }
        
        headers = {}
        
        return url, params, headers
    
    def parse_response(self, data: Dict) -> List[Dict]:
        """
        Parse Europe PMC response
        
        Response structure:
        {
            "resultList": {
                "result": [
                    {
                        "title": "...",
                        "authorString": "...",
                        "abstractText": "...",
                        "doi": "...",
                        "pmid": "...",
                        "firstPublicationDate": "..."
                    }
                ]
            }
        }
        """
        papers = []
        
        result_list = data.get('resultList', {})
        results = result_list.get('result', [])
        
        for item in results:
            # Extract title
            title = item.get('title', 'Untitled')
            
            # Extract authors (already formatted string)
            authors = item.get('authorString', 'Unknown')
            
            # Extract abstract
            abstract = item.get('abstractText', '')
            
            # Extract DOI
            doi = item.get('doi', '')
            
            # Build URL (prefer DOI, fallback to PMID)
            pmid = item.get('pmid')
            if doi:
                url = f"https://doi.org/{doi}"
            elif pmid:
                url = f"https://europepmc.org/article/MED/{pmid}"
            else:
                url = None
            
            # Extract publication date
            pub_date = item.get('firstPublicationDate')
            
            # Document type
            doc_type = item.get('pubType', 'article')
            
            paper = {
                'title': title,
                'authors': authors,
                'abstract': abstract,
                'doi': doi,
                'url': url,
                'date': pub_date,
                'type': doc_type,
                'source': 'europepmc'
            }
            
            papers.append(paper)
        
        return papers
    
    def get_timeout(self) -> float:
        return 12.0