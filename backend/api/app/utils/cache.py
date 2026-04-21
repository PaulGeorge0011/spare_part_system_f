# app/utils/cache.py
"""
简单的 API 响应缓存工具
用于缓存筛选选项等不常变更的数据，减少数据库查询
"""
import json
import hashlib
from typing import Optional, Any, Callable
from functools import wraps
import redis
from app.core.config import settings

# 创建 Redis 连接
try:
    redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
except Exception:
    redis_client = None

# 缓存键前缀
CACHE_PREFIX = "api_cache:"

# 默认过期时间（秒）
DEFAULT_TTL = 300  # 5 分钟
FILTER_OPTIONS_TTL = 600  # 筛选选项缓存 10 分钟


def get_cache_key(prefix: str, *args, **kwargs) -> str:
    """生成缓存键"""
    key_data = f"{prefix}:{json.dumps(args, sort_keys=True)}:{json.dumps(kwargs, sort_keys=True)}"
    return f"{CACHE_PREFIX}{hashlib.md5(key_data.encode()).hexdigest()}"


def get_cached(key: str) -> Optional[Any]:
    """获取缓存数据"""
    if not redis_client:
        return None
    try:
        data = redis_client.get(key)
        if data:
            return json.loads(data)
    except Exception:
        pass
    return None


def set_cached(key: str, data: Any, ttl: int = DEFAULT_TTL) -> bool:
    """设置缓存数据"""
    if not redis_client:
        return False
    try:
        redis_client.setex(key, ttl, json.dumps(data, default=str))
        return True
    except Exception:
        return False


def delete_cached(key: str) -> bool:
    """删除缓存"""
    if not redis_client:
        return False
    try:
        redis_client.delete(key)
        return True
    except Exception:
        return False


def clear_cache_pattern(pattern: str) -> int:
    """清除匹配模式的所有缓存"""
    if not redis_client:
        return 0
    try:
        keys = redis_client.keys(f"{CACHE_PREFIX}{pattern}*")
        if keys:
            return redis_client.delete(*keys)
    except Exception:
        pass
    return 0


def invalidate_filter_options_cache():
    """清除所有筛选选项缓存（当备件数据变更时调用）"""
    clear_cache_pattern("filter_options:")
    clear_cache_pattern("electrical_filter:")
    clear_cache_pattern("mechanical_filter:")


def cache_response(prefix: str, ttl: int = DEFAULT_TTL):
    """
    缓存装饰器，用于 API 响应缓存
    
    用法:
    @cache_response("filter_options", ttl=600)
    def get_filter_options(...):
        ...
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 生成缓存键
            cache_key = get_cache_key(prefix, *args[1:], **kwargs)  # 跳过 db 参数
            
            # 尝试获取缓存
            cached_data = get_cached(cache_key)
            if cached_data is not None:
                return cached_data
            
            # 执行原函数
            result = func(*args, **kwargs)
            
            # 缓存结果
            set_cached(cache_key, result, ttl)
            
            return result
        return wrapper
    return decorator


# 内存缓存（用于极高频访问的小数据，如配置）
_memory_cache: dict = {}


def memory_cache_get(key: str) -> Optional[Any]:
    """获取内存缓存"""
    item = _memory_cache.get(key)
    if item:
        import time
        if item['expire'] > time.time():
            return item['data']
        else:
            del _memory_cache[key]
    return None


def memory_cache_set(key: str, data: Any, ttl: int = 60) -> None:
    """设置内存缓存"""
    import time
    _memory_cache[key] = {
        'data': data,
        'expire': time.time() + ttl
    }
