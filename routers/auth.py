from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from datetime import datetime
import secrets

from database.models import get_db, User, UserConfig
from services.outlook import MicrosoftAuthService
from utils import encrypt_token, decrypt_token, cache_token
from config import settings

router = APIRouter()


def generate_state() -> str:
    """生成随机 state 防止 CSRF"""
    return secrets.token_urlsafe(32)


@router.get("/login")
async def login(request: Request):
    """Microsoft OAuth 登录入口"""
    # 生成 state 并存储到 session
    state = generate_state()
    request.session["oauth_state"] = state

    # 获取授权 URL
    auth_url = MicrosoftAuthService.get_auth_url(state)

    return RedirectResponse(url=auth_url)


@router.get("/callback")
async def callback(
    request: Request,
    code: str = None,
    state: str = None,
    error: str = None,
    error_description: str = None,
    db: Session = Depends(get_db),
):
    """OAuth 回调处理"""

    # 检查错误
    if error:
        raise HTTPException(
            status_code=400, detail=f"OAuth 错误: {error} - {error_description}"
        )

    if not code:
        raise HTTPException(status_code=400, detail="缺少授权码")

    # 验证 state 防止 CSRF
    stored_state = request.session.get("oauth_state")
    if not stored_state or stored_state != state:
        raise HTTPException(status_code=400, detail="无效的 state 参数")

    # 清除 state
    request.session.pop("oauth_state", None)

    try:
        # 用授权码换取 Token
        token_data = await MicrosoftAuthService.exchange_code_for_token(code)

        access_token = token_data.get("access_token")
        refresh_token = token_data.get("refresh_token")
        expires_at = token_data.get("expires_at")
        id_token = token_data.get("id_token", "")

        # 获取用户信息（可能失败）
        user_info = await MicrosoftAuthService.get_user_info(access_token)

        # 尝试从 user_info 获取邮箱，失败则从 ID token 提取
        email = user_info.get("mail") or user_info.get("userPrincipalName")
        name = user_info.get("displayName", "")

        # 如果无法从 Graph API 获取，尝试从 ID token 解析
        if not email and id_token:
            try:
                import json
                import base64
                # ID token 格式: header.payload.signature
                parts = id_token.split(".")
                if len(parts) >= 2:
                    # 解码 payload（第二部分）
                    payload = parts[1]
                    # 补充 padding
                    padding = 4 - len(payload) % 4
                    if padding != 4:
                        payload += "=" * padding
                    decoded = base64.urlsafe_b64decode(payload)
                    claims = json.loads(decoded)
                    email = claims.get("upn") or claims.get("email")
                    name = claims.get("name", "")
            except Exception as e:
                print(f"无法从 ID token 提取用户信息: {str(e)[:100]}")

        if not email:
            raise HTTPException(status_code=400, detail="无法获取用户邮箱，请确保在 Azure Portal 中已 Grant admin consent User.Read 权限")

        # 检查用户是否已存在
        user = db.query(User).filter(User.email == email).first()

        if user:
            # 更新现有用户
            user.name = name
            user.access_token = encrypt_token(access_token)
            user.refresh_token = encrypt_token(refresh_token)
            user.token_expires_at = expires_at
            user.last_login = datetime.utcnow()
        else:
            # 创建新用户
            user = User(
                email=email,
                name=name,
                access_token=encrypt_token(access_token),
                refresh_token=encrypt_token(refresh_token),
                token_expires_at=expires_at,
                last_login=datetime.utcnow(),
            )
            db.add(user)
            db.flush()  # 获取 user.id

            # 创建默认配置
            config = UserConfig(user_id=user.id)
            db.add(config)

        db.commit()

        # 缓存解密后的 Token 到内存（减少解密次数）
        cache_token(user.id, access_token)

        # 设置 session
        request.session["user_id"] = user.id
        request.session["user_email"] = email

        # 跳转到控制台
        return RedirectResponse(url="/dashboard")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OAuth 处理失败: {str(e)}")


@router.get("/logout")
async def logout(request: Request):
    """登出"""
    # 清除 session
    user_id = request.session.get("user_id")
    request.session.clear()

    # 清除 Token 缓存
    if user_id:
        from utils import clear_token_cache

        clear_token_cache(user_id)

    return RedirectResponse(url="/")


async def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    """获取当前登录用户"""
    user_id = request.session.get("user_id")

    if not user_id:
        raise HTTPException(status_code=401, detail="未登录")

    user = db.query(User).filter(User.id == user_id).first()

    if not user or not user.is_active:
        request.session.clear()
        raise HTTPException(status_code=401, detail="用户不存在或已禁用")

    # 检查 Token 是否过期
    if user.token_expires_at and user.token_expires_at < datetime.utcnow():
        # 尝试刷新 Token
        if user.refresh_token:
            try:
                refresh_token = decrypt_token(user.refresh_token)
                token_data = await MicrosoftAuthService.refresh_access_token(
                    refresh_token
                )

                user.access_token = encrypt_token(token_data.get("access_token"))
                user.refresh_token = encrypt_token(
                    token_data.get("refresh_token", refresh_token)
                )
                user.token_expires_at = token_data.get("expires_at")
                db.commit()

                # 更新缓存
                cache_token(user.id, token_data.get("access_token"))

            except Exception as e:
                # Token 刷新失败，需要重新登录
                request.session.clear()
                raise HTTPException(status_code=401, detail="Token 已过期，请重新登录")
        else:
            request.session.clear()
            raise HTTPException(status_code=401, detail="Token 已过期，请重新登录")

    return user


async def get_current_user_optional(
    request: Request, db: Session = Depends(get_db)
) -> User:
    """获取当前登录用户（可选，未登录返回 None）"""
    try:
        return await get_current_user(request, db)
    except HTTPException:
        return None
