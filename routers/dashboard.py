from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from database.models import get_db, UserConfig
from routers.auth import get_current_user, get_current_user_optional
from utils import decrypt_token

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def dashboard(
    request: Request, user=Depends(get_current_user), db: Session = Depends(get_db)
):
    """用户控制台"""

    # 获取用户配置
    config = db.query(UserConfig).filter(UserConfig.user_id == user.id).first()

    if not config:
        config = UserConfig(user_id=user.id)
        db.add(config)
        db.commit()
        db.refresh(config)

    html = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>控制台 - Outlook Web Tool</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f5f5f5;
            min-height: 100vh;
        }}
        .header {{
            background: #0078d4;
            color: white;
            padding: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .header h1 {{ font-size: 20px; }}
        .user-info {{ font-size: 14px; opacity: 0.9; }}
        .logout-btn {{
            background: rgba(255,255,255,0.2);
            color: white;
            padding: 8px 16px;
            border-radius: 4px;
            text-decoration: none;
            font-size: 14px;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 30px 20px;
        }}
        .card {{
            background: white;
            border-radius: 8px;
            padding: 24px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .card h2 {{
            font-size: 18px;
            margin-bottom: 16px;
            color: #333;
        }}
        .info-row {{
            display: flex;
            margin-bottom: 12px;
            padding: 8px 0;
            border-bottom: 1px solid #eee;
        }}
        .info-label {{
            width: 120px;
            color: #666;
            font-size: 14px;
        }}
        .info-value {{
            flex: 1;
            color: #333;
            font-size: 14px;
        }}
        .config-form {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 16px;
        }}
        .form-group {{
            margin-bottom: 16px;
        }}
        .form-group label {{
            display: block;
            margin-bottom: 6px;
            font-size: 14px;
            color: #333;
            font-weight: 500;
        }}
        .form-group input,
        .form-group select {{
            width: 100%;
            padding: 8px 12px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 14px;
        }}
        .form-group input:focus,
        .form-group select:focus {{
            outline: none;
            border-color: #0078d4;
        }}
        .checkbox-group {{
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .checkbox-group input {{ width: auto; }}
        .btn {{
            background: #0078d4;
            color: white;
            padding: 12px 24px;
            border: none;
            border-radius: 4px;
            font-size: 14px;
            cursor: pointer;
            transition: background 0.2s;
        }}
        .btn:hover {{ background: #005a9e; }}
        .btn-success {{ background: #28a745; }}
        .btn-success:hover {{ background: #218838; }}
        .btn-group {{
            display: flex;
            gap: 12px;
            margin-top: 20px;
        }}
        .status {{
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
        }}
        .status.active {{
            background: #d4edda;
            color: #155724;
        }}
        .status.inactive {{
            background: #f8d7da;
            color: #721c24;
        }}
    </style>
</head>
<body>
    <div class="header">
        <div>
            <h1>Outlook Web Tool</h1>
            <div class="user-info">{user.email} {f"({user.name})" if user.name else ""}</div>
        </div>
        <a href="/auth/logout" class="logout-btn">退出登录</a>
    </div>
    
    <div class="container">
        <!-- 账号信息 -->
        <div class="card">
            <h2>📧 账号信息</h2>
            <div class="info-row">
                <div class="info-label">邮箱地址</div>
                <div class="info-value">{user.email}</div>
            </div>
            <div class="info-row">
                <div class="info-label">显示名称</div>
                <div class="info-value">{user.name or "未设置"}</div>
            </div>
            <div class="info-row">
                <div class="info-label">登录状态</div>
                <div class="info-value">
                    <span class="status active">已连接</span>
                </div>
            </div>
            <div class="info-row">
                <div class="info-label">上次登录</div>
                <div class="info-value">{user.last_login.strftime("%Y-%m-%d %H:%M:%S") if user.last_login else "未知"}</div>
            </div>
        </div>
        
        <!-- 抓取配置 -->
        <div class="card">
            <h2>⚙️ 抓取配置</h2>
            <form id="configForm" class="config-form">
                <div class="form-group">
                    <label>抓取天数范围</label>
                    <input type="number" name="days_to_scrape" value="{config.days_to_scrape}" min="1" max="365">
                </div>
                
                <div class="form-group">
                    <label>收件人邮箱</label>
                    <input type="email" name="smtp_recipient" value="{config.smtp_recipient or ""}" placeholder="处理后发送到此邮箱">
                </div>
                
                <div class="form-group">
                    <label>AI 处理模式</label>
                    <select name="ai_mode">
                        <option value="summarize" {"selected" if config.ai_mode == "summarize" else ""}>摘要</option>
                        <option value="translate" {"selected" if config.ai_mode == "translate" else ""}>翻译</option>
                        <option value="none" {"selected" if config.ai_mode == "none" else ""}>不处理（原文）</option>
                    </select>
                </div>
                
                <div class="form-group">
                    <label class="checkbox-group">
                        <input type="checkbox" name="only_unread" {"checked" if config.only_unread else ""}>
                        <span>仅抓取未读邮件</span>
                    </label>
                </div>
                
                <div class="form-group">
                    <label class="checkbox-group">
                        <input type="checkbox" name="include_attachments" {"checked" if config.include_attachments else ""}>
                        <span>下载附件</span>
                    </label>
                </div>
            </form>
        </div>
        
        <!-- 操作按钮 -->
        <div class="card">
            <h2>🚀 执行操作</h2>
            <div class="btn-group">
                <button class="btn btn-success" onclick="fetchEmails()">
                    📥 抓取邮件
                </button>
                <button class="btn" onclick="processEmails()">
                    🤖 AI 处理并发送
                </button>
                <a href="/dashboard/emails" class="btn" style="background: #6c757d; text-decoration: none;">
                    📧 查看邮件列表
                </a>
            </div>
            <div id="status" style="margin-top: 16px; padding: 12px; border-radius: 4px; display: none;"></div>
        </div>
    </div>
    
    <script>
        // 保存配置
        document.getElementById('configForm').addEventListener('change', async function(e) {{
            const formData = new FormData(this);
            const data = {{}};
            formData.forEach((value, key) => {{
                if (key === 'only_unread' || key === 'include_attachments') {{
                    data[key] = true;
                }} else {{
                    data[key] = value;
                }}
            }});
            
            // 处理 checkbox 未勾选的情况
            if (!formData.has('only_unread')) data.only_unread = false;
            if (!formData.has('include_attachments')) data.include_attachments = false;
            
            try {{
                const response = await fetch('/api/config', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify(data)
                }});
                
                if (response.ok) {{
                    showStatus('配置已保存', 'success');
                }} else {{
                    showStatus('保存失败', 'error');
                }}
            }} catch (error) {{
                showStatus('网络错误', 'error');
            }}
        }});
        
        // 抓取邮件
        async function fetchEmails() {{
            showStatus('正在抓取邮件...', 'info');
            try {{
                const response = await fetch('/api/fetch', {{method: 'POST'}});
                const result = await response.json();
                
                if (response.ok) {{
                    showStatus(`✅ 抓取完成！共 {{result.total}} 封邮件，其中 {{result.new}} 封是新邮件`, 'success');
                }} else {{
                    showStatus('❌ ' + result.detail, 'error');
                }}
            }} catch (error) {{
                showStatus('❌ 网络错误: ' + error.message, 'error');
            }}
        }}
        
        // 处理邮件
        async function processEmails() {{
            showStatus('正在处理邮件...', 'info');
            try {{
                const response = await fetch('/api/process', {{method: 'POST'}});
                const result = await response.json();
                
                if (response.ok) {{
                    showStatus(`✅ 处理完成！已发送 {{result.sent}} 封邮件`, 'success');
                }} else {{
                    showStatus('❌ ' + result.detail, 'error');
                }}
            }} catch (error) {{
                showStatus('❌ 网络错误: ' + error.message, 'error');
            }}
        }}
        
        function showStatus(message, type) {{
            const status = document.getElementById('status');
            status.textContent = message;
            status.style.display = 'block';
            status.style.background = type === 'success' ? '#d4edda' : type === 'error' ? '#f8d7da' : '#d1ecf1';
            status.style.color = type === 'success' ? '#155724' : type === 'error' ? '#721c24' : '#0c5460';
        }}
    </script>
</body>
</html>
    """

    return html


@router.post("/config")
async def update_config(
    request: Request, user=Depends(get_current_user), db: Session = Depends(get_db)
):
    """更新用户配置"""
    from pydantic import BaseModel

    class ConfigUpdate(BaseModel):
        days_to_scrape: int = 7
        smtp_recipient: str = ""
        ai_mode: str = "summarize"
        only_unread: bool = False
        include_attachments: bool = True

    try:
        data = await request.json()
        config_update = ConfigUpdate(**data)

        config = db.query(UserConfig).filter(UserConfig.user_id == user.id).first()

        if not config:
            config = UserConfig(user_id=user.id)
            db.add(config)

        config.days_to_scrape = config_update.days_to_scrape
        config.smtp_recipient = config_update.smtp_recipient
        config.ai_mode = config_update.ai_mode
        config.only_unread = config_update.only_unread
        config.include_attachments = config_update.include_attachments

        db.commit()

        return {"message": "配置已更新"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/emails", response_class=HTMLResponse)
async def emails_list(
    request: Request,
    page: int = 1,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """邮件列表页面"""
    from database.models import Email

    per_page = 20
    skip = (page - 1) * per_page

    # 获取邮件列表
    emails = (
        db.query(Email)
        .filter(Email.user_id == user.id)
        .order_by(Email.received_at.desc())
        .offset(skip)
        .limit(per_page + 1)
        .all()
    )  # 多取一条判断是否还有下一页

    has_next = len(emails) > per_page
    emails = emails[:per_page]  # 去掉多取的那条

    html = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>邮件列表 - Outlook Web Tool</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f5f5f5;
            min-height: 100vh;
        }}
        .header {{
            background: #0078d4;
            color: white;
            padding: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .header h1 {{ font-size: 20px; }}
        .back-link {{
            color: white;
            text-decoration: none;
            font-size: 14px;
            opacity: 0.9;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 30px 20px;
        }}
        .email-list {{
            background: white;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .email-item {{
            padding: 16px 20px;
            border-bottom: 1px solid #eee;
            display: flex;
            align-items: center;
            gap: 16px;
        }}
        .email-item:last-child {{ border-bottom: none; }}
        .email-item:hover {{ background: #f8f9fa; }}
        .email-sender {{
            width: 200px;
            flex-shrink: 0;
        }}
        .sender-name {{
            font-weight: 500;
            color: #333;
            font-size: 14px;
        }}
        .sender-email {{
            font-size: 12px;
            color: #666;
        }}
        .email-content {{
            flex: 1;
            min-width: 0;
        }}
        .email-subject {{
            font-weight: 500;
            color: #333;
            margin-bottom: 4px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}
        .email-preview {{
            font-size: 13px;
            color: #666;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}
        .email-meta {{
            width: 150px;
            text-align: right;
            flex-shrink: 0;
        }}
        .email-date {{
            font-size: 13px;
            color: #999;
        }}
        .email-status {{
            display: inline-block;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 11px;
            margin-top: 4px;
        }}
        .status-new {{ background: #d4edda; color: #155724; }}
        .status-processed {{ background: #cce5ff; color: #004085; }}
        .status-sent {{ background: #d1ecf1; color: #0c5460; }}
        .badge {{
            display: inline-block;
            padding: 2px 6px;
            background: #ffc107;
            color: #856404;
            border-radius: 4px;
            font-size: 11px;
            margin-left: 8px;
        }}
        .pagination {{
            display: flex;
            justify-content: center;
            gap: 10px;
            margin-top: 20px;
        }}
        .pagination a {{
            padding: 8px 16px;
            background: white;
            border: 1px solid #ddd;
            border-radius: 4px;
            text-decoration: none;
            color: #333;
        }}
        .pagination a:hover {{ background: #f8f9fa; }}
        .empty-state {{
            text-align: center;
            padding: 60px 20px;
            color: #666;
        }}
        .empty-state h3 {{
            margin-bottom: 10px;
            color: #333;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>📧 邮件列表</h1>
        <a href="/dashboard" class="back-link">← 返回控制台</a>
    </div>
    
    <div class="container">
        <div class="email-list">
            {
        "".join(
            [
                f'''
            <div class="email-item">
                <div class="email-sender">
                    <div class="sender-name">{e.sender_name or e.sender_email}</div>
                    <div class="sender-email">{e.sender_email}</div>
                </div>
                <div class="email-content">
                    <div class="email-subject">
                        {e.subject or "(无主题)"}
                        {'<span class="badge">📎</span>' if e.has_attachments else ""}
                    </div>
                    <div class="email-preview">{e.body_text[:100] if e.body_text else ""}</div>
                </div>
                <div class="email-meta">
                    <div class="email-date">{e.received_at.strftime("%m-%d %H:%M") if e.received_at else ""}</div>
                    <span class="email-status {"status-sent" if e.sent else "status-processed" if e.is_processed else "status-new"}">
                        {"已发送" if e.sent else "已处理" if e.is_processed else "新邮件"}
                    </span>
                </div>
            </div>
            '''
                for e in emails
            ]
        )
        if emails
        else '''
            <div class="empty-state">
                <h3>暂无邮件</h3>
                <p>请先抓取邮件或调整筛选条件</p>
            </div>
            '''
    }
        </div>
        
        <div class="pagination">
            {
        f'<a href="/dashboard/emails?page={page - 1}">上一页</a>' if page > 1 else ""
    }
            <span style="padding: 8px 16px;">第 {page} 页</span>
            {
        f'<a href="/dashboard/emails?page={page + 1}">下一页</a>' if has_next else ""
    }
        </div>
    </div>
</body>
</html>
    """

    return html
