"""
arXiv Searcher
"""
from typing import Dict, List, Tuple
from app.services.external_apis.base_searcher import BaseSearcher
import xml.etree.ElementTree as ET


class ArXivSearcher(BaseSearcher):
    """Searcher for arXiv API"""
    
    def get_source_name(self) -> str:
        return "arxiv"
    
    def build_request(self, query: str, theme: str) -> Tuple[str, Dict, Dict]:
        url = "http://export.arxiv.org/api/query"
        
        params = {
            "search_query": f"all:{theme} {query}",
            "start": 0,
            "max_results": self.get_max_results()
        }
        
        headers = {}
        
        return url, params, headers
    
    async def search(self, query: str, theme: str, http_client):
        """Override search to handle XML response"""
        source_name = self.get_source_name()
        
        try:
            if not await self.rate_limiter.check_limit(source_name):
                return self._error_response("Rate limit exceeded")
            
            url, params, headers = self.build_request(query, theme)
            
            response = await http_client.get(
                url, params=params, headers=headers, timeout=self.get_timeout()
            )
            
            response.raise_for_status()
            
            # Parse XML
            papers = self._parse_xml(response.text)
            
            from app.services.external_apis.base_searcher import SearchResponse
            return SearchResponse(
                papers=papers,
                source=source_name,
                success=True
            )
        
        except Exception as e:
            self.logger.error(f"arXiv error: {e}")
            from app.services.external_apis.base_searcher import SearchResponse
            return SearchResponse(
                papers=[],
                source=source_name,
                success=False,
                error=str(e)
            )
    
    def _parse_xml(self, xml_text: str) -> List[Dict]:
        """Parse arXiv XML response"""
        papers = []
        
        try:
            root = ET.fromstring(xml_text)
            
            ns = {'atom': 'http://www.w3.org/2005/Atom'}
            
            for entry in root.findall('atom:entry', ns):
                title = entry.find('atom:title', ns)
                summary = entry.find('atom:summary', ns)
                
                authors_elem = entry.findall('atom:author', ns)
                authors = ", ".join([
                    a.find('atom:name', ns).text
                    for a in authors_elem
                    if a.find('atom:name', ns) is not None
                ])
                
                link = entry.find('atom:id', ns)
                
                paper = {
                    'title': title.text.strip() if title is not None else 'Untitled',
                    'authors': authors or "Unknown",
                    'abstract': summary.text.strip() if summary is not None else '',
                    'doi': '',
                    'url': link.text if link is not None else None,
                    'date': None,
                    'type': 'preprint',
                    'source': 'arxiv'
                }
                
                papers.append(paper)
        
        except Exception as e:
            self.logger.error(f"Error parsing arXiv XML: {e}")
        
        return papers
    
    def parse_response(self, data: Dict) -> List[Dict]:
        """Not used for arXiv (XML parser instead)"""
        return []