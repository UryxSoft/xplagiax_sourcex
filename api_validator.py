"""
Validador y Monitor de APIs Externas - VERSIÓN CORREGIDA
"""
import asyncio
import time
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import json
import logging

import httpx

logger = logging.getLogger(__name__)


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
        """Valida una API específica usando el cliente HTTP compartido"""
        errors = []
        latencies = []
        successful_requests = 0
        total_requests = 3  # Hacer 3 requests para promediar
        
        url = self.endpoints.get(source)
        params = self.test_queries.get(source, {})
        
        if not url:
            logger.warning(f"Endpoint no configurado para {source}")
            return APIHealthMetrics(
                source=source,
                status="down",
                avg_latency_ms=0,
                success_rate=0,
                last_check=datetime.now().isoformat(),
                errors=["Endpoint no configurado"]
            )
        
        response_sample = None
        
        for attempt in range(total_requests):
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
                    logger.warning(f"{source} retornó {response.status_code}")
            
            except httpx.TimeoutException:
                errors.append("Timeout >10s")
                logger.warning(f"{source} timeout en intento {attempt + 1}")
            except httpx.ConnectError as e:
                errors.append(f"Connection error: {str(e)[:30]}")
                logger.warning(f"{source} connection error en intento {attempt + 1}")
            except Exception as e:
                errors.append(f"Error: {str(e)[:50]}")
                logger.error(f"{source} error inesperado", extra={"error": str(e)})
            
            # Evitar rate limits entre intentos
            if attempt < total_requests - 1:
                await asyncio.sleep(0.5)
        
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
        
        logger.info(f"{source} validación completada", extra={
            "status": status,
            "success_rate": success_rate,
            "avg_latency": avg_latency
        })
        
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
            
            elif source == "arxiv":
                # arXiv retorna XML, no JSON
                pass
            
            elif source == "europepmc":
                if "resultList" not in data:
                    errors.append("Schema inválido: falta 'resultList'")
            
            elif source == "doaj":
                if "results" not in data:
                    errors.append("Schema inválido: falta 'results'")
            
            elif source == "zenodo":
                if "hits" not in data:
                    errors.append("Schema inválido: falta 'hits'")
            
            # Validación genérica: debe tener al menos un campo
            if not data or len(data) == 0:
                errors.append("Respuesta vacía")
        
        except json.JSONDecodeError:
            # Algunas APIs retornan XML (arXiv)
            if source not in ["arxiv"]:
                errors.append("Respuesta no es JSON válido")
    
    async def validate_all_apis(self, client: httpx.AsyncClient) -> Dict[str, APIHealthMetrics]:
        """Valida todas las APIs en paralelo usando el cliente compartido"""
        logger.info("Iniciando validación de todas las APIs externas")
        
        tasks = [
            self.validate_api(source, client)
            for source in self.endpoints.keys()
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Guardar métricas y manejar excepciones
        for result in results:
            if isinstance(result, Exception):
                logger.error("Error validando API", extra={"error": str(result)})
                continue
            
            self.metrics[result.source] = result
        
        logger.info(f"Validación completada: {len(self.metrics)} APIs verificadas")
        return self.metrics
    
    def get_health_report(self) -> Dict:
        """Genera reporte de salud"""
        if not self.metrics:
            return {
                "summary": {
                    "total_apis": 0,
                    "healthy": 0,
                    "degraded": 0,
                    "down": 0,
                    "overall_health": "unknown",
                    "avg_latency_ms": 0,
                    "avg_success_rate": 0
                },
                "apis": {}
            }
        
        total = len(self.metrics)
        healthy = sum(1 for m in self.metrics.values() if m.status == "healthy")
        degraded = sum(1 for m in self.metrics.values() if m.status == "degraded")
        down = sum(1 for m in self.metrics.values() if m.status == "down")
        
        avg_latency = sum(m.avg_latency_ms for m in self.metrics.values()) / total if total > 0 else 0
        avg_success = sum(m.success_rate for m in self.metrics.values()) / total if total > 0 else 0
        
        # Determinar salud general
        if down == 0:
            overall_health = "healthy"
        elif down < total / 2:
            overall_health = "degraded"
        else:
            overall_health = "critical"
        
        return {
            "summary": {
                "total_apis": total,
                "healthy": healthy,
                "degraded": degraded,
                "down": down,
                "overall_health": overall_health,
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
    
    async def continuous_monitoring(self, client: httpx.AsyncClient, interval_seconds: int = 300):
        """Monitoreo continuo (cada 5 minutos por defecto)"""
        logger.info(f"Iniciando monitoreo continuo (intervalo: {interval_seconds}s)")
        
        while True:
            try:
                await self.validate_all_apis(client)
                report = self.get_health_report()
                
                logger.info("Reporte de salud", extra={
                    "healthy": report['summary']['healthy'],
                    "total": report['summary']['total_apis'],
                    "avg_latency_ms": report['summary']['avg_latency_ms']
                })
                
                failing = self.get_failing_apis()
                if failing:
                    logger.warning("APIs con problemas detectadas", extra={
                        "failing_apis": failing
                    })
                
                await asyncio.sleep(interval_seconds)
            
            except asyncio.CancelledError:
                logger.info("Monitoreo continuo cancelado")
                break
            except Exception as e:
                logger.error("Error en monitoreo continuo", extra={"error": str(e)})
                await asyncio.sleep(interval_seconds)


# Instancia global
_api_validator: Optional[APIValidator] = None


def get_api_validator() -> APIValidator:
    """Retorna instancia global del validador"""
    global _api_validator
    if _api_validator is None:
        _api_validator = APIValidator()
    return _api_validator