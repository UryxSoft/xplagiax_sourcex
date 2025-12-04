"""
Serialización ultra-optimizada con orjson y msgpack
"""
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Detectar librerías disponibles
try:
    import orjson
    ORJSON_AVAILABLE = True
except ImportError:
    ORJSON_AVAILABLE = False
    logger.warning("orjson not available, using standard json (slower)")

try:
    import msgpack
    MSGPACK_AVAILABLE = True
except ImportError:
    MSGPACK_AVAILABLE = False
    logger.warning("msgpack not available")

if not ORJSON_AVAILABLE:
    import json


class FastSerializer:
    """Serializador ultra-rápido con fallbacks"""
    
    @staticmethod
    def dumps_json(obj: Any) -> bytes:
        """Serializar a JSON (5-10x más rápido con orjson)"""
        if ORJSON_AVAILABLE:
            return orjson.dumps(obj)
        else:
            return json.dumps(obj).encode('utf-8')
    
    @staticmethod
    def loads_json(data: bytes) -> Any:
        """Deserializar JSON"""
        if ORJSON_AVAILABLE:
            return orjson.loads(data)
        else:
            return json.loads(data.decode('utf-8'))
    
    @staticmethod
    def dumps_msgpack(obj: Any) -> bytes:
        """Serializar a msgpack (más compacto)"""
        if MSGPACK_AVAILABLE:
            return msgpack.packb(obj, use_bin_type=True)
        else:
            # Fallback a orjson/json
            return FastSerializer.dumps_json(obj)
    
    @staticmethod
    def loads_msgpack(data: bytes) -> Any:
        """Deserializar msgpack"""
        if MSGPACK_AVAILABLE:
            return msgpack.unpackb(data, raw=False)
        else:
            return FastSerializer.loads_json(data)


# Instancia global
serializer = FastSerializer()


# Funciones convenientes
def dumps_json(obj: Any) -> bytes:
    """Shortcut para JSON serialization"""
    return serializer.dumps_json(obj)


def loads_json(data: bytes) -> Any:
    """Shortcut para JSON deserialization"""
    return serializer.loads_json(data)


def dumps_msgpack(obj: Any) -> bytes:
    """Shortcut para msgpack serialization"""
    return serializer.dumps_msgpack(obj)


def loads_msgpack(data: bytes) -> Any:
    """Shortcut para msgpack deserialization"""
    return serializer.loads_msgpack(data)