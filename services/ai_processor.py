import httpx
from typing import Optional
from config import settings


class AIProcessor:
    """AI 处理服务 - 翻译和摘要"""

    def __init__(self):
        self.api_url = settings.AI_API_URL
        self.api_key = settings.AI_API_KEY
        self.model = settings.AI_MODEL

    async def summarize(self, text: str, max_length: int = 200) -> str:
        """
        生成文本摘要

        Args:
            text: 原始文本
            max_length: 摘要最大长度

        Returns:
            摘要文本
        """
        if not text:
            return ""

        # 如果 AI 服务未配置，返回原文前 max_length 字符
        if not self.api_url or not self.api_key:
            return text[:max_length] + "..." if len(text) > max_length else text

        try:
            async with httpx.AsyncClient() as client:
                prompt = f"""请对以下邮件内容进行摘要，提取关键信息，限制在 {max_length} 字以内：

{text}

摘要："""

                response = await client.post(
                    f"{self.api_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model,
                        "messages": [
                            {
                                "role": "system",
                                "content": "你是一个邮件助手，擅长提取邮件关键信息。",
                            },
                            {"role": "user", "content": prompt},
                        ],
                        "max_tokens": max_length * 2,
                        "temperature": 0.3,
                    },
                    timeout=30.0,
                )

                response.raise_for_status()
                data = response.json()

                summary = (
                    data.get("choices", [{}])[0].get("message", {}).get("content", "")
                )
                return summary.strip()

        except Exception as e:
            print(f"AI 摘要失败: {e}")
            # 失败时返回原文前段
            return text[:max_length] + "..." if len(text) > max_length else text

    async def translate(self, text: str, target_lang: str = "zh") -> str:
        """
        翻译文本

        Args:
            text: 原始文本
            target_lang: 目标语言代码 (zh/en/ja/ko等)

        Returns:
            翻译后的文本
        """
        if not text:
            return ""

        # 如果 AI 服务未配置，返回原文
        if not self.api_url or not self.api_key:
            return text

        # 语言映射
        lang_names = {
            "zh": "中文",
            "en": "英文",
            "ja": "日文",
            "ko": "韩文",
            "fr": "法文",
            "de": "德文",
            "es": "西班牙文",
            "ru": "俄文",
        }

        target_name = lang_names.get(target_lang, target_lang)

        try:
            async with httpx.AsyncClient() as client:
                prompt = f"""请将以下邮件内容翻译成{target_name}，保持专业性和准确性：

{text}

{target_name}翻译："""

                response = await client.post(
                    f"{self.api_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model,
                        "messages": [
                            {
                                "role": "system",
                                "content": f"你是一个专业的邮件翻译助手，擅长将邮件翻译成{target_name}。",
                            },
                            {"role": "user", "content": prompt},
                        ],
                        "temperature": 0.3,
                    },
                    timeout=60.0,
                )

                response.raise_for_status()
                data = response.json()

                translation = (
                    data.get("choices", [{}])[0].get("message", {}).get("content", "")
                )
                return translation.strip()

        except Exception as e:
            print(f"AI 翻译失败: {e}")
            # 失败时返回原文
            return text

    async def process(
        self, text: str, mode: str = "summarize", target_lang: str = "zh"
    ) -> str:
        """
        处理邮件内容

        Args:
            text: 邮件正文
            mode: 处理模式 (summarize/translate/none)
            target_lang: 翻译目标语言

        Returns:
            处理后的文本
        """
        if mode == "none" or not mode:
            return text
        elif mode == "summarize":
            return await self.summarize(text)
        elif mode == "translate":
            return await self.translate(text, target_lang)
        else:
            return text


# 全局实例
ai_processor = AIProcessor()
