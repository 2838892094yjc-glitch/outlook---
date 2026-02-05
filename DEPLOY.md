# Zeabur 部署指南

## 前置条件

- 已注册 Zeabur 账号：https://zeabur.com
- 已绑定 GitHub 账号
- 已注册 Azure 应用（已完成）

## 部署步骤

### 1. 准备代码仓库

```bash
# 初始化 Git 仓库（如果还没有）
cd outlook_web
git init

# 添加文件（不包括 .env）
git add .
git commit -m "Initial commit"

# 推送到 GitHub（需要先在 GitHub 创建仓库）
git remote add origin https://github.com/你的用户名/outlook-web-tool.git
git push -u origin main
```

### 2. 在 Zeabur 创建项目

1. 访问 https://zeabur.com/dashboard
2. 点击 "Create Project"
3. 选择 "Deploy from GitHub"
4. 选择你的仓库
5. 选择区域（推荐 Asia-East / Singapore）

### 3. 添加 PostgreSQL 服务

1. 在项目页面点击 "Add Service"
2. 选择 "PostgreSQL"
3. 等待创建完成（约 1 分钟）

### 4. 添加 Redis 服务（可选）

1. 点击 "Add Service"
2. 选择 "Redis"
3. 等待创建完成

### 5. 配置环境变量

进入应用服务 → Environment Variables，添加以下变量：

#### 必填变量

| 变量名 | 值 | 说明 |
|-------|---|------|
| `SECRET_KEY` | `openssl rand -base64 32` | 随机 32 位字符串 |
| `ENCRYPTION_KEY` | `openssl rand -base64 32` | 随机 32 位字符串（不同于上面的） |
| `MICROSOFT_CLIENT_ID` | `你的Azure应用ID` | Azure 应用 ID |
| `MICROSOFT_CLIENT_SECRET` | `你的Azure应用密钥` | Azure 应用密钥 |
| `MICROSOFT_REDIRECT_URI` | `https://你的域名.zeabur.app/auth/callback` | OAuth 回调地址 |
| `MICROSOFT_TENANT_ID` | `common` 或你的租户ID | Azure 租户 ID |

#### SMTP 配置

| 变量名 | 值 | 说明 |
|-------|---|------|
| `SMTP_HOST` | `smtp-mail.outlook.com` | Outlook SMTP 服务器 |
| `SMTP_PORT` | `587` | 端口 |
| `SMTP_USER` | `你的邮箱@outlook.com` | 发件邮箱 |
| `SMTP_PASSWORD` | `你的密码或应用密码` | 邮箱密码 |
| `SMTP_USE_TLS` | `true` | 使用 TLS 加密 |

#### AI 配置（可选，不配置则使用原文）

| 变量名 | 值 | 说明 |
|-------|---|------|
| `AI_API_URL` | `https://api.openai.com/v1` | AI API 地址 |
| `AI_API_KEY` | `sk-...` | API 密钥 |
| `AI_MODEL` | `gpt-4` | 模型名称 |

#### 自动生成变量（无需手动设置）

- `DATABASE_URL` - PostgreSQL 连接地址（自动）
- `REDIS_URL` - Redis 连接地址（自动）

### 6. 更新 Azure OAuth 回调地址

1. 访问 https://portal.azure.com
2. 进入应用注册 → 邮件助手
3. 点击 "身份验证" → "添加平台"
4. 添加 Web 平台
5. 添加重定向 URI：`https://你的域名.zeabur.app/auth/callback`
6. 保存

### 7. 部署应用

1. 在 Zeabur 项目页面，点击 "Deploy" 或等待自动部署
2. 等待构建完成（约 2-3 分钟）
3. 访问生成的域名测试

### 8. 绑定自定义域名（可选）

1. 在 Zeabur 应用服务页面
2. 点击 "Domains"
3. 选择 "Custom Domain"
4. 输入你的域名（如 `outlook.yourdomain.com`）
5. 按照指引添加 DNS 记录
6. 等待 SSL 证书自动颁发

## 部署后检查清单

- [ ] 访问首页正常显示
- [ ] 点击"使用 Microsoft 账号登录"跳转正常
- [ ] OAuth 登录后能成功回调
- [ ] 控制台页面正常显示
- [ ] 点击"抓取邮件"成功
- [ ] 邮件列表能显示抓取的邮件
- [ ] 点击"AI 处理并发送"成功
- [ ] 收到处理后的邮件

## 故障排查

### 问题：OAuth 回调失败

**原因：** Redirect URI 不匹配

**解决：**
1. 检查 Azure 中的回调地址是否与部署域名一致
2. 检查 `MICROSOFT_REDIRECT_URI` 环境变量
3. 确保包含 `https://` 和完整路径 `/auth/callback`

### 问题：邮件发送失败

**原因：** SMTP 认证失败

**解决：**
1. 如果开启了 Outlook 两步验证，需要生成应用密码
2. 访问 https://account.live.com/proofs/Manage
3. 生成应用密码并替换 `SMTP_PASSWORD`

### 问题：数据库连接失败

**原因：** PostgreSQL 未正确连接

**解决：**
1. 检查是否添加了 PostgreSQL 服务
2. 检查 `DATABASE_URL` 是否已自动生成
3. 重启应用服务

### 问题：内存不足

**原因：** 免费额度内存限制

**解决：**
1. 升级 Zeabur 套餐
2. 或优化代码减少内存使用

## 更新部署

代码更新后自动部署：

```bash
# 修改代码后
git add .
git commit -m "Update: xxx"
git push

# Zeabur 会自动检测到推送并重新部署
```

## 监控和日志

1. 在 Zeabur 控制台查看应用日志
2. 点击 "Logs" 查看实时输出
3. 可以使用 `/health` 接口检查健康状态

## 备份建议

- 定期导出 PostgreSQL 数据
- 环境变量导出保存到安全位置
- 代码使用 Git 版本控制