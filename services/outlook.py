import httpx
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from config import settings


class MicrosoftAuthService:
    """Microsoft OAuth 2.0 服务"""

    # Microsoft Graph API 端点
    AUTH_URL = f"https://login.microsoftonline.com/{settings.MICROSOFT_TENANT_ID}/oauth2/v2.0/authorize"
    TOKEN_URL = f"https://login.microsoftonline.com/{settings.MICROSOFT_TENANT_ID}/oauth2/v2.0/token"
    GRAPH_API_BASE = "https://graph.microsoft.com/v1.0"

    # 需要的权限范围
    SCOPES = [
        "openid",
        "profile",
        "email",
        "offline_access",  # 用于获取 refresh_token
        "Mail.Read",
        "Mail.ReadBasic",
    ]

    @classmethod
    def get_auth_url(cls, state: str) -> str:
        """获取 OAuth 授权 URL"""
        scope = " ".join(cls.SCOPES)
        auth_url = (
            f"{cls.AUTH_URL}?"
            f"client_id={settings.MICROSOFT_CLIENT_ID}"
            f"&response_type=code"
            f"&redirect_uri={settings.MICROSOFT_REDIRECT_URI}"
            f"&scope={scope}"
            f"&state={state}"
            f"&response_mode=query"
        )
        return auth_url

    @classmethod
    async def exchange_code_for_token(cls, code: str) -> Dict[str, Any]:
        """用授权码换取 Token"""
        async with httpx.AsyncClient() as client:
            data = {
                "client_id": settings.MICROSOFT_CLIENT_ID,
                "client_secret": settings.MICROSOFT_CLIENT_SECRET,
                "code": code,
                "redirect_uri": settings.MICROSOFT_REDIRECT_URI,
                "grant_type": "authorization_code",
            }

            response = await client.post(cls.TOKEN_URL, data=data)
            response.raise_for_status()

            token_data = response.json()

            # 计算过期时间
            expires_in = token_data.get("expires_in", 3600)
            token_data["expires_at"] = datetime.utcnow() + timedelta(seconds=expires_in)

            return token_data

    @classmethod
    async def refresh_access_token(cls, refresh_token: str) -> Dict[str, Any]:
        """使用 Refresh Token 刷新 Access Token"""
        async with httpx.AsyncClient() as client:
            data = {
                "client_id": settings.MICROSOFT_CLIENT_ID,
                "client_secret": settings.MICROSOFT_CLIENT_SECRET,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
                "scope": " ".join(cls.SCOPES),
            }

            response = await client.post(cls.TOKEN_URL, data=data)
            response.raise_for_status()

            token_data = response.json()

            # 计算新的过期时间
            expires_in = token_data.get("expires_in", 3600)
            token_data["expires_at"] = datetime.utcnow() + timedelta(seconds=expires_in)

            return token_data

    @classmethod
    async def get_user_info(cls, access_token: str) -> Dict[str, Any]:
        """获取用户信息"""
        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {access_token}"}
            response = await client.get(f"{cls.GRAPH_API_BASE}/me", headers=headers)
            response.raise_for_status()
            return response.json()


class OutlookService:
    """Outlook 邮件服务"""

    GRAPH_API_BASE = "https://graph.microsoft.com/v1.0"

    def __init__(self, access_token: str):
        self.access_token = access_token
        self.headers = {"Authorization": f"Bearer {access_token}"}

    async def get_messages(
        self,
        folder: str = "Inbox",
        days: int = 7,
        sender: Optional[str] = None,
        keyword: Optional[str] = None,
        only_unread: bool = False,
        limit: int = 50,
    ) -> list:
        """获取邮件列表"""
        # 构建筛选条件
        filters = []

        # 时间筛选
        since_date = datetime.utcnow() - timedelta(days=days)
        filters.append(f"receivedDateTime ge {since_date.isoformat()}Z")

        # 发件人筛选
        if sender:
            filters.append(f"from/emailAddress/address eq '{sender}'")

        # 关键词筛选（搜索主题或正文）
        if keyword:
            # Microsoft Graph 搜索需要特殊处理，这里先用简单筛选
            pass

        # 已读/未读筛选
        if only_unread:
            filters.append("isRead eq false")

        # 构建 URL
        filter_query = " and ".join(filters) if filters else ""
        url = f"{self.GRAPH_API_BASE}/me/mailFolders/{folder}/messages"

        params = {
            "$top": limit,
            "$orderby": "receivedDateTime desc",
            "$select": "id,subject,from,receivedDateTime,bodyPreview,hasAttachments,isRead",
        }

        if filter_query:
            params["$filter"] = filter_query

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            data = response.json()
            return data.get("value", [])

    async def get_message_detail(self, message_id: str) -> dict:
        """获取邮件详情（包括完整正文）"""
        url = f"{self.GRAPH_API_BASE}/me/messages/{message_id}"
        params = {
            "$select": "id,subject,from,toRecipients,receivedDateTime,body,bodyPreview,hasAttachments,isRead"
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json()

    async def get_attachments(self, message_id: str) -> list:
        """获取邮件附件列表"""
        url = f"{self.GRAPH_API_BASE}/me/messages/{message_id}/attachments"

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self.headers)
            response.raise_for_status()
            data = response.json()
            return data.get("value", [])

    async def get_attachment_content(
        self, message_id: str, attachment_name: str
    ) -> bytes:
        """获取附件内容（二进制）"""
        # 首先获取附件列表找到 ID
        attachments = await self.get_attachments(message_id)
        attachment_id = None

        for att in attachments:
            if att.get("name") == attachment_name:
                attachment_id = att.get("id")
                break

        if not attachment_id:
            return b""

        # 获取附件内容
        url = f"{self.GRAPH_API_BASE}/me/messages/{message_id}/attachments/{attachment_id}/$value"

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self.headers)
            response.raise_for_status()
            return response.content
