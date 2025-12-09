"""
缓存管理器 - 提供查询结果和 Embedding 缓存功能
支持 LRU 缓存策略和持久化存储
"""

import os
import json
import hashlib
import pickle
from pathlib import Path
from typing import Any, Optional, Dict, List
from functools import lru_cache
from collections import OrderedDict
from datetime import datetime, timedelta
import threading


class LRUCache:
    """
    线程安全的 LRU 缓存实现
    支持过期时间和容量限制
    """
    
    def __init__(self, max_size: int = 100, ttl_seconds: Optional[int] = 3600):
        """
        初始化 LRU 缓存
        
        Args:
            max_size: 最大缓存条目数
            ttl_seconds: 缓存过期时间（秒），None 表示永不过期
        """
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.cache = OrderedDict()
        self.timestamps = {}  # 存储每个键的创建时间
        self.lock = threading.RLock()
        
        # 统计信息
        self.hits = 0
        self.misses = 0
    
    def _is_expired(self, key: str) -> bool:
        """检查缓存项是否过期"""
        if self.ttl_seconds is None:
            return False
        
        if key not in self.timestamps:
            return True
        
        age = (datetime.now() - self.timestamps[key]).total_seconds()
        return age > self.ttl_seconds
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        with self.lock:
            if key not in self.cache:
                self.misses += 1
                return None
            
            # 检查是否过期
            if self._is_expired(key):
                del self.cache[key]
                del self.timestamps[key]
                self.misses += 1
                return None
            
            # 移到末尾（表示最近使用）
            self.cache.move_to_end(key)
            self.hits += 1
            return self.cache[key]
    
    def put(self, key: str, value: Any):
        """存储缓存值"""
        with self.lock:
            # 如果键已存在，更新并移到末尾
            if key in self.cache:
                self.cache.move_to_end(key)
            
            self.cache[key] = value
            self.timestamps[key] = datetime.now()
            
            # 如果超过最大容量，移除最旧的项
            if len(self.cache) > self.max_size:
                oldest_key = next(iter(self.cache))
                del self.cache[oldest_key]
                del self.timestamps[oldest_key]
    
    def clear(self):
        """清空缓存"""
        with self.lock:
            self.cache.clear()
            self.timestamps.clear()
            self.hits = 0
            self.misses = 0
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        with self.lock:
            total_requests = self.hits + self.misses
            hit_rate = (self.hits / total_requests * 100) if total_requests > 0 else 0
            
            return {
                'size': len(self.cache),
                'max_size': self.max_size,
                'hits': self.hits,
                'misses': self.misses,
                'hit_rate': f"{hit_rate:.1f}%",
                'ttl_seconds': self.ttl_seconds
            }


