from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database.models import get_db, Email, FetchLog, SendLog
from routers.auth import get_current_user
from services.outlook import OutlookService
from services.ai_processor import ai_processor
from services.smtp_sender import smtp_sender
from utils import decrypt_token, get_cached_token
from datetime import datetime
import base64
import httpx

router = APIRouter()


@router.get("/emails")
async def get_emails(
    skip: int = 0,
    limit: int = 50,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取用户的邮件列表"""
    emails = (
        db.query(Email)
        .filter(Email.user_id == user.id)
        .order_by(Email.received_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    return {
        "total": len(emails),
        "emails": [
            {
                "id": e.id,
                "message_id": e.message_id,
                "subject": e.subject,
                "sender_email": e.sender_email,
                "sender_name": e.sender_name,
                "received_at": e.received_at.isoformat() if e.received_at else None,
                "has_attachments": e.has_attachments,
                "is_read": e.is_read,
                "is_processed": e.is_processed,
                "sent": e.sent,
                "body_preview": e.body_text[:200] + "..."
                if e.body_text and len(e.body_text) > 200
                else e.body_text,
            }
            for e in emails
        ],
    }


@router.post("/fetch")
async def fetch_emails(user=Depends(get_current_user), db: Session = Depends(get_db)):
    """手动触发邮件抓取"""
    from database.models import UserConfig

    # 获取用户配置
    config = db.query(UserConfig).filter(UserConfig.user_id == user.id).first()
    if not config:
        raise HTTPException(status_code=400, detail="用户配置不存在")

    # 获取 access token
    access_token = get_cached_token(user.id)
    if not access_token:
        access_token = decrypt_token(user.access_token)
        if not access_token:
            raise HTTPException(status_code=401, detail="无法获取访问令牌，请重新登录")

    # 创建抓取日志
    fetch_log = FetchLog(user_id=user.id, status="running")
    db.add(fetch_log)
    db.commit()

    try:
        # 创建 Outlook 服务实例
        outlook = OutlookService(access_token)

        total_emails = 0
        new_emails = 0

        # 遍历配置的文件夹
        for folder in config.folders_to_scrape:
            try:
                # 获取邮件列表
                messages = await outlook.get_messages(
                    folder=folder,
                    days=config.days_to_scrape,
                    sender=config.sender_filter[0] if config.sender_filter else None,
                    only_unread=config.only_unread,
                    limit=100,  # 每次最多 100 封
                )

                total_emails += len(messages)

                for msg in messages:
                    message_id = msg.get("id")

                    # 检查是否已存在
                    existing = (
                        db.query(Email)
                        .filter(
                            Email.message_id == message_id, Email.user_id == user.id
                        )
                        .first()
                    )

                    if existing:
                        continue

                    # 获取邮件详情（包含完整正文）
                    detail = await outlook.get_message_detail(message_id)

                    # 获取附件信息
                    attachments = []
                    if msg.get("hasAttachments") and config.include_attachments:
                        attachments = await outlook.get_attachments(message_id)

                    # 创建邮件记录
                    from_addr = msg.get("from", {}).get("emailAddress", {})
                    received_time = msg.get("receivedDateTime")

                    email = Email(
                        user_id=user.id,
                        message_id=message_id,
                        subject=msg.get("subject", "(无主题)"),
                        sender_email=from_addr.get("address", ""),
                        sender_name=from_addr.get("name", ""),
                        received_at=datetime.fromisoformat(
                            received_time.replace("Z", "+00:00")
                        )
                        if received_time
                        else None,
                        body_html=detail.get("body", {}).get("content", ""),
                        body_text=msg.get("bodyPreview", ""),
                        has_attachments=msg.get("hasAttachments", False),
                        attachments=[
                            {
                                "name": a.get("name"),
                                "size": a.get("size"),
                                "content_type": a.get("contentType"),
                            }
                            for a in attachments
                        ],
                        is_read=msg.get("isRead", False),
                        is_processed=False,
                        sent=False,
                    )

                    db.add(email)
                    new_emails += 1

            except Exception as e:
                print(f"抓取文件夹 {folder} 时出错: {e}")
                continue

        db.commit()

        # 更新日志
        fetch_log.total_emails = total_emails
        fetch_log.new_emails = new_emails
        fetch_log.status = "success"
        db.commit()

        return {"message": "抓取完成", "total": total_emails, "new": new_emails}

    except Exception as e:
        # 更新日志为失败
        fetch_log.status = "failed"
        fetch_log.error_message = str(e)
        db.commit()

        raise HTTPException(status_code=500, detail=f"抓取失败: {str(e)}")


@router.post("/process")
async def process_emails(user=Depends(get_current_user), db: Session = Depends(get_db)):
    """
    处理邮件（AI + 发送）

    流程：
    1. 获取未处理且未发送的邮件
    2. AI 处理（翻译/摘要）
    3. SMTP 发送
    4. 更新状态
    """
    from database.models import UserConfig

    # 获取用户配置
    config = db.query(UserConfig).filter(UserConfig.user_id == user.id).first()
    if not config:
        raise HTTPException(status_code=400, detail="用户配置不存在")

    # 检查收件人配置
    if not config.smtp_recipient:
        raise HTTPException(status_code=400, detail="请先在配置中设置收件人邮箱")

    # 获取未处理且未发送的邮件
    emails = (
        db.query(Email)
        .filter(
            Email.user_id == user.id, Email.is_processed == False, Email.sent == False
        )
        .all()
    )

    if not emails:
        return {"message": "没有待处理的邮件", "processed": 0, "sent": 0}

    processed_count = 0
    sent_count = 0
    errors = []

    for email in emails:
        try:
            # 1. AI 处理
            content_to_process = email.body_text or email.body_html or ""

            if config.ai_enabled and config.ai_mode != "none":
                processed_content = await ai_processor.process(
                    text=content_to_process,
                    mode=config.ai_mode,
                    target_lang=config.target_language,
                )
            else:
                # AI 关闭时，直接使用原文
                processed_content = content_to_process

            # 更新邮件处理状态
            email.processed_content = processed_content
            email.is_processed = True
            email.processed_at = datetime.utcnow()
            processed_count += 1

            # 2. SMTP 发送
            # 下载附件内容（如果需要）
            attachments_with_content = []
            if email.has_attachments and config.include_attachments:
                # 获取 access token
                access_token = get_cached_token(user.id)
                if not access_token:
                    access_token = decrypt_token(user.access_token)

                if access_token:
                    outlook = OutlookService(access_token)
                    for att_info in email.attachments:
                        try:
                            # 下载附件内容
                            att_data = await outlook.get_attachment_content(
                                email.message_id, att_info.get("name", "")
                            )
                            if att_data:
                                attachments_with_content.append(
                                    {
                                        "name": att_info.get("name"),
                                        "content_type": att_info.get(
                                            "content_type", "application/octet-stream"
                                        ),
                                        "content": base64.b64encode(att_data).decode(),
                                    }
                                )
                        except Exception as e:
                            print(f"下载附件失败 {att_info.get('name')}: {e}")
                            continue

            # 发送邮件
            send_result = await smtp_sender.send_processed_email(
                to_email=config.smtp_recipient,
                original_subject=email.subject,
                original_sender=f"{email.sender_name} <{email.sender_email}>",
                original_date=email.received_at,
                processed_content=processed_content,
                original_body=email.body_text if config.ai_mode != "none" else None,
                attachments=attachments_with_content
                if attachments_with_content
                else None,
            )

            # 记录发送日志
            send_log = SendLog(
                user_id=user.id,
                email_id=email.id,
                recipient=config.smtp_recipient,
                subject=f"[Outlook助手] {email.subject}",
                status="success" if send_result["success"] else "failed",
                error_message=send_result.get("message")
                if not send_result["success"]
                else None,
            )
            db.add(send_log)

            if send_result["success"]:
                email.sent = True
                email.sent_at = datetime.utcnow()
                sent_count += 1
            else:
                errors.append(f"邮件 {email.id}: {send_result['message']}")

            db.commit()

        except Exception as e:
            error_msg = f"处理邮件 {email.id} 失败: {str(e)}"
            print(error_msg)
            errors.append(error_msg)

            # 记录失败日志
            send_log = SendLog(
                user_id=user.id,
                email_id=email.id,
                recipient=config.smtp_recipient,
                subject=f"[Outlook助手] {email.subject}",
                status="failed",
                error_message=str(e),
            )
            db.add(send_log)
            db.commit()
            continue

    return {
        "message": "处理完成",
        "total": len(emails),
        "processed": processed_count,
        "sent": sent_count,
        "errors": errors if errors else None,
    }


@router.get("/emails/{email_id}")
async def get_email_detail(
    email_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)
):
    """获取单封邮件详情"""
    email = (
        db.query(Email).filter(Email.id == email_id, Email.user_id == user.id).first()
    )

    if not email:
        raise HTTPException(status_code=404, detail="邮件不存在")

    return {
        "id": email.id,
        "message_id": email.message_id,
        "subject": email.subject,
        "sender_email": email.sender_email,
        "sender_name": email.sender_name,
        "received_at": email.received_at.isoformat() if email.received_at else None,
        "body_html": email.body_html,
        "body_text": email.body_text,
        "has_attachments": email.has_attachments,
        "attachments": email.attachments,
        "is_read": email.is_read,
        "is_processed": email.is_processed,
        "sent": email.sent,
        "processed_content": email.processed_content,
    }


@router.delete("/emails/{email_id}")
async def delete_email(
    email_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)
):
    """删除邮件记录"""
    email = (
        db.query(Email).filter(Email.id == email_id, Email.user_id == user.id).first()
    )

    if not email:
        raise HTTPException(status_code=404, detail="邮件不存在")

    db.delete(email)
    db.commit()

    return {"message": "邮件已删除"}
