"""
OpenAlex Searcher - Free and open catalog of scholarly papers
"""
from typing import Dict, List, Tuple
from app.services.external_apis.base_searcher import BaseSearcher


class OpenAlexSearcher(BaseSearcher):
    """
    Searcher for OpenAlex API
    
    OpenAlex: Free and open catalog of the world's scholarly papers
    https://openalex.org
    """
    
    def get_source_name(self) -> str:
        return "openalex"
    
    def build_request(self, query: str, theme: str) -> Tuple[str, Dict, Dict]:
        """
        Build OpenAlex API request
        
        API Docs: https://docs.openalex.org/api-entities/works/search-works
        """
        url = "https://api.openalex.org/works"
        
        # Combine theme and query for better results
        search_query = f"{theme} {query}"
        
        params = {
            "search": search_query,
            "per_page": self.get_max_results(),
            "filter": "type:article",  # Filter for articles only
            "sort": "relevance_score:desc"
        }
        
        headers = {
            "User-Agent": "xplagiax-bot (mailto:admin@xplagiax.com)"
        }
        
        return url, params, headers
    
    def parse_response(self, data: Dict) -> List[Dict]:
        """
        Parse OpenAlex response
        
        Response structure:
        {
            "results": [
                {
                    "id": "https://openalex.org/W...",
                    "title": "...",
                    "authorships": [...],
                    "publication_date": "2023-01-15",
                    "abstract_inverted_index": {...},
                    "doi": "...",
                    "primary_location": {...}
                }
            ]
        }
        """
        papers = []
        
        results = data.get('results', [])
        
        for item in results:
            # Extract title
            title = item.get('title', 'Untitled')
            
            # Extract authors
            authorships = item.get('authorships', [])
            authors = ", ".join([
                auth.get('author', {}).get('display_name', '')
                for auth in authorships
            ])
            
            if not authors:
                authors = "Unknown"
            
            # Extract abstract (OpenAlex uses inverted index)
            abstract = self._reconstruct_abstract(
                item.get('abstract_inverted_index', {})
            )
            
            # Extract DOI
            doi = item.get('doi', '').replace('https://doi.org/', '')
            
            # Extract URL
            url = item.get('id') or item.get('primary_location', {}).get('landing_page_url')
            
            # Extract publication date
            pub_date = item.get('publication_date')
            
            # Document type
            doc_type = item.get('type', 'article')
            
            paper = {
                'title': title,
                'authors': authors,
                'abstract': abstract,
                'doi': doi,
                'url': url,
                'date': pub_date,
                'type': doc_type,
                'source': 'openalex'
            }
            
            papers.append(paper)
        
        return papers
    
    def _reconstruct_abstract(self, inverted_index: Dict) -> str:
        """
        Reconstruct abstract from OpenAlex inverted index
        
        OpenAlex stores abstracts as inverted index:
        {"hello": [0], "world": [1]} -> "hello world"
        
        Args:
            inverted_index: Dict mapping words to positions
        
        Returns:
            Reconstructed abstract text
        """
        if not inverted_index:
            return ""
        
        try:
            # Create list of (position, word) tuples
            word_positions = []
            
            for word, positions in inverted_index.items():
                for pos in positions:
                    word_positions.append((pos, word))
            
            # Sort by position
            word_positions.sort(key=lambda x: x[0])
            
            # Join words
            abstract = " ".join([word for _, word in word_positions])
            
            return abstract
        
        except Exception as e:
            self.logger.error(f"Error reconstructing abstract: {e}")
            return ""
    
    def get_timeout(self) -> float:
        return 10.0