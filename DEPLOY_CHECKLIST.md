# Zeabur 部署检查清单

使用此清单确保部署成功。

## 步骤 1: 准备代码

- [ ] 确认所有代码文件已保存
- [ ] 确认 `.env` 文件在 `.gitignore` 中
- [ ] 运行以下命令检查：
  ```bash
  cd outlook_web
  cat .gitignore | grep ".env"
  # 应该显示 ".env"
  ```

## 步骤 2: 创建 GitHub 仓库

- [ ] 访问 https://github.com/new
- [ ] 仓库名称：outlook-web-tool（或其他）
- [ ] 选择 Public 或 Private
- [ ] **不要**勾选 "Add a README file"
- [ ] **不要**勾选 "Add .gitignore"
- [ ] 点击 "Create repository"
- [ ] 复制仓库地址（如 https://github.com/你的用户名/outlook-web-tool.git）

## 步骤 3: 推送代码

```bash
cd outlook_web

# 初始化 Git（如果还没做）
git init

# 添加文件
git add .

# 提交
git commit -m "Initial commit for Zeabur deployment"

# 连接远程仓库（替换为你的仓库地址）
git remote add origin https://github.com/你的用户名/outlook-web-tool.git

# 推送
git push -u origin main
```

**检查**：访问 GitHub 仓库页面，确认文件已上传

## 步骤 4: Zeabur 创建项目

- [ ] 访问 https://zeabur.com/dashboard
- [ ] 点击 "Create Project"
- [ ] 选择 "Deploy from GitHub"
- [ ] 授权 GitHub（如果第一次使用）
- [ ] 选择 outlook-web-tool 仓库
- [ ] 选择地区：Asia East (Singapore)
- [ ] 等待创建（约 30 秒）

## 步骤 5: 添加 PostgreSQL

- [ ] 在项目页面点击 "Add Service"
- [ ] 选择 "PostgreSQL"
- [ ] 等待创建完成（约 1 分钟）
- [ ] 点击 PostgreSQL 服务
- [ ] 确认 "Connection String" 已自动生成

## 步骤 6: 生成密钥

```bash
# 生成两个随机密钥
openssl rand -base64 32
# 复制第一个作为 SECRET_KEY

openssl rand -base64 32
# 复制第二个作为 ENCRYPTION_KEY
```

## 步骤 7: 配置环境变量

在 Zeabur 控制台 → 你的应用服务 → Environment Variables：

### 基础配置

```
APP_NAME=Outlook Web Tool
DEBUG=false
SECRET_KEY=上面生成的第一个密钥
ENCRYPTION_KEY=上面生成的第二个密钥
```

### OAuth 配置（从 Azure Portal 获取）

```
MICROSOFT_CLIENT_ID=你的Azure应用ID
MICROSOFT_CLIENT_SECRET=你的Azure应用密钥
MICROSOFT_REDIRECT_URI=https://你的域名.zeabur.app/auth/callback
MICROSOFT_TENANT_ID=common
```

**注意**：将 `你的域名` 替换为 Zeabur 分配的域名（在控制台查看）

### SMTP 配置

```
SMTP_HOST=smtp-mail.outlook.com
SMTP_PORT=587
SMTP_USER=你的邮箱@outlook.com
SMTP_PASSWORD=你的密码或应用密码
SMTP_USE_TLS=true
```

**注意**：如果 Outlook 开启了两步验证，需要使用应用密码替代

### AI 配置（可选，暂时留空）

```
AI_API_URL=
AI_API_KEY=
AI_MODEL=gpt-4
```

### 自动生成变量（不要手动设置）

- DATABASE_URL ✅（PostgreSQL 服务自动提供）
- REDIS_URL ✅（可选，Redis 服务自动提供）

## 步骤 8: 部署应用

- [ ] 点击 "Deploy" 或等待自动部署
- [ ] 等待构建（约 2-3 分钟）
- [ ] 查看日志确保无错误：
  ```
  🚀 Outlook Web Tool 启动成功！
  📊 数据库: postgresql://...
  ```

## 步骤 9: 更新 Azure OAuth 回调

- [ ] 访问 https://portal.azure.com
- [ ] 进入 "应用注册" → "邮件助手"
- [ ] 点击左侧 "身份验证"
- [ ] 找到 "Web" 平台
- [ ] 点击 "添加 URI"
- [ ] 输入：`https://你的域名.zeabur.app/auth/callback`
- [ ] 点击 "保存"

**确认**：回调地址现在有两个：
- http://localhost:8000/auth/callback（本地开发）
- https://你的域名.zeabur.app/auth/callback（线上）

## 步骤 10: 功能测试

访问你的应用：`https://你的域名.zeabur.app`

### 测试 1: 首页
- [ ] 页面正常显示
- [ ] 能看到 "使用 Microsoft 账号登录" 按钮

### 测试 2: 登录
- [ ] 点击登录按钮
- [ ] 跳转到 Microsoft 登录页面
- [ ] 登录并授权
- [ ] 成功回调到控制台页面

### 测试 3: 配置
- [ ] 能看到账号信息
- [ ] 修改"收件人邮箱"为你自己的邮箱
- [ ] 修改"抓取天数"为 7
- [ ] 选择 AI 模式（可选：翻译/摘要/原文）
- [ ] 配置自动保存

### 测试 4: 抓取邮件
- [ ] 点击"📥 抓取邮件"
- [ ] 等待几秒
- [ ] 显示"抓取完成，共 X 封邮件，新增 Y 封"

### 测试 5: 查看邮件
- [ ] 点击"📧 查看邮件列表"
- [ ] 能看到抓取的邮件
- [ ] 状态显示"新邮件"

### 测试 6: 处理发送
- [ ] 返回控制台
- [ ] 点击"🤖 AI 处理并发送"
- [ ] 等待处理完成
- [ ] 检查你的收件邮箱，确认收到邮件

### 测试 7: 邮件内容
- [ ] 收到的邮件包含：
  - [ ] 原邮件主题
  - [ ] 发件人信息
  - [ ] AI 处理后的内容
  - [ ] 原文内容（如果 AI 模式不是原文）
  - [ ] 附件（如果有）

## 故障排查

如果测试失败，查看 Zeabur 日志：

1. 进入 Zeabur 控制台
2. 点击你的应用服务
3. 点击 "Logs"
4. 查看最新错误信息

### 常见问题

**登录失败**
- 检查 `MICROSOFT_REDIRECT_URI` 是否与 Azure 中配置的一致
- 检查是否包含 `https://` 和 `/auth/callback`

**数据库错误**
- 确认添加了 PostgreSQL 服务
- 确认 `DATABASE_URL` 已自动生成

**SMTP 错误**
- 如果 Outlook 有两步验证，使用应用密码
- 检查 `SMTP_USER` 和 `SMTP_PASSWORD`

**AI 处理无反应**
- 未配置 AI API 时，会自动使用原文
- 这是正常行为

## 完成！

所有检查项完成后，部署成功！🎉

后续更新代码只需：
```bash
git add .
git commit -m "Update: xxx"
git push
```

Zeabur 会自动重新部署。