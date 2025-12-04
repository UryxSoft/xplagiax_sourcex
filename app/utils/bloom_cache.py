"""
Bloom filter para cache - reduce lookups innecesarios
pip install mmh3 bitarray
"""
import mmh3  # MurmurHash3
from bitarray import bitarray
import math


class BloomFilter:
    """
    Bloom filter probabilístico
    
    False positive rate: ~1%
    False negative rate: 0% (nunca)
    """
    
    def __init__(self, expected_items: int = 100000, fp_rate: float = 0.01):
        # Calcular tamaño óptimo
        self.size = self._optimal_size(expected_items, fp_rate)
        self.hash_count = self._optimal_hash_count(self.size, expected_items)
        
        # Bit array
        self.bits = bitarray(self.size)
        self.bits.setall(0)
        
        self.item_count = 0
    
    def _optimal_size(self, n, p):
        """Tamaño óptimo del bit array"""
        return int(-n * math.log(p) / (math.log(2) ** 2))
    
    def _optimal_hash_count(self, m, n):
        """Número óptimo de hash functions"""
        return int((m / n) * math.log(2))
    
    def add(self, item: str):
        """Agregar item"""
        for seed in range(self.hash_count):
            index = mmh3.hash(item, seed) % self.size
            self.bits[index] = 1
        self.item_count += 1
    
    def contains(self, item: str) -> bool:
        """
        Check si item PUEDE estar en cache
        
        Returns:
            True: item PUEDE estar (check cache)
            False: item NO está (skip cache)
        """
        for seed in range(self.hash_count):
            index = mmh3.hash(item, seed) % self.size
            if not self.bits[index]:
                return False
        return True
    
    def clear(self):
        """Clear filter"""
        self.bits.setall(0)
        self.item_count = 0


# Integrar en CacheManager:
class CacheManager:
    def __init__(self, ttl: int = 3600):
        self.ttl = ttl
        self.bloom = BloomFilter()  # ✅ NUEVO
    
    async def get_from_cache(self, key: str):
        # ✅ Check bloom primero
        if not self.bloom.contains(key):
            return None  # Seguro no existe, skip Redis
        
        # Puede existir, check Redis
        redis_client = get_redis_client()
        # ... resto igual ...
    
    async def save_to_cache(self, key: str, value: Any):
        # ... guardar en Redis ...
        
        # ✅ Agregar a bloom
        self.bloom.add(key)