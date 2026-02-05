from cryptography.fernet import Fernet
import base64
import os

# 从环境变量获取加密密钥，如果没有则生成一个
# 注意：生产环境应该固定密钥，否则重启后无法解密
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")
if not ENCRYPTION_KEY:
    # 生成 32 字节密钥并转为 base64
    key = Fernet.generate_key()
    ENCRYPTION_KEY = key.decode()
    print(f"⚠️  生成临时加密密钥: {ENCRYPTION_KEY}")
    print("⚠️  生产环境请设置 ENCRYPTION_KEY 环境变量")

fernet = Fernet(
    ENCRYPTION_KEY.encode() if isinstance(ENCRYPTION_KEY, str) else ENCRYPTION_KEY
)


def encrypt_token(token: str) -> str:
    """加密 Token"""
    if not token:
        return ""
    return fernet.encrypt(token.encode()).decode()


def decrypt_token(encrypted_token: str) -> str:
    """解密 Token"""
    if not encrypted_token:
        return ""
    try:
        return fernet.decrypt(encrypted_token.encode()).decode()
    except Exception:
        return ""


# 为了安全，限制 Token 只在内存中短暂存在
token_cache = {}


def get_cached_token(user_id: int) -> str:
    """从缓存获取解密后的 Token（避免频繁解密）"""
    return token_cache.get(user_id, "")


def cache_token(user_id: int, token: str):
    """缓存解密后的 Token"""
    token_cache[user_id] = token


from typing import Optional


def clear_token_cache(user_id: Optional[int] = None):
    """清除 Token 缓存"""
    if user_id is not None:
        token_cache.pop(user_id, None)
    else:
        token_cache.clear()