class EmbeddingCache:
    """
    Embedding 缓存
    支持持久化到磁盘，避免重复调用 API
    """
    
    def __init__(self, cache_dir: str = "./cache/embeddings", max_memory_size: int = 1000):
        """
        初始化 Embedding 缓存
        
        Args:
            cache_dir: 缓存文件目录
            max_memory_size: 内存中最大缓存数量
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # 内存缓存（LRU）
        self.memory_cache = LRUCache(max_size=max_memory_size, ttl_seconds=None)
        
        # 磁盘缓存索引
        self.index_file = self.cache_dir / "index.json"
        self.disk_index = self._load_index()
        
        self.lock = threading.RLock()
    
    def _load_index(self) -> Dict[str, str]:
        """加载磁盘缓存索引"""
        if self.index_file.exists():
            try:
                with open(self.index_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}
    
    def _save_index(self):
        """保存磁盘缓存索引"""
        try:
            with open(self.index_file, 'w', encoding='utf-8') as f:
                json.dump(self.disk_index, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"⚠️  保存缓存索引失败: {e}")
    
    @staticmethod
    def _hash_text(text: str) -> str:
        """计算文本的 hash 值作为缓存键"""
        return hashlib.sha256(text.encode('utf-8')).hexdigest()
    
    def get(self, text: str) -> Optional[List[float]]:
        """
        获取文本的 Embedding
        
        Args:
            text: 输入文本
            
        Returns:
            Embedding 向量，如果不存在则返回 None
        """
        text_hash = self._hash_text(text)
        
        # 1. 先查内存缓存
        embedding = self.memory_cache.get(text_hash)
        if embedding is not None:
            return embedding
        
        # 2. 查磁盘缓存
        with self.lock:
            if text_hash in self.disk_index:
                cache_file = self.cache_dir / self.disk_index[text_hash]
                if cache_file.exists():
                    try:
                        with open(cache_file, 'rb') as f:
                            embedding = pickle.load(f)
                        
                        # 加载到内存缓存
                        self.memory_cache.put(text_hash, embedding)
                        return embedding
                    except Exception as e:
                        print(f"⚠️  加载缓存失败: {e}")
        
        return None
    
    def put(self, text: str, embedding: List[float]):
        """
        存储文本的 Embedding
        
        Args:
            text: 输入文本
            embedding: Embedding 向量
        """
        text_hash = self._hash_text(text)
        
        # 1. 存入内存缓存
        self.memory_cache.put(text_hash, embedding)
        
        # 2. 存入磁盘缓存
        with self.lock:
            cache_file = self.cache_dir / f"{text_hash}.pkl"
            try:
                with open(cache_file, 'wb') as f:
                    pickle.dump(embedding, f)
                
                self.disk_index[text_hash] = f"{text_hash}.pkl"
                self._save_index()
            except Exception as e:
                print(f"⚠️  保存缓存失败: {e}")
    
    def get_batch(self, texts: List[str]) -> Dict[str, Optional[List[float]]]:
        """
        批量获取 Embeddings
        
        Args:
            texts: 文本列表
            
        Returns:
            {text: embedding} 字典，未命中的返回 None
        """
        results = {}
        for text in texts:
            results[text] = self.get(text)
        return results
    
    def put_batch(self, text_embedding_pairs: List[tuple]):
        """
        批量存储 Embeddings
        
        Args:
            text_embedding_pairs: [(text, embedding), ...] 列表
        """
        for text, embedding in text_embedding_pairs:
            self.put(text, embedding)
    
    def clear(self):
        """清空所有缓存"""
        self.memory_cache.clear()
        
        with self.lock:
            # 删除磁盘文件
            for cache_file in self.cache_dir.glob("*.pkl"):
                try:
                    cache_file.unlink()
                except Exception:
                    pass
            
            self.disk_index.clear()
            self._save_index()
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        memory_stats = self.memory_cache.get_stats()
        
        return {
            'memory_cache': memory_stats,
            'disk_cache_size': len(self.disk_index),
            'cache_dir': str(self.cache_dir)
        }


class QueryCache:
    """
    查询结果缓存
    缓存完整的 RAG 问答结果
    """
    
    def __init__(self, max_size: int = 50, ttl_seconds: int = 1800):
        """
        初始化查询缓存
        
        Args:
            max_size: 最大缓存数量
            ttl_seconds: 缓存过期时间（默认 30 分钟）
        """
        self.cache = LRUCache(max_size=max_size, ttl_seconds=ttl_seconds)
    
    @staticmethod
    def _make_cache_key(query: str, top_k: int, temperature: float, threshold: float) -> str:
        """生成缓存键"""
        key_str = f"{query}|{top_k}|{temperature:.2f}|{threshold:.2f}"
        return hashlib.md5(key_str.encode('utf-8')).hexdigest()
    
    def get(self, query: str, top_k: int, temperature: float, threshold: float) -> Optional[Dict[str, Any]]:
        """获取查询结果"""
        cache_key = self._make_cache_key(query, top_k, temperature, threshold)
        return self.cache.get(cache_key)
    
    def put(self, query: str, top_k: int, temperature: float, threshold: float, result: Dict[str, Any]):
        """存储查询结果"""
        cache_key = self._make_cache_key(query, top_k, temperature, threshold)
        self.cache.put(cache_key, result)
    
    def clear(self):
        """清空缓存"""
        self.cache.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        return self.cache.get_stats()


# 全局缓存管理器实例
_embedding_cache: Optional[EmbeddingCache] = None
_query_cache: Optional[QueryCache] = None


def get_embedding_cache() -> EmbeddingCache:
    """获取全局 Embedding 缓存实例（单例模式）"""
    global _embedding_cache
    if _embedding_cache is None:
        _embedding_cache = EmbeddingCache()
    return _embedding_cache


def get_query_cache() -> QueryCache:
    """获取全局查询缓存实例（单例模式）"""
    global _query_cache
    if _query_cache is None:
        _query_cache = QueryCache()
    return _query_cache


if __name__ == "__main__":
    # 测试缓存功能
    print("=" * 60)
    print("测试缓存管理器")
    print("=" * 60)
    
    # 测试 LRU 缓存
    print("\n1. 测试 LRU 缓存")
    lru = LRUCache(max_size=3, ttl_seconds=10)
    
    lru.put("key1", "value1")
    lru.put("key2", "value2")
    lru.put("key3", "value3")
    
    print(f"获取 key1: {lru.get('key1')}")
    print(f"获取 key2: {lru.get('key2')}")
    print(f"获取不存在的键: {lru.get('key4')}")
    
    print(f"\n缓存统计: {lru.get_stats()}")
    
    # 测试 Embedding 缓存
    print("\n2. 测试 Embedding 缓存")
    emb_cache = EmbeddingCache(cache_dir="./test_cache", max_memory_size=10)
    
    test_embedding = [0.1, 0.2, 0.3, 0.4, 0.5]
    emb_cache.put("测试文本", test_embedding)
    
    cached = emb_cache.get("测试文本")
    print(f"缓存的 Embedding: {cached}")
    print(f"缓存统计: {emb_cache.get_stats()}")
    
    # 清理测试缓存
    emb_cache.clear()
    
    print("\n✅ 缓存测试完成")
