"""
Validador y Monitor de APIs Externas
"""
import asyncio
import time
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import json

import httpx


@dataclass
class APIHealthMetrics:
    """Métricas de salud de una API"""
    source: str
    status: str  # "healthy", "degraded", "down"
    avg_latency_ms: float
    success_rate: float
    last_check: str
    errors: List[str]
    response_sample: Optional[Dict] = None


class APIValidator:
    """
    Valida APIs externas en tiempo real
    """
    def __init__(self):
        self.metrics = {}
        self.test_queries = {
            "crossref": {"query": "machine learning", "rows": 1},
            "pubmed": {"term": "covid", "retmax": 1, "retmode": "json"},
            "semantic_scholar": {"query": "neural networks", "limit": 1},
            "arxiv": {"search_query": "all:quantum", "max_results": 1},
            "openalex": {"search": "artificial intelligence", "per-page": 1},
            "europepmc": {"query": "cancer", "pageSize": 1, "format": "json"},
            "doaj": {"pageSize": 1},
            "zenodo": {"q": "dataset", "size": 1}
        }
        
        self.endpoints = {
            "crossref": "https://api.crossref.org/works",
            "pubmed": "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
            "semantic_scholar": "https://api.semanticscholar.org/graph/v1/paper/search",
            "arxiv": "http://export.arxiv.org/api/query",
            "openalex": "https://api.openalex.org/works",
            "europepmc": "https://www.ebi.ac.uk/europepmc/webservices/rest/search",
            "doaj": "https://doaj.org/api/v2/search/articles/test",
            "zenodo": "https://zenodo.org/api/records"
        }
    
    async def validate_api(self, source: str, client: httpx.AsyncClient) -> APIHealthMetrics:
        """Valida una API específica"""
        errors = []
        latencies = []
        successful_requests = 0
        total_requests = 3  # Hacer 3 requests para promediar
        
        url = self.endpoints.get(source)
        params = self.test_queries.get(source, {})
        
        if not url:
            return APIHealthMetrics(
                source=source,
                status="down",
                avg_latency_ms=0,
                success_rate=0,
                last_check=datetime.now().isoformat(),
                errors=["Endpoint no configurado"]
            )
        
        response_sample = None
        
        for _ in range(total_requests):
            try:
                start = time.time()
                response = await client.get(url, params=params, timeout=10.0)
                latency = (time.time() - start) * 1000
                
                if response.status_code == 200:
                    successful_requests += 1
                    latencies.append(latency)
                    
                    # Guardar sample de la primera respuesta exitosa
                    if not response_sample:
                        try:
                            data = response.json()
                            # Tomar solo primeros campos para no sobrecargar
                            response_sample = {
                                k: str(v)[:100] if isinstance(v, str) else v
                                for k, v in list(data.items())[:3]
                            }
                        except:
                            response_sample = {"raw": response.text[:200]}
                    
                    # Validaciones adicionales
                    self._validate_response_structure(source, response, errors)
                else:
                    errors.append(f"HTTP {response.status_code}")
            
            except httpx.TimeoutException:
                errors.append("Timeout >10s")
            except Exception as e:
                errors.append(f"Error: {str(e)[:50]}")
            
            await asyncio.sleep(0.5)  # Evitar rate limits
        
        # Calcular métricas
        avg_latency = sum(latencies) / len(latencies) if latencies else 0
        success_rate = (successful_requests / total_requests) * 100
        
        # Determinar estado
        if success_rate == 100 and avg_latency < 1000:
            status = "healthy"
        elif success_rate >= 50:
            status = "degraded"
        else:
            status = "down"
        
        return APIHealthMetrics(
            source=source,
            status=status,
            avg_latency_ms=round(avg_latency, 2),
            success_rate=round(success_rate, 2),
            last_check=datetime.now().isoformat(),
            errors=list(set(errors)),  # Deduplicar
            response_sample=response_sample
        )
    
    def _validate_response_structure(self, source: str, response: httpx.Response, errors: List[str]):
        """Valida la estructura de la respuesta"""
        try:
            data = response.json()
            
            # Validaciones específicas por fuente
            if source == "crossref":
                if "message" not in data or "items" not in data.get("message", {}):
                    errors.append("Schema inválido: falta 'message.items'")
            
            elif source == "pubmed":
                if "esearchresult" not in data:
                    errors.append("Schema inválido: falta 'esearchresult'")
            
            elif source == "semantic_scholar":
                if "data" not in data:
                    errors.append("Schema inválido: falta 'data'")
            
            elif source == "openalex":
                if "results" not in data:
                    errors.append("Schema inválido: falta 'results'")
            
            # Validación genérica: debe tener al menos un campo
            if not data or len(data) == 0:
                errors.append("Respuesta vacía")
        
        except json.JSONDecodeError:
            errors.append("Respuesta no es JSON válido")
    
    async def validate_all_apis(self) -> Dict[str, APIHealthMetrics]:
        """Valida todas las APIs en paralelo"""
        print("🔍 Validando todas las APIs externas...")
        
        async with httpx.AsyncClient() as client:
            tasks = [
                self.validate_api(source, client)
                for source in self.endpoints.keys()
            ]
            results = await asyncio.gather(*tasks)
        
        # Guardar métricas
        for result in results:
            self.metrics[result.source] = result
        
        return self.metrics
    
    def get_health_report(self) -> Dict:
        """Genera reporte de salud"""
        total = len(self.metrics)
        healthy = sum(1 for m in self.metrics.values() if m.status == "healthy")
        degraded = sum(1 for m in self.metrics.values() if m.status == "degraded")
        down = sum(1 for m in self.metrics.values() if m.status == "down")
        
        avg_latency = sum(m.avg_latency_ms for m in self.metrics.values()) / total if total > 0 else 0
        avg_success = sum(m.success_rate for m in self.metrics.values()) / total if total > 0 else 0
        
        return {
            "summary": {
                "total_apis": total,
                "healthy": healthy,
                "degraded": degraded,
                "down": down,
                "overall_health": "healthy" if down == 0 else "degraded" if degraded > 0 else "critical",
                "avg_latency_ms": round(avg_latency, 2),
                "avg_success_rate": round(avg_success, 2)
            },
            "apis": {
                source: asdict(metrics)
                for source, metrics in self.metrics.items()
            }
        }
    
    def get_failing_apis(self) -> List[str]:
        """Retorna lista de APIs que fallan"""
        return [
            source
            for source, metrics in self.metrics.items()
            if metrics.status in ["degraded", "down"]
        ]
    
    async def continuous_monitoring(self, interval_seconds: int = 300):
        """Monitoreo continuo (cada 5 minutos)"""
        while True:
            await self.validate_all_apis()
            report = self.get_health_report()
            
            print(f"\n📊 Reporte de Salud ({datetime.now().strftime('%H:%M:%S')})")
            print(f"   Healthy: {report['summary']['healthy']}/{report['summary']['total_apis']}")
            print(f"   Latencia promedio: {report['summary']['avg_latency_ms']}ms")
            
            failing = self.get_failing_apis()
            if failing:
                print(f"   ⚠️ APIs con problemas: {', '.join(failing)}")
            
            await asyncio.sleep(interval_seconds)


# Instancia global
_api_validator: Optional[APIValidator] = None


def get_api_validator() -> APIValidator:
    """Retorna instancia global del validador"""
    global _api_validator
    if _api_validator is None:
        _api_validator = APIValidator()
    return _api_validator