"""
Funciones de búsqueda en diferentes fuentes académicas
"""
from typing import List, Dict
from xml.etree import ElementTree as ET

import httpx

from config import Config


async def search_crossref(query: str, theme: str, client: httpx.AsyncClient, rate_limiter) -> List[Dict]:
    """Busca en Crossref con rate limiting"""
    if not await rate_limiter.can_make_request("crossref"):
        return []
    
    try:
        url = "https://api.crossref.org/works"
        params = {
            "query": f"{theme} {query}",
            "rows": Config.MAX_RESULTS_PER_SOURCE,
            "select": "title,author,abstract,type"
        }
        response = await client.get(url, params=params)
        
        if response.status_code == 200:
            data = response.json()
            results = []
            for item in data.get("message", {}).get("items", []):
                title = item.get("title", [""])[0] if isinstance(item.get("title"), list) else item.get("title", "")
                abstract = item.get("abstract", "")
                authors = item.get("author", [])
                author = authors[0].get("family", "Unknown") if authors else "Unknown"
                doc_type = item.get("type", "article")
                
                if abstract:
                    results.append({
                        "title": title,
                        "abstract": abstract,
                        "author": author,
                        "type": doc_type
                    })
            return results
    except Exception as e:
        print(f"Error Crossref: {e}")
    return []


async def search_pubmed(query: str, theme: str, client: httpx.AsyncClient, rate_limiter) -> List[Dict]:
    """Busca en PubMed con parser XML robusto"""
    if not await rate_limiter.can_make_request("pubmed"):
        return []
    
    try:
        # Búsqueda de IDs
        search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
        search_params = {
            "db": "pubmed",
            "term": f"{theme} {query}",
            "retmax": Config.MAX_RESULTS_PER_SOURCE,
            "retmode": "json"
        }
        response = await client.get(search_url, params=search_params)
        
        if response.status_code != 200:
            return []
        
        ids = response.json().get("esearchresult", {}).get("idlist", [])
        if not ids:
            return []
        
        # Obtener resúmenes (XML)
        fetch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
        fetch_params = {
            "db": "pubmed",
            "id": ",".join(ids[:3]),
            "retmode": "xml"
        }
        response = await client.get(fetch_url, params=fetch_params)
        
        # Parser XML optimizado
        results = []
        try:
            root = ET.fromstring(response.content)
            for article in root.findall(".//PubmedArticle"):
                title_elem = article.find(".//ArticleTitle")
                abstract_elem = article.find(".//AbstractText")
                author_elem = article.find(".//Author/LastName")
                
                if abstract_elem is not None and abstract_elem.text:
                    results.append({
                        "title": title_elem.text if title_elem is not None else "Unknown",
                        "abstract": abstract_elem.text,
                        "author": author_elem.text if author_elem is not None else "Unknown",
                        "type": "article"
                    })
        except ET.ParseError:
            pass
        
        return results
    except Exception as e:
        print(f"Error PubMed: {e}")
    return []


async def search_semantic_scholar(query: str, theme: str, client: httpx.AsyncClient, rate_limiter) -> List[Dict]:
    """Busca en Semantic Scholar"""
    if not await rate_limiter.can_make_request("semantic_scholar"):
        return []
    
    try:
        url = "https://api.semanticscholar.org/graph/v1/paper/search"
        params = {
            "query": f"{theme} {query}",
            "limit": Config.MAX_RESULTS_PER_SOURCE,
            "fields": "title,abstract,authors,publicationTypes,year,externalIds,url"
        }
        
        response = await client.get(url, params=params)
        
        if response.status_code == 200:
            data = response.json()
            results = []
            for paper in data.get("data", []):
                title = paper.get("title", "")
                abstract = paper.get("abstract", "")
                authors = paper.get("authors", [])
                author = authors[0].get("name", "Unknown") if authors else "Unknown"
                pub_types = paper.get("publicationTypes", [])
                doc_type = pub_types[0] if pub_types else "article"
                year = paper.get("year", "Unknown")  #  NUEVO
                doi = paper.get("externalIds", {}).get("DOI")  #  NUEVO
                url = paper.get("url")  #  NUEVO
                
                if abstract:
                    results.append({
                        "title": title,
                        "abstract": abstract,
                        "author": author,
                        "type": doc_type,
                        "publication_date": str(year),  #  NUEVO
                        "doi": doi,  #  NUEVO
                        "url": url  #  NUEVO
                    })
            return results
    except Exception as e:
        print(f"Error Semantic Scholar: {e}")
    return []


async def search_arxiv(query: str, theme: str, client: httpx.AsyncClient, rate_limiter) -> List[Dict]:
    """Busca en arXiv con parser XML"""
    if not await rate_limiter.can_make_request("arxiv"):
        return []
    
    try:
        url = "http://export.arxiv.org/api/query"
        params = {
            "search_query": f"all:{theme} {query}",
            "start": 0,
            "max_results": Config.MAX_RESULTS_PER_SOURCE
        }
        response = await client.get(url, params=params)
        
        if response.status_code == 200:
            results = []
            try:
                ns = {'atom': 'http://www.w3.org/2005/Atom'}
                root = ET.fromstring(response.content)
                
                for entry in root.findall('atom:entry', ns):
                    title_elem = entry.find('atom:title', ns)
                    summary_elem = entry.find('atom:summary', ns)
                    author_elem = entry.find('atom:author/atom:name', ns)
                    
                    if summary_elem is not None and summary_elem.text:
                        results.append({
                            "title": title_elem.text.strip() if title_elem is not None else "Unknown",
                            "abstract": summary_elem.text.strip(),
                            "author": author_elem.text if author_elem is not None else "Unknown",
                            "type": "preprint"
                        })
            except ET.ParseError:
                pass
            
            return results
    except Exception as e:
        print(f"Error arXiv: {e}")
    return []


