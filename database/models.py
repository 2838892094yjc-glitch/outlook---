from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Text,
    Boolean,
    DateTime,
    ForeignKey,
    JSON,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os

# Database URL from environment or default
DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://user:password@localhost/outlook_web"
)

engine = create_engine(
    DATABASE_URL,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    connect_args={"connect_timeout": 10}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


class User(Base):
    """用户表 - 对应一个 Microsoft 账号"""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=True)

    # OAuth Tokens (加密存储)
    access_token = Column(Text, nullable=True)
    refresh_token = Column(Text, nullable=True)
    token_expires_at = Column(DateTime, nullable=True)

    # 状态
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)

    # 关系
    emails = relationship("Email", back_populates="user")
    configs = relationship("UserConfig", back_populates="user", uselist=False)


class UserConfig(Base):
    """用户配置表"""

    __tablename__ = "user_configs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)

    # 抓取配置
    days_to_scrape = Column(Integer, default=7)  # 默认7天
    folders_to_scrape = Column(JSON, default=["Inbox"])  # 邮件文件夹
    sender_filter = Column(JSON, default=[])  # 发件人白名单
    keyword_filter = Column(JSON, default=[])  # 关键词
    only_unread = Column(Boolean, default=False)
    include_attachments = Column(Boolean, default=True)

    # 输出配置
    smtp_recipient = Column(String, nullable=True)  # 收件人邮箱
    ai_enabled = Column(Boolean, default=True)
    ai_mode = Column(String, default="summarize")  # summarize/translate/none
    target_language = Column(String, default="zh")  # 翻译目标语言

    # 定时任务
    auto_fetch = Column(Boolean, default=False)
    fetch_interval_hours = Column(Integer, default=24)

    # 关系
    user = relationship("User", back_populates="configs")


class Email(Base):
    """邮件缓存表"""

    __tablename__ = "emails"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))

    # 邮件元数据
    message_id = Column(String, unique=True, index=True)  # Microsoft Graph message ID
    subject = Column(String, nullable=True)
    sender_email = Column(String, nullable=True)
    sender_name = Column(String, nullable=True)
    received_at = Column(DateTime, nullable=True)

    # 内容
    body_html = Column(Text, nullable=True)
    body_text = Column(Text, nullable=True)
    has_attachments = Column(Boolean, default=False)
    attachments = Column(JSON, default=[])  # [{name, size, content_type}]

    # 处理状态
    is_read = Column(Boolean, default=False)
    is_processed = Column(Boolean, default=False)  # 是否已处理（AI+发送）
    processed_at = Column(DateTime, nullable=True)
    processed_content = Column(Text, nullable=True)  # AI处理后的内容
    sent = Column(Boolean, default=False)  # 是否已发送
    sent_at = Column(DateTime, nullable=True)

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)

    # 关系
    user = relationship("User", back_populates="emails")


class SendLog(Base):
    """发送日志表"""

    __tablename__ = "send_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    email_id = Column(Integer, ForeignKey("emails.id"), nullable=True)

    # 发送信息
    recipient = Column(String, nullable=False)
    subject = Column(String, nullable=False)
    status = Column(String, nullable=False)  # success/failed/pending
    error_message = Column(Text, nullable=True)

    # 时间
    created_at = Column(DateTime, default=datetime.utcnow)


class FetchLog(Base):
    """抓取日志表"""

    __tablename__ = "fetch_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))

    # 抓取信息
    total_emails = Column(Integer, default=0)
    new_emails = Column(Integer, default=0)
    status = Column(String, nullable=False)  # success/failed
    error_message = Column(Text, nullable=True)

    # 时间
    created_at = Column(DateTime, default=datetime.utcnow)


# 创建所有表
def init_db():
    Base.metadata.create_all(bind=engine)


# 获取数据库会话
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
