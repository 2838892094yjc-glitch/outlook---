# Outlook邮箱每日总结推送-港校必备

基于 FastAPI 的 Outlook 邮件自动处理工具，部署于 Zeabur。

## 功能特性

- ✅ Microsoft OAuth 登录 - 安全的官方认证
- ✅ 多账号管理 - 完全隔离存储
- ✅ 自动抓取邮件 - 支持多种筛选条件
- ✅ AI 智能处理 - 翻译/摘要
- ✅ SMTP 邮件发送 - 使用你的邮件服务
- ✅ Web 管理界面 - 简单直观的操作

## 技术栈

- **后端**: FastAPI + SQLAlchemy + PostgreSQL
- **认证**: Microsoft OAuth 2.0
- **AI**: OpenAI/Claude API（云端）
- **邮件**: Microsoft Graph API + SMTP
- **部署**: Zeabur (Docker + PostgreSQL + Redis)

## 快速开始

### 在线使用

访问部署地址：https://your-app.zeabur.app

### 本地开发

```bash
# 1. 克隆仓库
git clone https://github.com/你的用户名/outlook-web-tool.git
cd outlook-web-tool/outlook_web

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置环境变量
cp .env.example .env
# 编辑 .env 文件填入配置

# 4. 运行
python main.py

# 5. 访问 http://localhost:8000
```

## 使用流程

1. **登录** - 使用 Microsoft 账号 OAuth 登录
2. **配置** - 设置抓取天数、AI 模式、收件人邮箱
3. **抓取** - 点击"抓取邮件"获取 Outlook 邮件
4. **处理** - 点击"AI 处理并发送"自动翻译/摘要并发送
5. **查看** - 在邮件列表中查看处理状态

## 项目结构

```
outlook_web/
├── main.py                     # FastAPI 入口
├── config.py                   # 环境变量配置
├── requirements.txt            # Python 依赖
├── Dockerfile                  # 容器配置
├── zeabur.yaml                # Zeabur 部署配置
├── DEPLOY.md                  # 详细部署指南 ⭐
├── database/
│   ├── __init__.py
│   └── models.py              # PostgreSQL 数据模型
├── routers/
│   ├── __init__.py
│   ├── auth.py                # OAuth 认证
│   ├── dashboard.py           # 控制台 + 配置 + 邮件列表
│   └── api.py                 # API 接口（抓取/处理/邮件管理）
├── services/
│   ├── __init__.py
│   ├── outlook.py             # Microsoft Graph API
│   ├── ai_processor.py        # AI 翻译/摘要
│   └── smtp_sender.py         # SMTP 邮件发送
├── utils/
│   └── __init__.py            # Token 加密/缓存
└── templates/
    └── index.html             # 首页
```

## 数据模型

### User（用户）
- 对应一个 Microsoft 账号
- 存储 OAuth Token（加密）
- Token 自动刷新

### UserConfig（用户配置）
- 抓取配置：天数、文件夹、发件人筛选、关键词、已读/未读
- 输出配置：收件人邮箱、AI 模式（翻译/摘要/原文）、目标语言
- 附件配置：是否下载

### Email（邮件）
- 缓存抓取的邮件（正文、附件信息）
- 处理状态：是否已 AI 处理、是否已发送
- 处理结果：翻译/摘要后的内容

### SendLog（发送日志）
- 记录每次发送的详情
- 成功/失败状态
- 错误信息

## 部署到 Zeabur

### 简要步骤

1. Fork 或推送代码到 GitHub
2. 在 Zeabur 创建项目，选择 GitHub 仓库
3. 添加 PostgreSQL 服务
4. 配置环境变量（见下方）
5. 更新 Azure OAuth 回调地址
6. 部署完成！

### 详细指南

参见 [DEPLOY.md](./DEPLOY.md)

### 必需环境变量

