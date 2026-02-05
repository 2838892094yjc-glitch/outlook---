import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import List, Optional
from datetime import datetime
import base64
from config import settings


class SMTPSender:
    """SMTP 邮件发送服务"""

    def __init__(self):
        self.host = settings.SMTP_HOST
        self.port = settings.SMTP_PORT
        self.user = settings.SMTP_USER
        self.password = settings.SMTP_PASSWORD
        self.use_tls = settings.SMTP_USE_TLS

    async def send_email(
        self,
        to_email: str,
        subject: str,
        body_html: str,
        body_text: Optional[str] = None,
        attachments: Optional[List[dict]] = None,
    ) -> dict:
        """
        发送邮件

        Args:
            to_email: 收件人邮箱
            subject: 邮件主题
            body_html: HTML 正文
            body_text: 纯文本正文（可选）
            attachments: 附件列表 [{name, content_type, content(base64)}]

        Returns:
            {"success": bool, "message": str}
        """
        try:
            # 创建邮件
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.user
            msg["To"] = to_email
            msg["Date"] = datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S +0000")

            # 添加正文
            if body_text:
                msg.attach(MIMEText(body_text, "plain", "utf-8"))
            if body_html:
                msg.attach(MIMEText(body_html, "html", "utf-8"))

            # 添加附件
            if attachments:
                for attachment in attachments:
                    try:
                        part = MIMEBase("application", "octet-stream")
                        content = base64.b64decode(attachment["content"])
                        part.set_payload(content)
                        encoders.encode_base64(part)
                        part.add_header(
                            "Content-Disposition",
                            f'attachment; filename="{attachment["name"]}"',
                        )
                        msg.attach(part)
                    except Exception as e:
                        print(f"附件处理失败 {attachment.get('name')}: {e}")
                        continue

            # 发送邮件
            async with aiosmtplib.SMTP(
                hostname=self.host, port=self.port, use_tls=self.use_tls
            ) as smtp:
                await smtp.login(self.user, self.password)
                await smtp.send_message(msg)

            return {"success": True, "message": "邮件发送成功"}

        except Exception as e:
            return {"success": False, "message": f"邮件发送失败: {str(e)}"}

    async def send_processed_email(
        self,
        to_email: str,
        original_subject: str,
        original_sender: str,
        original_date: datetime,
        processed_content: str,
        original_body: Optional[str] = None,
        attachments: Optional[List[dict]] = None,
    ) -> dict:
        """
        发送处理后的邮件

        Args:
            to_email: 收件人邮箱
            original_subject: 原邮件主题
            original_sender: 原发件人
            original_date: 原邮件日期
            processed_content: AI 处理后的内容
            original_body: 原文内容（可选）
            attachments: 附件列表

        Returns:
            {"success": bool, "message": str}
        """
        # 构建主题
        subject = f"[Outlook助手] {original_subject}"

        # 构建 HTML 正文
        html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
        }}
        .header {{
            background: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
            border-left: 4px solid #0078d4;
        }}
        .header-item {{
            margin: 5px 0;
            font-size: 14px;
        }}
        .header-label {{
            color: #666;
            font-weight: 500;
        }}
        .content {{
            background: white;
            padding: 20px;
            border: 1px solid #e9ecef;
            border-radius: 8px;
            margin-bottom: 20px;
        }}
        .content h2 {{
            margin-top: 0;
            color: #0078d4;
            font-size: 18px;
        }}
        .original {{
            background: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
            border: 1px solid #e9ecef;
        }}
        .original h3 {{
            margin-top: 0;
            color: #666;
            font-size: 14px;
        }}
        .footer {{
            text-align: center;
            color: #999;
            font-size: 12px;
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #e9ecef;
        }}
    </style>
</head>
<body>
    <div class="header">
        <div class="header-item"><span class="header-label">原邮件主题：</span>{
            original_subject
        }</div>
        <div class="header-item"><span class="header-label">发件人：</span>{
            original_sender
        }</div>
        <div class="header-item"><span class="header-label">时间：</span>{
            original_date.strftime("%Y-%m-%d %H:%M:%S") if original_date else "未知"
        }</div>
    </div>
    
    <div class="content">
        <h2>🤖 AI 处理结果</h2>
        <div>{processed_content.replace(chr(10), "<br>")}</div>
    </div>
    
    {
            f'''
    <div class="original">
        <h3>📧 原始邮件内容</h3>
        <div>{original_body.replace(chr(10), "<br>")}</div>
    </div>
    '''
            if original_body
            else ""
        }
    
    <div class="footer">
        由 Outlook Web Tool 自动处理发送<br>
        发送时间：{datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")}
    </div>
</body>
</html>
        """

        # 构建纯文本正文
        text_body = f"""原邮件主题：{original_subject}
发件人：{original_sender}
时间：{original_date.strftime("%Y-%m-%d %H:%M:%S") if original_date else "未知"}

--- AI 处理结果 ---

{processed_content}

---
由 Outlook Web Tool 自动处理发送
        """

        return await self.send_email(
            to_email=to_email,
            subject=subject,
            body_html=html_body,
            body_text=text_body,
            attachments=attachments,
        )


# 全局实例
smtp_sender = SMTPSender()