async def search_openalex(query: str, theme: str, client: httpx.AsyncClient, rate_limiter) -> List[Dict]:
    """Busca en OpenAlex"""
    if not await rate_limiter.can_make_request("openalex"):
        return []
    
    try:
        url = "https://api.openalex.org/works"
        params = {
            "search": f"{theme} {query}",
            "per-page": Config.MAX_RESULTS_PER_SOURCE
        }
        response = await client.get(url, params=params)
        
        if response.status_code == 200:
            data = response.json()
            results = []
            for work in data.get("results", []):
                title = work.get("title", "")
                abstract_idx = work.get("abstract_inverted_index", {})
                
                # Reconstruir abstract
                if abstract_idx:
                    word_positions = [(word, min(positions)) for word, positions in abstract_idx.items()]
                    word_positions.sort(key=lambda x: x[1])
                    abstract_text = ' '.join([w for w, _ in word_positions[:100]])
                else:
                    abstract_text = ""
                
                authorships = work.get("authorships", [])
                author = "Unknown"
                if authorships:
                    author = authorships[0].get("author", {}).get("display_name", "Unknown")
                
                doc_type = work.get("type", "article")
                year = work.get("publication_year", "Unknown")
                doi = work.get("doi")
                url = work.get("id")  # OpenAlex ID como URL
                
                if abstract_text:
                    results.append({
                        "title": title,
                        "abstract": abstract_text,
                        "author": author,
                        "type": doc_type,
                        "publication_date": str(year),  # 
                        "doi": doi,  # 
                        "url": url   # 
                    })
            return results
    except Exception as e:
        print(f"Error OpenAlex: {e}")
    return []


async def search_europepmc(query: str, theme: str, client: httpx.AsyncClient, rate_limiter) -> List[Dict]:
    """Busca en Europe PMC"""
    if not await rate_limiter.can_make_request("europepmc"):
        return []
    
    try:
        url = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
        params = {
            "query": f"{theme} {query}",
            "format": "json",
            "pageSize": Config.MAX_RESULTS_PER_SOURCE
        }
        response = await client.get(url, params=params)
        
        if response.status_code == 200:
            data = response.json()
            results = []
            for result in data.get("resultList", {}).get("result", []):
                title = result.get("title", "")
                abstract = result.get("abstractText", "")
                author = result.get("authorString", "Unknown")
                doc_type = result.get("pubType", "article")
                
                if abstract:
                    results.append({
                        "title": title,
                        "abstract": abstract,
                        "author": author,
                        "type": doc_type
                    })
            return results
    except Exception as e:
        print(f"Error Europe PMC: {e}")
    return []


async def search_doaj(query: str, theme: str, client: httpx.AsyncClient, rate_limiter) -> List[Dict]:
    """Busca en DOAJ"""
    if not await rate_limiter.can_make_request("doaj"):
        return []
    
    try:
        url = f"https://doaj.org/api/v2/search/articles/{theme}%20{query}"
        params = {"pageSize": Config.MAX_RESULTS_PER_SOURCE}
        response = await client.get(url, params=params)
        
        if response.status_code == 200:
            data = response.json()
            results = []
            for result in data.get("results", []):
                bibjson = result.get("bibjson", {})
                title = bibjson.get("title", "")
                abstract = bibjson.get("abstract", "")
                authors = bibjson.get("author", [])
                author = authors[0].get("name", "Unknown") if authors else "Unknown"
                
                if abstract:
                    results.append({
                        "title": title,
                        "abstract": abstract,
                        "author": author,
                        "type": "article"
                    })
            return results
    except Exception as e:
        print(f"Error DOAJ: {e}")
    return []


async def search_zenodo(query: str, theme: str, client: httpx.AsyncClient, rate_limiter) -> List[Dict]:
    """Busca en Zenodo"""
    if not await rate_limiter.can_make_request("zenodo"):
        return []
    
    try:
        url = "https://zenodo.org/api/records"
        params = {
            "q": f"{theme} {query}",
            "size": Config.MAX_RESULTS_PER_SOURCE
        }
        response = await client.get(url, params=params)
        
        if response.status_code == 200:
            data = response.json()
            results = []
            for hit in data.get("hits", {}).get("hits", []):
                metadata = hit.get("metadata", {})
                title = metadata.get("title", "")
                description = metadata.get("description", "")
                creators = metadata.get("creators", [])
                author = creators[0].get("name", "Unknown") if creators else "Unknown"
                resource_type = metadata.get("resource_type", {}).get("type", "publication")
                
                if description:
                    results.append({
                        "title": title,
                        "abstract": description[:500],
                        "author": author,
                        "type": resource_type
                    })
            return results
    except Exception as e:
        print(f"Error Zenodo: {e}")
    return []