| 变量 | 说明 |
|-----|------|
| `SECRET_KEY` | 随机字符串（`openssl rand -base64 32`）|
| `ENCRYPTION_KEY` | 另一个随机字符串 |
| `MICROSOFT_CLIENT_ID` | Azure 应用 ID |
| `MICROSOFT_CLIENT_SECRET` | Azure 应用密钥 |
| `MICROSOFT_REDIRECT_URI` | `https://你的域名.zeabur.app/auth/callback` |
| `MICROSOFT_TENANT_ID` | Azure 租户 ID |
| `SMTP_HOST` | SMTP 服务器（如 smtp-mail.outlook.com）|
| `SMTP_PORT` | SMTP 端口（如 587）|
| `SMTP_USER` | 发件邮箱 |
| `SMTP_PASSWORD` | 邮箱密码或应用密码 |
| `SMTP_USE_TLS` | `true` |

**自动生成变量（无需设置）**:
- `DATABASE_URL` - Zeabur PostgreSQL 自动提供
- `REDIS_URL` - Zeabur Redis 自动提供

### 可选环境变量

| 变量 | 说明 | 默认值 |
|-----|------|--------|
| `AI_API_URL` | AI 服务地址 | - |
| `AI_API_KEY` | AI API 密钥 | - |
| `AI_MODEL` | AI 模型 | gpt-4 |
| `APP_NAME` | 应用名称 | Outlook Web Tool |
| `DEBUG` | 调试模式 | false |

## API 接口

### 认证
- `GET /auth/login` - 开始 OAuth 登录
- `GET /auth/callback` - OAuth 回调
- `GET /auth/logout` - 退出登录

### 控制台
- `GET /` - 首页
- `GET /dashboard` - 控制台（配置 + 操作按钮）
- `GET /dashboard/emails` - 邮件列表

### API
- `GET /api/emails` - 获取邮件列表
- `GET /api/emails/{id}` - 获取邮件详情
- `DELETE /api/emails/{id}` - 删除邮件
- `POST /api/fetch` - 抓取邮件
- `POST /api/process` - AI 处理并发送
- `POST /api/config` - 更新配置
- `GET /health` - 健康检查

## 技术细节

### OAuth 流程
1. 生成随机 state 防止 CSRF
2. 跳转到 Microsoft 授权页面
3. 用户授权后回调到 `/auth/callback`
4. 验证 state，交换 code 获取 Token
5. 加密存储 Token，设置 Session

### Token 管理
- Access Token 加密存储在 PostgreSQL
- Refresh Token 用于自动续期
- 内存缓存减少解密次数
- Session 使用 Redis（7 天有效期）

### AI 处理
- 支持翻译和摘要两种模式
- 调用云端 AI API（OpenAI/Claude）
- 未配置时自动降级为原文

### SMTP 发送
- 使用配置的 SMTP 服务器
- 支持 HTML + 纯文本双格式
- 附件自动下载并转发
- 精美的邮件模板

## 安全说明

- ✅ OAuth Token 使用 Fernet 加密存储
- ✅ Session 使用 Redis，支持 HTTPS-only cookie
- ✅ 所有 API 需要登录验证
- ✅ CSRF 防护（state 参数验证）
- ✅ SQL 注入防护（SQLAlchemy ORM）
- ✅ 用户数据完全隔离

## 开发完成清单

- [x] Phase 1: 基础框架 + 数据库模型
- [x] Phase 2: OAuth 认证 + Session 管理
- [x] Phase 3: 邮件抓取 + 存储 + 列表
- [x] Phase 4: AI 处理 + SMTP 发送
- [x] Phase 5: Zeabur 部署配置

## 后续优化建议

- [ ] 添加定时任务（APScheduler）
- [ ] 邮件搜索功能
- [ ] 批量操作（删除、标记已读）
- [ ] 邮件详情页面
- [ ] 附件预览/下载
- [ ] 多语言界面
- [ ] 深色模式
- [ ] 移动端适配
- [ ] 单元测试
- [ ] API 文档（Swagger UI 已自带）

## 许可证

MIT License - 详见 LICENSE 文件

## 支持

遇到问题？
1. 查看 [DEPLOY.md](./DEPLOY.md) 故障排查部分
2. 检查 Zeabur 控制台日志
3. 访问 `/health` 检查服务状态

---

**⚠️ 安全提醒**：`.env` 文件包含敏感信息，已添加到 `.gitignore`，切勿提交到 Git！
