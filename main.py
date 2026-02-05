from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy.orm import Session
import uvicorn

from database.models import init_db, get_db, User, UserConfig
from config import settings

# 初始化 FastAPI 应用
app = FastAPI(
    title=settings.APP_NAME, description="Outlook 邮件自动处理工具", version="1.0.0"
)

# 添加 Session 中间件（用于 OAuth state 验证和用户登录状态）
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SECRET_KEY,
    max_age=3600 * 24 * 7,  # 7 天有效期
)

# 静态文件和模板
try:
    app.mount("/static", StaticFiles(directory="static"), name="static")
except:
    pass  # 目录不存在时跳过

templates = Jinja2Templates(directory="templates")

# 导入路由
from routers import auth, dashboard, api

app.include_router(auth.router, prefix="/auth", tags=["认证"])
app.include_router(dashboard.router, prefix="/dashboard", tags=["控制台"])
app.include_router(api.router, prefix="/api", tags=["API"])


@app.on_event("startup")
async def startup_event():
    """应用启动时初始化数据库"""
    import time
    max_retries = 3
    retry_delay = 2

    for attempt in range(max_retries):
        try:
            init_db()
            print(f"🚀 {settings.APP_NAME} 启动成功！")
            print(f"📊 数据库: {settings.DATABASE_URL[:30]}...")
            break
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"⚠️ 数据库连接失败 (尝试 {attempt + 1}/{max_retries}): {str(e)[:100]}")
                time.sleep(retry_delay)
            else:
                print(f"❌ 数据库连接失败: {str(e)[:200]}")
                raise


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """首页 - 重定向到登录或控制台"""
    return templates.TemplateResponse(
        "index.html", {"request": request, "app_name": settings.APP_NAME}
    )


@app.get("/health")
async def health_check():
    """健康检查接口"""
    return {"status": "ok", "app": settings.APP_NAME}


if __name__ == "__main__":
    import os
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=settings.DEBUG)
