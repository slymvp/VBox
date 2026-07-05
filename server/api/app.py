
"""
VBox REST API 服务
使用 FastAPI 提供统一的查询接口，支持PC端、移动端、电视端访问
"""
from fastapi import FastAPI, Query, HTTPException, Body, Request, File, UploadFile, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional, List
import sys
import os
import httpx
import hashlib
import json
from datetime import datetime, timedelta, timezone

# 加载环境变量（有 fallback 机制）
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # 如果没有 dotenv，就不加载，直接使用环境变量
    pass


def utc_plus_8() -> datetime:
    """获取 UTC+8 时区的当前时间（只到秒级）"""
    now = datetime.now(timezone.utc) + timedelta(hours=8)
    return now.replace(microsecond=0)


def escape_like(keyword: str) -> str:
    """转义LIKE查询中的特殊字符，防止SQL注入"""
    # 转义 % _ \ 三个LIKE通配符
    keyword = keyword.replace('\\', '\\\\')
    keyword = keyword.replace('%', '\\%')
    keyword = keyword.replace('_', '\\_')
    return keyword


# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import DatabaseManager
from core.logger import setup_logger

logger = setup_logger('vbox.api')

# 管理端认证
from core.auth import create_access_token, decode_token, get_password_hash, verify_password
from models import AdminUser, SessionLocal

security = HTTPBearer(auto_error=False)

ADMIN_TOKEN_EXPIRE_HOURS = 24


def _create_admin_token(admin_user) -> str:
    """为管理员创建 JWT token"""
    return create_access_token(
        data={"sub": str(admin_user.id), "role": admin_user.role, "username": admin_user.username},
        expires_delta=timedelta(hours=ADMIN_TOKEN_EXPIRE_HOURS)
    )


def _verify_admin_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """验证管理员 token，返回管理员用户信息"""
    if not credentials:
        logger.warning("401: 未提供认证凭据（缺少 Authorization 头）")
        raise HTTPException(status_code=401, detail="未提供认证凭据")
    payload = decode_token(credentials.credentials)
    if not payload:
        logger.warning(f"401: Token 解码失败或已过期 (token 前20位: {credentials.credentials[:20]}...)")
        raise HTTPException(status_code=401, detail="认证已过期或无效")
    if payload.get("type") != "access":
        logger.warning(f"401: Token type 不是 access，实际为: {payload.get('type')}")
        raise HTTPException(status_code=401, detail="认证已过期或无效")
    admin_id = payload.get("sub")
    if not admin_id:
        logger.warning("401: Token 中缺少 sub 字段")
        raise HTTPException(status_code=401, detail="无效的认证信息")
    try:
        admin_id = int(admin_id)
    except (ValueError, TypeError):
        logger.warning(f"401: Token 中 sub 字段无效: {admin_id}")
        raise HTTPException(status_code=401, detail="无效的认证信息")
    session = SessionLocal()
    try:
        admin = session.query(AdminUser).filter(AdminUser.id == admin_id, AdminUser.is_active == True).first()
        if not admin:
            logger.warning(f"401: 管理员 {admin_id} 不存在或已被禁用")
            raise HTTPException(status_code=401, detail="账号不存在或已被禁用")
        return admin
    finally:
        session.close()


def _require_admin(admin=Depends(_verify_admin_token)):
    """要求管理员角色为 admin（超级管理员）"""
    if admin.role != 'admin':
        raise HTTPException(status_code=403, detail="仅超级管理员可执行此操作")
    return admin


def init_default_admin():
    """初始化默认管理员账号"""
    session = SessionLocal()
    try:
        existing = session.query(AdminUser).filter(AdminUser.username == 'admin').first()
        if not existing:
            admin = AdminUser(
                username='admin',
                password_hash=get_password_hash('sly888'),
                role='admin',
                nickname='超级管理员',
                is_active=True
            )
            session.add(admin)
            session.commit()
            logger.info("已创建默认管理员账号: admin")
        else:
            logger.info("管理员账号已存在，跳过初始化")
    except Exception as e:
        session.rollback()
        logger.error(f"初始化管理员失败: {e}")
    finally:
        session.close()

# 定时任务相关
from apscheduler.schedulers.background import BackgroundScheduler
from contextlib import asynccontextmanager

scheduler = BackgroundScheduler()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI生命周期管理：启动和关闭定时任务"""
    # 初始化默认管理员账号
    init_default_admin()

    # 初始化爬虫任务调度器
    from core.task_scheduler import get_scheduler
    crawl_scheduler = get_scheduler()
    crawl_scheduler.initialize()  # 使用默认配置和数据库路径
    crawl_scheduler.start()
    logger.info("爬虫任务调度器已启动")

    # 启动定时任务
    scheduler.start()
    logger.info("定时任务调度器已启动")

    # 从数据库加载已有定时任务
    _load_scheduled_tasks_from_db()

    yield

    # 关闭定时任务
    scheduler.shutdown()
    logger.info("定时任务调度器已关闭")

    # 关闭爬虫任务调度器
    crawl_scheduler.stop()
    logger.info("爬虫任务调度器已关闭")

# 创建FastAPI应用
app = FastAPI(
    title="VBox API",
    description="多平台视频数据查询接口",
    version="1.0.0",
    docs_url=None,
    redoc_url=None,
    lifespan=lifespan
)

# 配置CORS（允许跨域访问）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api")
def api_root():
    """API根路径"""
    return {
        "message": "VBox API Service",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/api/health")
def health_check():
    """健康检查接口"""
    return {"status": "ok"}


@app.get("/api/series")
def list_series(
    category: Optional[str] = Query(None, description="频道过滤 (tv, movie, variety, cartoon, child)"),
    platform: Optional[str] = Query(None, description="平台过滤 (iqiyi, tencent, youku, mgtv, bilibili)"),
    year: Optional[str] = Query(None, description="年份过滤"),
    area: Optional[str] = Query(None, description="地区过滤"),
    tag: Optional[str] = Query(None, description="标签过滤"),
    director: Optional[str] = Query(None, description="导演过滤"),
    actor: Optional[str] = Query(None, description="演员过滤"),
    sort: Optional[str] = Query(None, description="排序方式: hot-最热, new-最新, score-评分"),
    min_score: Optional[float] = Query(None, description="最低评分过滤"),
    page: int = Query(1, ge=1, description="页码"),
    limit: int = Query(20, ge=1, le=100, description="每页数量")
):
    """
    获取剧集列表

    - **category**: 可选，频道 (tv, movie, variety, cartoon, child)，不传则跨频道查询
    - **platform**: 可选，平台名称
    - **year**: 可选，年份
    - **area**: 可选，地区
    - **tag**: 可选，标签
    - **director**: 可选，导演
    - **actor**: 可选，演员
    - **sort**: 可选，排序方式 (hot-最热, new-最新, score-评分)
    - **min_score**: 可选，最低评分过滤
    - **page**: 页码，从1开始
    - **limit**: 每页数量，最大100
    """
    try:
        if category:
            result = DatabaseManager.list_series(category, platform=platform, year=year, area=area, tag=tag, director=director, actor=actor, sort=sort, min_score=min_score, page=page, limit=limit)
        else:
            result = DatabaseManager.list_series_all(platform=platform, year=year, area=area, tag=tag, director=director, actor=actor, sort=sort, min_score=min_score, page=page, limit=limit)
        # 给每个item补充category_key
        for item in result.get('items', []):
            if 'category_key' not in item:
                item['category_key'] = category or 'tv'
        return {
            "code": 0,
            "message": "success",
            "data": result
        }
    except Exception as e:
        logger.error(f"获取剧集列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/series/{cid}")
def get_series_detail(
    cid: str,
    category: str = Query(None, description="频道标识 (tv, movie, variety, cartoon, child)，不传则自动查找")
):
    """
    获取剧集详情（包含分集信息）

    - **cid**: 剧集ID
    - **category**: 频道标识，不传则跨频道自动查找
    """
    try:
        result = None
        if category:
            result = DatabaseManager.get_series_with_episodes(category, cid)
            if result:
                result['category_key'] = category
        if not result:
            result = DatabaseManager.find_series_with_episodes_by_cid(cid)
        if not result:
            raise HTTPException(status_code=404, detail=f"剧集不存在: {cid}")
        return {
            "code": 0,
            "message": "success",
            "data": result
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取剧集详情失败: {cid}, 错误: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/episodes")
def list_episodes(
    series_id: int = Query(..., description="剧集ID"),
    category: str = Query("tv", description="频道标识 (tv, movie, variety, cartoon, child)"),
    page: int = Query(1, ge=1, description="页码"),
    limit: int = Query(50, ge=1, le=200, description="每页数量")
):
    """
    获取分集列表

    - **series_id**: 剧集数据库ID
    - **category**: 频道标识，默认tv
    - **page**: 页码
    - **limit**: 每页数量，最大200
    """
    try:
        result = DatabaseManager.list_episodes(category, series_id=series_id, page=page, limit=limit)
        return {
            "code": 0,
            "message": "success",
            "data": result
        }
    except Exception as e:
        logger.error(f"获取分集列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/search")
def search_series(
    keyword: str = Query(..., min_length=1, description="搜索关键词"),
    platform: Optional[str] = Query(None, description="平台过滤"),
    category: Optional[str] = Query(None, description="频道过滤 (tv, movie, variety, cartoon, child)"),
    page: int = Query(1, ge=1, description="页码"),
    limit: int = Query(20, ge=1, le=100, description="每页数量")
):
    """
    搜索剧集

    - **keyword**: 搜索关键词
    - **platform**: 可选，平台过滤
    - **category**: 可选，频道过滤，不传则跨频道搜索
    - **page**: 页码
    - **limit**: 每页数量
    """
    try:
        logger.info(f"搜索关键词: {keyword}")
        if category:
            result = DatabaseManager.list_series(category, platform=platform, keyword=keyword, page=page, limit=limit)
            for item in result.get('items', []):
                item['category_key'] = category
        else:
            result = DatabaseManager.search_series_all(keyword=keyword, platform=platform, page=page, limit=limit)
        result['keyword'] = keyword
        return {
            "code": 0,
            "message": "success",
            "data": result
        }
    except Exception as e:
        logger.error(f"搜索失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stats")
def get_stats():
    """
    获取统计数据

    返回：
    - 总剧集数
    - 总分集数
    - 各平台数量分布
    - 最后更新时间
    """
    try:
        stats = DatabaseManager.get_stats()
        return {
            "code": 0,
            "message": "success",
            "data": stats
        }
    except Exception as e:
        logger.error(f"获取统计数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/filter-options")
def get_filter_options(
    category: str = Query(..., description="频道标识 (tv, movie, variety, cartoon, child)"),
    platform: Optional[str] = Query(None, description="平台过滤")
):
    """
    获取筛选选项（年份、地区、标签、导演、演员的去重列表）

    - **category**: 频道标识（必填）
    - **platform**: 可选，平台过滤
    """
    try:
        result = DatabaseManager.get_filter_options(category, platform=platform)
        return {
            "code": 0,
            "message": "success",
            "data": result
        }
    except Exception as e:
        logger.error(f"获取筛选选项失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/platforms")
def list_platforms():
    """
    获取支持的平台列表（从数据库动态读取）
    """
    platforms = DatabaseManager.list_platforms(enabled_only=True)
    data = []
    for p in platforms:
        data.append({"key": p["key"], "name": p["name"], "icon": p.get("icon", "")})
    return {
        "code": 0,
        "message": "success",
        "data": data
    }


@app.get("/api/categories")
def list_categories():
    """
    获取支持的分类列表（从数据库动态读取）
    """
    categories = DatabaseManager.list_categories(enabled_only=True)
    data = []
    for c in categories:
        data.append({
            "key": c["key"],
            "name": c["name"],
            "icon": c.get("icon", "")
        })
    return {
        "code": 0,
        "message": "success",
        "data": data
    }


@app.get("/api/parse_sources")
def get_parse_sources(platform: Optional[str] = None):
    """
    获取视频解析源配置（从数据库读取）
    platform: 可选，平台key，如 iqiyi, tencent, youku, mgtv, bilibili
    """
    try:
        platform_id = None
        if platform and platform != '':
            platform_obj = DatabaseManager().get_platform_by_key(platform)
            if platform_obj:
                platform_id = platform_obj.get('id')

        sources = DatabaseManager().list_parse_sources(enabled_only=True, platform_id=platform_id)
        data = []
        for s in sources:
            data.append({"key": s["key"], "name": s["name"], "url": s["url"]})
        return {
            "code": 0,
            "message": "success",
            "data": data
        }
    except Exception as e:
        logger.error(f"读取解析源配置失败: {e}")
        return {
            "code": 1,
            "message": str(e),
            "data": []
        }


@app.get("/api/proxy/image")
def proxy_image(url: str = Query(..., description="图片URL")):
    """
    图片代理接口 - 绕过封面图防盗链
    通过后端请求图片并转发给前端，避免浏览器直接请求被拒绝
    """
    # 安全校验：只允许代理已知图片域名
    allowed_domains = [
        'pic0.iqiyipic.com', 'pic1.iqiyipic.com', 'pic2.iqiyipic.com', 'pic3.iqiyipic.com',
        'pic4.iqiyipic.com', 'pic5.iqiyipic.com', 'pic6.iqiyipic.com', 'pic7.iqiyipic.com',
        'pic8.iqiyipic.com', 'pic9.iqiyipic.com',
        'vpic-cover.puui.qpic.cn', 'puui.qpic.cn',
        'img.360kan.com', 'image.360kan.com',
        'img2.rrys.tv', 'img.rrys.tv',
        'm.360kan.com',
    ]

    from urllib.parse import urlparse
    parsed = urlparse(url)
    domain_allowed = any(parsed.hostname and parsed.hostname.endswith(d) for d in allowed_domains)

    if not domain_allowed:
        # 对于未知域名也允许代理，但记录日志
        logger.warning(f"代理未知域名图片: {parsed.hostname}")

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': f'{parsed.scheme}://{parsed.hostname}/' if parsed.hostname else '',
        }

        with httpx.Client(timeout=15, follow_redirects=True) as client:
            response = client.get(url, headers=headers)
            if response.status_code == 200:
                content_type = response.headers.get('content-type', 'image/jpeg')
                return StreamingResponse(
                    iter([response.content]),
                    media_type=content_type,
                    headers={
                        'Cache-Control': 'public, max-age=86400',
                        'Access-Control-Allow-Origin': '*',
                    }
                )
            elif response.status_code == 404:
                raise HTTPException(status_code=404, detail="图片不存在")
            else:
                raise HTTPException(status_code=response.status_code, detail="图片请求失败")
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="图片请求超时")
    except Exception as e:
        logger.error(f"图片代理失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 管理端 API ====================

class AdminLoginRequest(BaseModel):
    username: str
    password: str


@app.post("/admin-api/login")
def admin_login(request: AdminLoginRequest):
    """
    管理端登录（JWT认证）
    """
    try:
        session = SessionLocal()
        try:
            admin = session.query(AdminUser).filter(
                AdminUser.username == request.username,
                AdminUser.is_active == True
            ).first()
            if not admin or not verify_password(request.password, admin.password_hash):
                return {"code": 1, "message": "用户名或密码错误", "data": None}
            # 更新最后登录时间
            admin.last_login = utc_plus_8()
            session.commit()
            token = _create_admin_token(admin)
            return {
                "code": 0,
                "message": "登录成功",
                "data": {
                    "token": token,
                    "user": admin.to_dict()
                }
            }
        finally:
            session.close()
    except Exception as e:
        logger.error(f"管理端登录失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/admin-api/admin-info")
def admin_get_info(admin=Depends(_verify_admin_token)):
    """获取当前登录管理员信息"""
    return {"code": 0, "message": "success", "data": admin.to_dict()}


@app.post("/admin-api/change-password")
def admin_change_password(
    data: dict = Body(...),
    admin=Depends(_verify_admin_token)
):
    """修改当前管理员密码"""
    try:
        old_password = data.get('old_password', '')
        new_password = data.get('new_password', '')
        if not old_password or not new_password:
            return {"code": 1, "message": "请填写旧密码和新密码", "data": None}
        if len(new_password) < 6:
            return {"code": 1, "message": "新密码至少6位", "data": None}
        if not verify_password(old_password, admin.password_hash):
            return {"code": 1, "message": "旧密码不正确", "data": None}
        session = SessionLocal()
        try:
            admin_db = session.query(AdminUser).filter(AdminUser.id == admin.id).first()
            admin_db.password_hash = get_password_hash(new_password)
            session.commit()
            return {"code": 0, "message": "密码修改成功", "data": None}
        finally:
            session.close()
    except Exception as e:
        logger.error(f"修改密码失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 管理员账号管理 API ====================

class AdminUserRequest(BaseModel):
    username: str
    password: str
    role: str = 'operator'
    nickname: Optional[str] = None


@app.get("/admin-api/admin-users")
def admin_list_users(admin=Depends(_verify_admin_token)):
    """获取所有管理员列表（仅超级管理员可访问）"""
    if admin.role != 'admin':
        return {"code": 1, "message": "仅超级管理员可访问", "data": None}
    try:
        session = SessionLocal()
        try:
            users = session.query(AdminUser).order_by(AdminUser.id.asc()).all()
            return {
                "code": 0,
                "message": "success",
                "data": [u.to_dict() for u in users]
            }
        finally:
            session.close()
    except Exception as e:
        logger.error(f"获取管理员列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/admin-api/admin-users")
def admin_create_user(
    request: AdminUserRequest,
    admin=Depends(_verify_admin_token)
):
    """创建管理员/操作员账号（仅超级管理员可访问）"""
    if admin.role != 'admin':
        return {"code": 1, "message": "仅超级管理员可访问", "data": None}
    try:
        if not request.username or len(request.username) < 2:
            return {"code": 1, "message": "用户名至少2个字符", "data": None}
        if not request.password or len(request.password) < 6:
            return {"code": 1, "message": "密码至少6位", "data": None}
        if request.role not in ('admin', 'operator'):
            return {"code": 1, "message": "角色只能是 admin 或 operator", "data": None}
        session = SessionLocal()
        try:
            existing = session.query(AdminUser).filter(AdminUser.username == request.username).first()
            if existing:
                return {"code": 1, "message": f"用户名 '{request.username}' 已存在", "data": None}
            new_user = AdminUser(
                username=request.username,
                password_hash=get_password_hash(request.password),
                role=request.role,
                nickname=request.nickname or request.username,
                is_active=True
            )
            session.add(new_user)
            session.commit()
            session.refresh(new_user)
            return {"code": 0, "message": "创建成功", "data": new_user.to_dict()}
        finally:
            session.close()
    except Exception as e:
        logger.error(f"创建管理员失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/admin-api/admin-users/{user_id}")
def admin_update_user(
    user_id: int,
    data: dict = Body(...),
    admin=Depends(_verify_admin_token)
):
    """更新管理员/操作员账号（仅超级管理员可访问）"""
    if admin.role != 'admin':
        return {"code": 1, "message": "仅超级管理员可访问", "data": None}
    try:
        session = SessionLocal()
        try:
            user = session.query(AdminUser).filter(AdminUser.id == user_id).first()
            if not user:
                return {"code": 1, "message": "用户不存在", "data": None}
            if 'nickname' in data:
                user.nickname = data['nickname']
            if 'role' in data and data['role'] in ('admin', 'operator'):
                user.role = data['role']
            if 'is_active' in data:
                user.is_active = bool(data['is_active'])
            if 'password' in data and data['password']:
                if len(data['password']) < 6:
                    return {"code": 1, "message": "密码至少6位", "data": None}
                user.password_hash = get_password_hash(data['password'])
            session.commit()
            session.refresh(user)
            return {"code": 0, "message": "更新成功", "data": user.to_dict()}
        finally:
            session.close()
    except Exception as e:
        logger.error(f"更新管理员失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/admin-api/admin-users/{user_id}")
def admin_delete_user(
    user_id: int,
    admin=Depends(_verify_admin_token)
):
    """删除管理员/操作员账号（仅超级管理员可访问，不能删除自己）"""
    if admin.role != 'admin':
        return {"code": 1, "message": "仅超级管理员可访问", "data": None}
    if admin.id == user_id:
        return {"code": 1, "message": "不能删除自己的账号", "data": None}
    try:
        session = SessionLocal()
        try:
            user = session.query(AdminUser).filter(AdminUser.id == user_id).first()
            if not user:
                return {"code": 1, "message": "用户不存在", "data": None}
            session.delete(user)
            session.commit()
            return {"code": 0, "message": "删除成功", "data": None}
        finally:
            session.close()
    except Exception as e:
        logger.error(f"删除管理员失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/admin-api/stats")
def admin_get_stats():
    """
    获取统计数据
    """
    try:
        stats = DatabaseManager.get_stats()
        return {
            "code": 0,
            "message": "success",
            "data": stats
        }
    except Exception as e:
        logger.error(f"获取统计数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 频道管理 API ====================

class CategoryCreate(BaseModel):
    key: str
    name: str
    icon: Optional[str] = ""
    description: Optional[str] = ""
    sort_order: int = 0


class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    icon: Optional[str] = None
    description: Optional[str] = None
    sort_order: Optional[int] = None
    enabled: Optional[bool] = None


@app.get("/admin-api/categories")
def admin_list_categories():
    """获取频道列表"""
    try:
        categories = DatabaseManager.list_categories()
        return {"code": 0, "message": "success", "data": categories}
    except Exception as e:
        logger.error(f"获取频道列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/admin-api/categories")
def admin_create_category(data: CategoryCreate):
    """创建频道"""
    try:
        result = DatabaseManager.create_category(
            key=data.key,
            name=data.name,
            icon=data.icon,
            description=data.description,
            sort_order=data.sort_order
        )
        return {"code": 0, "message": "创建成功", "data": result}
    except Exception as e:
        logger.error(f"创建频道失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/admin-api/categories/{category_id}")
def admin_update_category(category_id: int, data: CategoryUpdate):
    """更新频道"""
    try:
        update_data = {}
        for k, v in data.dict().items():
            if v is not None:
                update_data[k] = v
        result = DatabaseManager.update_category(category_id, update_data)
        if not result:
            raise HTTPException(status_code=404, detail="频道不存在")
        return {"code": 0, "message": "更新成功", "data": result}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新频道失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/admin-api/categories/{category_id}")
def admin_delete_category(category_id: int):
    """删除频道"""
    try:
        success = DatabaseManager.delete_category(category_id)
        if not success:
            raise HTTPException(status_code=404, detail="频道不存在")
        return {"code": 0, "message": "删除成功"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除频道失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 平台管理 API ====================

class PlatformCreate(BaseModel):
    key: str
    name: str
    spider: Optional[str] = None
    official_site: Optional[str] = ""
    rate_limit: float = 1.0
    timeout: int = 15
    icon: Optional[str] = ""
    sort_order: int = 0
    user_agent: Optional[str] = ""
    keywords: Optional[dict] = None
    config: Optional[dict] = None


class PlatformUpdate(BaseModel):
    name: Optional[str] = None
    spider: Optional[str] = None
    official_site: Optional[str] = None
    rate_limit: Optional[float] = None
    timeout: Optional[int] = None
    icon: Optional[str] = None
    sort_order: Optional[int] = None
    enabled: Optional[bool] = None
    user_agent: Optional[str] = None
    keywords: Optional[dict] = None
    config: Optional[dict] = None


@app.get("/admin-api/platforms-v2")
def admin_list_platforms_v2():
    """获取平台列表（新版，使用数据库）"""
    try:
        platforms = DatabaseManager.list_platforms()
        return {"code": 0, "message": "success", "data": platforms}
    except Exception as e:
        logger.error(f"获取平台列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/admin-api/platforms-v2/export")
def admin_export_platforms():
    """导出所有平台数据（包括频道、关键词、解析源）"""
    try:
        from models import AdminPlatform, AdminPlatformChannel, ParseSource
        db = DatabaseManager()

        platforms = db.list_platforms()
        export_data = {"platforms": []}

        with db.session_scope() as session:
            for platform in platforms:
                platform_data = {
                    "key": platform.get("key"),
                    "name": platform.get("name"),
                    "spider": platform.get("spider"),
                    "official_site": platform.get("official_site"),
                    "icon": platform.get("icon"),
                    "rate_limit": platform.get("rate_limit"),
                    "timeout": platform.get("timeout"),
                    "sort_order": platform.get("sort_order"),
                    "enabled": platform.get("enabled"),
                    "user_agent": platform.get("user_agent"),
                    "keywords": platform.get("keywords", {}),
                    "channels": [],
                    "parse_sources": []
                }

                # 获取频道
                channels = session.query(AdminPlatformChannel).filter(
                    AdminPlatformChannel.platform_id == platform.get("id")
                ).all()
                for ch in channels:
                    platform_data["channels"].append({
                        "category_id": ch.category_id,
                        "channel_key": ch.channel_key,
                        "channel_name": ch.channel_name,
                        "url": ch.url,
                        "output_table": ch.output_table,
                        "channel_id": ch.channel_id,
                        "sort_order": ch.sort_order,
                        "enabled": ch.enabled
                    })

                # 获取解析源
                parse_sources = session.query(ParseSource).filter(
                    ParseSource.platform_id == platform.get("id")
                ).all()
                for ps in parse_sources:
                    platform_data["parse_sources"].append({
                        "key": ps.key,
                        "name": ps.name,
                        "type": ps.type,
                        "url": ps.url,
                        "sort_order": ps.sort_order
                    })

                export_data["platforms"].append(platform_data)

        import json
        from fastapi.responses import Response
        content = json.dumps(export_data, ensure_ascii=False, indent=2)
        return Response(
            content=content,
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename=platforms_export.json"}
        )
    except Exception as e:
        logger.error(f"导出平台数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class PlatformImportData(BaseModel):
    platforms: List[dict]


@app.post("/admin-api/platforms-v2/import")
def admin_import_platforms(data: PlatformImportData):
    """导入平台数据"""
    try:
        from models import AdminPlatform, AdminPlatformChannel, ParseSource
        db = DatabaseManager()

        imported_platforms = 0
        imported_channels = 0
        imported_parse_sources = 0

        with db.session_scope() as session:
            for platform_data in data.platforms:
                # 创建或更新平台
                existing = session.query(AdminPlatform).filter(
                    AdminPlatform.key == platform_data.get("key")
                ).first()

                if existing:
                    platform = existing
                else:
                    platform = AdminPlatform(
                        key=platform_data.get("key"),
                        name=platform_data.get("name"),
                        spider=platform_data.get("spider"),
                        official_site=platform_data.get("official_site"),
                        icon=platform_data.get("icon"),
                        rate_limit=platform_data.get("rate_limit", 1.0),
                        timeout=platform_data.get("timeout", 15),
                        sort_order=platform_data.get("sort_order", 0),
                        enabled=platform_data.get("enabled", True),
                        user_agent=platform_data.get("user_agent"),
                        keywords=json.dumps(platform_data.get("keywords", {}), ensure_ascii=False)
                    )
                    session.add(platform)
                    session.flush()

                imported_platforms += 1

                # 导入频道
                for ch_data in platform_data.get("channels", []):
                    existing_ch = session.query(AdminPlatformChannel).filter(
                        AdminPlatformChannel.platform_id == platform.id,
                        AdminPlatformChannel.channel_key == ch_data.get("channel_key")
                    ).first()

                    if not existing_ch:
                        channel = AdminPlatformChannel(
                            platform_id=platform.id,
                            category_id=ch_data.get("category_id"),
                            channel_key=ch_data.get("channel_key"),
                            channel_name=ch_data.get("channel_name"),
                            url=ch_data.get("url"),
                            output_table=ch_data.get("output_table", "series"),
                            channel_id=ch_data.get("channel_id"),
                            sort_order=ch_data.get("sort_order", 0),
                            enabled=ch_data.get("enabled", True)
                        )
                        session.add(channel)
                        imported_channels += 1

                # 导入解析源
                for ps_data in platform_data.get("parse_sources", []):
                    existing_ps = session.query(ParseSource).filter(
                        ParseSource.platform_id == platform.id,
                        ParseSource.key == ps_data.get("key")
                    ).first()

                    if not existing_ps:
                        parse_source = ParseSource(
                            platform_id=platform.id,
                            key=ps_data.get("key"),
                            name=ps_data.get("name"),
                            type=ps_data.get("type", "json"),
                            url=ps_data.get("url"),
                            sort_order=ps_data.get("sort_order", 0)
                        )
                        session.add(parse_source)
                        imported_parse_sources += 1

        return {
            "code": 0,
            "message": f"导入成功：{imported_platforms} 个平台，{imported_channels} 个频道，{imported_parse_sources} 个解析源"
        }
    except Exception as e:
        logger.error(f"导入平台数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/admin-api/platforms-v2")
def admin_create_platform(data: PlatformCreate):
    """创建平台（新版）"""
    try:
        result = DatabaseManager.create_platform(
            key=data.key,
            name=data.name,
            spider=data.spider,
            official_site=data.official_site,
            rate_limit=data.rate_limit,
            timeout=data.timeout,
            icon=data.icon,
            sort_order=data.sort_order,
            user_agent=data.user_agent,
            keywords=data.keywords,
            config=data.config
        )
        return {"code": 0, "message": "创建成功", "data": result}
    except Exception as e:
        logger.error(f"创建平台失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/admin-api/platforms-v2/{platform_id}")
def admin_update_platform(platform_id: int, data: PlatformUpdate):
    """更新平台（新版）"""
    try:
        update_data = {}
        for k, v in data.dict().items():
            if v is not None:
                update_data[k] = v
        result = DatabaseManager.update_platform(platform_id, update_data)
        if not result:
            raise HTTPException(status_code=404, detail="平台不存在")
        return {"code": 0, "message": "更新成功", "data": result}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新平台失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/admin-api/platforms-v2/{platform_id}")
def admin_delete_platform(platform_id: int):
    """删除平台（新版）"""
    try:
        success = DatabaseManager.delete_platform(platform_id)
        if not success:
            raise HTTPException(status_code=404, detail="平台不存在")
        return {"code": 0, "message": "删除成功"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除平台失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/admin-api/platforms-v2/{platform_id}/channels")
def admin_list_platform_channels_by_platform(platform_id: int):
    """获取指定平台的频道列表"""
    try:
        channels = DatabaseManager.list_platform_channels(platform_id=platform_id)
        return {"code": 0, "message": "success", "data": channels}
    except Exception as e:
        logger.error(f"获取平台频道列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class PlatformChannelCreateV2(BaseModel):
    platform_id: int
    category_id: Optional[int] = None
    channel_key: str
    channel_name: str
    url: str
    output_table: str = "series"
    channel_id: Optional[str] = None
    config: Optional[dict] = None
    sort_order: int = 0
    enabled: bool = True


class PlatformChannelUpdateV2(BaseModel):
    category_id: Optional[int] = None
    channel_key: Optional[str] = None
    channel_name: Optional[str] = None
    url: Optional[str] = None
    output_table: Optional[str] = None
    channel_id: Optional[str] = None
    config: Optional[dict] = None
    sort_order: Optional[int] = None
    enabled: Optional[bool] = None


@app.post("/admin-api/platforms-v2/{platform_id}/channels")
def admin_create_platform_channel_v2(platform_id: int, data: PlatformChannelCreateV2):
    """创建平台频道（新版）"""
    try:
        result = DatabaseManager.create_platform_channel(
            platform_id=platform_id,
            category_id=data.category_id,
            channel_key=data.channel_key,
            channel_name=data.channel_name,
            url=data.url,
            output_table=data.output_table,
            channel_id=data.channel_id,
            config=data.config,
            sort_order=data.sort_order
        )
        return {"code": 0, "message": "创建成功", "data": result}
    except Exception as e:
        logger.error(f"创建平台频道失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/admin-api/platforms-v2/{platform_id}/channels/{pc_id}")
def admin_update_platform_channel_v2(platform_id: int, pc_id: int, data: PlatformChannelUpdateV2):
    """更新平台频道（新版）"""
    try:
        update_data = {}
        for k, v in data.dict().items():
            if v is not None:
                update_data[k] = v
        result = DatabaseManager.update_platform_channel(pc_id, update_data)
        if not result:
            raise HTTPException(status_code=404, detail="平台频道不存在")
        return {"code": 0, "message": "更新成功", "data": result}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新平台频道失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/admin-api/platforms-v2/{platform_id}/channels/{pc_id}")
def admin_delete_platform_channel_v2(platform_id: int, pc_id: int):
    """删除平台频道（新版）"""
    try:
        success = DatabaseManager.delete_platform_channel(pc_id)
        if not success:
            raise HTTPException(status_code=404, detail="平台频道不存在")
        return {"code": 0, "message": "删除成功"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除平台频道失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/admin-api/platforms-v2/{platform_id}/parse-sources")
def admin_list_parse_sources_by_platform(platform_id: int):
    """获取指定平台的解析源列表"""
    try:
        sources = DatabaseManager.list_parse_sources(platform_id=platform_id)
        return {"code": 0, "message": "success", "data": sources}
    except Exception as e:
        logger.error(f"获取解析源列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class ParseSourceCreateV2(BaseModel):
    platform_id: int
    name: str
    type: str = "json"
    url: str
    sort_order: int = 0
    enabled: bool = True


class ParseSourceUpdateV2(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    url: Optional[str] = None
    sort_order: Optional[int] = None
    enabled: Optional[bool] = None


@app.post("/admin-api/platforms-v2/{platform_id}/parse-sources")
def admin_create_parse_source_v2(platform_id: int, data: ParseSourceCreateV2):
    """创建解析源（新版）"""
    try:
        result = DatabaseManager.create_parse_source(
            key=f"{platform_id}_{data.name.replace(' ', '_')}",
            name=data.name,
            url=data.url,
            sort_order=data.sort_order,
            platform_id=platform_id,
            type=data.type
        )
        return {"code": 0, "message": "创建成功", "data": result}
    except Exception as e:
        logger.error(f"创建解析源失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/admin-api/platforms-v2/{platform_id}/parse-sources/{ps_id}")
def admin_update_parse_source_v2(platform_id: int, ps_id: int, data: ParseSourceUpdateV2):
    """更新解析源（新版）"""
    try:
        update_data = {}
        for k, v in data.dict().items():
            if v is not None:
                update_data[k] = v
        result = DatabaseManager.update_parse_source(ps_id, update_data)
        if not result:
            raise HTTPException(status_code=404, detail="解析源不存在")
        return {"code": 0, "message": "更新成功", "data": result}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新解析源失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/admin-api/platforms-v2/{platform_id}/parse-sources/{ps_id}")
def admin_delete_parse_source_v2(platform_id: int, ps_id: int):
    """删除解析源（新版）"""
    try:
        success = DatabaseManager.delete_parse_source(ps_id)
        if not success:
            raise HTTPException(status_code=404, detail="解析源不存在")
        return {"code": 0, "message": "删除成功"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除解析源失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 平台频道管理 API ====================

class PlatformChannelCreate(BaseModel):
    platform_id: int
    category_id: int
    channel_key: str
    url: str
    channel_name: Optional[str] = ""
    output_table: str = "series"
    channel_id: Optional[str] = None
    sort_order: int = 0


class PlatformChannelUpdate(BaseModel):
    platform_id: Optional[int] = None
    category_id: Optional[int] = None
    channel_key: Optional[str] = None
    channel_name: Optional[str] = None
    url: Optional[str] = None
    output_table: Optional[str] = None
    channel_id: Optional[str] = None
    sort_order: Optional[int] = None
    enabled: Optional[bool] = None


@app.get("/admin-api/platform-channels")
def admin_list_platform_channels(
    category_id: Optional[int] = Query(None),
    platform_id: Optional[int] = Query(None)
):
    """获取平台频道列表"""
    try:
        channels = DatabaseManager.list_platform_channels(
            category_id=category_id,
            platform_id=platform_id
        )
        return {"code": 0, "message": "success", "data": channels}
    except Exception as e:
        logger.error(f"获取平台频道列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/admin-api/channel-config-tree")
def admin_get_channel_config_tree():
    """获取完整的频道配置树（包含分类、平台、平台频道的层级结构）"""
    try:
        # 获取所有数据
        categories = DatabaseManager.list_categories()
        platforms = DatabaseManager.list_platforms()
        platform_channels = DatabaseManager.list_platform_channels()

        # 构建树结构
        category_map = {cat['id']: {**cat, 'platforms': []} for cat in categories}
        platform_map = {plat['id']: {**plat, 'channels': []} for plat in platforms}

        # 把平台频道添加到对应的平台下
        for pc in platform_channels:
            if pc['platform_id'] in platform_map:
                platform_map[pc['platform_id']]['channels'].append(pc)

        # 把平台添加到对应的分类下（只要该平台有该分类的频道）
        for pc in platform_channels:
            if pc['category_id'] in category_map:
                # 检查是否已经添加过这个平台到该分类
                added = any(p['id'] == pc['platform_id'] for p in category_map[pc['category_id']]['platforms'])
                if not added and pc['platform_id'] in platform_map:
                    # 添加平台到分类
                    category_map[pc['category_id']]['platforms'].append(platform_map[pc['platform_id']])

        result = list(category_map.values())
        return {"code": 0, "message": "success", "data": result}
    except Exception as e:
        logger.error(f"获取频道配置树失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/admin-api/platform-channels")
def admin_create_platform_channel(data: PlatformChannelCreate):
    """创建平台频道"""
    try:
        result = DatabaseManager.create_platform_channel(
            platform_id=data.platform_id,
            category_id=data.category_id,
            channel_key=data.channel_key,
            url=data.url,
            channel_name=data.channel_name,
            output_table=data.output_table,
            channel_id=data.channel_id,
            sort_order=data.sort_order
        )
        return {"code": 0, "message": "创建成功", "data": result}
    except Exception as e:
        logger.error(f"创建平台频道失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/admin-api/platform-channels/{pc_id}")
def admin_update_platform_channel(pc_id: int, data: PlatformChannelUpdate):
    """更新平台频道"""
    try:
        update_data = {}
        for k, v in data.dict().items():
            if v is not None:
                update_data[k] = v
        result = DatabaseManager.update_platform_channel(pc_id, update_data)
        if not result:
            raise HTTPException(status_code=404, detail="平台频道不存在")
        return {"code": 0, "message": "更新成功", "data": result}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新平台频道失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/admin-api/platform-channels/{pc_id}")
def admin_delete_platform_channel(pc_id: int):
    """删除平台频道"""
    try:
        success = DatabaseManager.delete_platform_channel(pc_id)
        if not success:
            raise HTTPException(status_code=404, detail="平台频道不存在")
        return {"code": 0, "message": "删除成功"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除平台频道失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 解析源管理 API ====================

class ParseSourceCreate(BaseModel):
    key: str
    name: str
    url: str
    sort_order: int = 0


class ParseSourceUpdate(BaseModel):
    name: Optional[str] = None
    url: Optional[str] = None
    sort_order: Optional[int] = None
    enabled: Optional[bool] = None


@app.get("/admin-api/parse-sources")
def admin_list_parse_sources():
    """获取解析源列表"""
    try:
        sources = DatabaseManager.list_parse_sources()
        return {"code": 0, "message": "success", "data": sources}
    except Exception as e:
        logger.error(f"获取解析源列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/admin-api/parse-sources")
def admin_create_parse_source(data: ParseSourceCreate):
    """创建解析源"""
    try:
        result = DatabaseManager.create_parse_source(
            key=data.key,
            name=data.name,
            url=data.url,
            sort_order=data.sort_order
        )
        return {"code": 0, "message": "创建成功", "data": result}
    except Exception as e:
        logger.error(f"创建解析源失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/admin-api/parse-sources/{ps_id}")
def admin_update_parse_source(ps_id: int, data: ParseSourceUpdate):
    """更新解析源"""
    try:
        update_data = {}
        for k, v in data.dict().items():
            if v is not None:
                update_data[k] = v
        result = DatabaseManager.update_parse_source(ps_id, update_data)
        if not result:
            raise HTTPException(status_code=404, detail="解析源不存在")
        return {"code": 0, "message": "更新成功", "data": result}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新解析源失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/admin-api/parse-sources/{ps_id}")
def admin_delete_parse_source(ps_id: int):
    """删除解析源"""
    try:
        success = DatabaseManager.delete_parse_source(ps_id)
        if not success:
            raise HTTPException(status_code=404, detail="解析源不存在")
        return {"code": 0, "message": "删除成功"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除解析源失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# 客户端获取解析源的 API
@app.get("/api/parse-sources")
def list_parse_sources():
    """获取启用的解析源列表（客户端使用）"""
    try:
        sources = DatabaseManager.list_parse_sources(enabled_only=True)
        return {"code": 0, "message": "success", "data": sources}
    except Exception as e:
        logger.error(f"获取解析源列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/admin-api/series")
def admin_list_series(
    platform: Optional[str] = Query(None, description="平台过滤"),
    category: Optional[str] = Query(None, description="频道过滤 (tv, movie, variety, cartoon, child)"),
    keyword: Optional[str] = Query(None, description="关键词搜索"),
    id: Optional[int] = Query(None, description="ID精确匹配"),
    page: int = Query(1, ge=1, description="页码"),
    limit: int = Query(20, ge=1, le=100, description="每页数量")
):
    """
    获取剧集列表
    """
    try:
        if category:
            result = DatabaseManager.list_series(category, platform=platform, keyword=keyword, id=id, page=page, limit=limit)
        else:
            result = DatabaseManager.list_series_all(platform=platform, keyword=keyword, page=page, limit=limit)
        return {
            "code": 0,
            "message": "success",
            "data": result
        }
    except Exception as e:
        logger.error(f"获取剧集列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/admin-api/series")
def admin_create_series(data: dict):
    """
    管理端创建新剧集
    """
    try:
        category = data.get('category_key', 'tv')
        result = DatabaseManager.admin_create_series(category, data)
        return {
            "code": 0,
            "message": "创建成功",
            "data": result
        }
    except Exception as e:
        logger.error(f"创建剧集失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/admin-api/series/{series_id}")
def admin_update_series(series_id: int, data: dict):
    """
    管理端更新剧集
    """
    try:
        category = data.get('category_key', 'tv')
        result = DatabaseManager.admin_update_series(category, series_id, data)
        if not result:
            raise HTTPException(status_code=404, detail="剧集不存在")
        return {
            "code": 0,
            "message": "更新成功",
            "data": result
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新剧集失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/admin-api/series/{series_id}")
def admin_delete_series(series_id: int, category: str = Query("tv", description="频道标识")):
    """
    删除剧集
    """
    try:
        from models import get_video_model, get_video_ep_model, get_session
        SeriesModel = get_video_model(category)
        with get_session() as session:
            series = session.query(SeriesModel).filter(SeriesModel.id == series_id).first()
            if not series:
                raise HTTPException(status_code=404, detail="剧集不存在")
            session.delete(series)
            return {"code": 0, "message": "删除成功", "data": None}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除剧集失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/admin-api/episodes")
def admin_list_episodes(
    series_id: Optional[int] = Query(None, description="剧集ID过滤"),
    category: str = Query("tv", description="频道标识"),
    keyword: Optional[str] = Query(None, description="关键词搜索（播放标题或联合标题）"),
    page: int = Query(1, ge=1, description="页码"),
    limit: int = Query(20, ge=1, le=100, description="每页数量")
):
    """
    获取分集列表
    """
    try:
        result = DatabaseManager.list_episodes(category, series_id=series_id, keyword=keyword, page=page, limit=limit)
        return {
            "code": 0,
            "message": "success",
            "data": result
        }
    except Exception as e:
        logger.error(f"获取分集列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/admin-api/episodes")
def admin_create_episode(data: dict):
    """
    管理端创建新分集
    """
    try:
        category = data.get('category_key', 'tv')
        result = DatabaseManager.admin_create_episode(category, data)
        return {
            "code": 0,
            "message": "创建成功",
            "data": result
        }
    except Exception as e:
        logger.error(f"创建分集失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/admin-api/episodes/{episode_id}")
def admin_update_episode(episode_id: int, data: dict):
    """
    管理端更新分集
    """
    try:
        category = data.get('category_key', 'tv')
        result = DatabaseManager.admin_update_episode(category, episode_id, data)
        if not result:
            raise HTTPException(status_code=404, detail="分集不存在")
        return {
            "code": 0,
            "message": "更新成功",
            "data": result
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新分集失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/admin-api/episodes/{episode_id}")
def admin_delete_episode(episode_id: int, category: str = Query("tv", description="频道标识")):
    """
    删除分集
    """
    try:
        success = DatabaseManager.delete_episode(category, episode_id)
        if not success:
            raise HTTPException(status_code=404, detail="分集不存在")
        return {"code": 0, "message": "删除成功", "data": None}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除分集失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 爬虫管理 API ====================

@app.get("/admin-api/crawl-tasks")
def admin_list_crawl_tasks(
    page: int = Query(1, ge=1, description="页码"),
    limit: int = Query(20, ge=1, le=100, description="每页数量")
):
    """
    获取爬虫任务列表
    """
    try:
        result = DatabaseManager.list_crawl_tasks(page=page, limit=limit)
        return {
            "code": 0,
            "message": "success",
            "data": result
        }
    except Exception as e:
        logger.error(f"获取爬虫任务列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/admin-api/platforms")
def admin_get_platforms():
    """
    获取所有平台配置
    """
    try:
        platforms = []
        # 添加ALL选项
        platforms.append({
            "key": "all",
            "name": "全部平台",
            "channels": []
        })

        # 从数据库获取所有平台和频道
        db_platforms = DatabaseManager.list_platforms()
        db_channels = DatabaseManager.list_platform_channels()

        # 按平台ID分组频道
        channel_map = {}
        for ch in db_channels:
            plat_key = None
            # 找到这个频道对应的平台的key
            for p in db_platforms:
                if p["id"] == ch["platform_id"]:
                    plat_key = p["key"]
                    break
            if plat_key:
                if plat_key not in channel_map:
                    channel_map[plat_key] = []
                channel_map[plat_key].append({
                    "key": ch["channel_key"],
                    "name": ch["channel_name"]
                })

        # 添加所有平台
        for p in db_platforms:
            platforms.append({
                "key": p["key"],
                "name": p["name"],
                "channels": channel_map.get(p["key"], [])
            })

        return {
            "code": 0,
            "message": "success",
            "data": platforms
        }
    except Exception as e:
        logger.error(f"获取平台列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# 简单的后台任务存储
_crawl_task_threads = {}
# 记录今天是否已经清理过日志
_last_cleanup_date = None


def run_crawl_process(platform_key, channel_keys, mode, max_items):
    """在独立进程中运行爬虫（顶层函数，避免pickle问题）"""
    try:
        import sys
        import os
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
        from core.config import Config
        from main import crawl_platform
        config = Config()

        # 如果是 all，则遍历所有平台
        if platform_key == "all":
            platforms = config.get_platforms()
            for p_key in platforms.keys():
                from core.logger import setup_logger
                logger = setup_logger('vbox.crawl')

                # 遍历指定频道（或所有频道）
                channels = channel_keys or list(config.get_channels(p_key).keys())

                for ch_key in channels:
                    logger.info(f"后台任务开始: {p_key} - {ch_key}, 模式: {mode}, max_items: {max_items}")
                    crawl_platform(p_key, ch_key, max_items=max_items)
                    logger.info(f"后台任务完成: {p_key} - {ch_key}")
        else:
            from core.logger import setup_logger
            logger = setup_logger('vbox.crawl')

            # 遍历指定频道（或所有频道）
            channels = channel_keys or list(config.get_channels(platform_key).keys())

            for ch_key in channels:
                logger.info(f"后台任务开始: {platform_key} - {ch_key}, 模式: {mode}, max_items: {max_items}")
                crawl_platform(platform_key, ch_key, max_items=max_items)
                logger.info(f"后台任务完成: {platform_key} - {ch_key}")
    except Exception as e:
        import traceback
        traceback.print_exc()


def should_cleanup_today():
    """判断今天是否已经清理过日志"""
    global _last_cleanup_date
    today = utc_plus_8().date()
    if _last_cleanup_date != today:
        _last_cleanup_date = today
        return True
    return False


@app.post("/admin-api/trigger-crawl")
def admin_trigger_crawl(
    data: dict = Body(...)
):
    """
    手动触发爬虫任务
    """
    from core.task_scheduler import get_scheduler

    # 每天第一次触发任务时清理10天前的旧日志
    if should_cleanup_today():
        from core.log_stream import cleanup_old_logs
        try:
            deleted_count = cleanup_old_logs(10)
            logger.info(f"清理了 {deleted_count} 条旧日志")
        except Exception as e:
            logger.error(f"清理旧日志失败: {e}")

    platform_key = data.get('platform')
    channel_keys = data.get('channels')  # 多频道数组
    mode = data.get('mode', 'test')
    prod_type = data.get('prod_type')
    max_items = data.get('max_items')
    sort = data.get('sort')  # 排序类型：'75'=热门, '71'/'79'=最新

    # 确定 mode 和 max_items
    if mode == 'prod' or prod_type:
        # 生产模式
        mode = 'new' if prod_type == 'incremental' else 'all'
        max_items = None
    elif mode == 'test':
        # 测试模式
        if max_items is None:
            max_items = 10
    else:
        # 默认测试模式
        mode = 'test'
        if max_items is None:
            max_items = 10

    if not platform_key:
        raise HTTPException(status_code=400, detail="请指定平台")

    # 获取调度器并提交任务
    scheduler = get_scheduler()
    task_ids = scheduler.submit_task(
        platform_key=platform_key,
        channel_keys=channel_keys,
        max_items=max_items or 10,
        task_type="manual",
        sort=sort
    )

    return {
        "code": 0,
        "message": f"已提交 {len(task_ids)} 个频道任务",
        "data": {
            "task_ids": task_ids,
            "count": len(task_ids)
        }
    }


@app.get("/admin-api/task-status")
def get_task_status(page: int = 1, limit: int = 50):
    """获取任务队列状态，支持已完成任务分页"""
    from core.task_scheduler import get_scheduler
    scheduler = get_scheduler()
    all_tasks = scheduler.get_all_tasks()

    # 对 completed 任务进行分页
    completed_list = all_tasks["completed"]
    total = len(completed_list)
    offset = (page - 1) * limit
    paginated_completed = completed_list[offset:offset + limit]

    result = {
        "running": all_tasks["running"],
        "pending": all_tasks["pending"],
        "completed": paginated_completed,
        "completed_total": total,
        "platform_running": all_tasks["platform_running"],
        "global_active": all_tasks["global_active"]
    }

    return {
        "code": 0,
        "message": "success",
        "data": result
    }


@app.post("/admin-api/stop-task/{task_id}")
def admin_stop_task(task_id: str):
    """停止指定的任务"""
    from core.task_scheduler import get_scheduler
    scheduler = get_scheduler()
    success = scheduler.stop_task(task_id)
    if success:
        return {
            "code": 0,
            "message": "任务已停止"
        }
    else:
        raise HTTPException(status_code=404, detail="任务不存在或已完成")


@app.post("/admin-api/stop-task-by-db-id/{db_task_id}")
def admin_stop_task_by_db_id(db_task_id: int):
    """通过数据库任务ID停止任务"""
    from core.task_scheduler import get_scheduler
    scheduler = get_scheduler()

    # 查找具有该数据库任务ID的运行中任务
    with scheduler.state_lock:
        for task_id, task in scheduler.tasks.items():
            if getattr(task, 'db_task_id', None) == db_task_id:
                if task.status.value == 'running':
                    success = scheduler.stop_task(task_id)
                    if success:
                        return {
                            "code": 0,
                            "message": "任务已停止"
                        }

    raise HTTPException(status_code=404, detail="任务不存在或已完成")


@app.post("/admin-api/stop-all-tasks")
def admin_stop_all_tasks():
    """停止所有运行中的任务"""
    from core.task_scheduler import get_scheduler
    scheduler = get_scheduler()
    stopped_count = scheduler.stop_all_running()

    # 同时更新数据库中的任务状态
    from core.database import DatabaseManager
    db = DatabaseManager()
    with db.session_scope() as session:
        from models import TaskCrawl
        running_tasks = session.query(TaskCrawl).filter(TaskCrawl.status == 'running').all()
        for task in running_tasks:
            task.status = 'failed'
            task.error_message = '用户手动停止'
            task.completed_at = datetime.now()
        db_stopped = len(running_tasks)

    return {
        "code": 0,
        "message": f"已停止 {stopped_count} 个调度任务，{db_stopped} 个数据库任务"
    }


@app.post("/admin-api/reset-all-tasks")
def admin_reset_all_tasks():
    """重置所有任务状态，强制终止所有运行中的任务"""
    from core.task_scheduler import get_scheduler
    scheduler = get_scheduler()

    with scheduler.state_lock:
        # 强制终止所有进程
        for task_id, proc in list(scheduler.active_processes.items()):
            if proc.is_alive():
                try:
                    proc.terminate()
                    proc.join(timeout=3)
                    if proc.is_alive():
                        proc.kill()
                        proc.join(timeout=1)
                except Exception as e:
                    logger.error(f"强制终止任务 {task_id} 失败: {e}")

        # 重置所有运行中的任务状态
        from core.task_scheduler import TaskStatus
        for task_id, task in list(scheduler.tasks.items()):
            if task.status == TaskStatus.RUNNING:
                task.status = TaskStatus.FAILED
                task.error = "手动重置状态"
                task.completed_at = datetime.now()

        # 清空运行计数
        scheduler.active_processes.clear()
        scheduler.platform_running.clear()

    # 同时更新数据库中的任务状态
    from core.database import DatabaseManager
    db = DatabaseManager()
    with db.session_scope() as session:
        from models import TaskCrawl
        running_tasks = session.query(TaskCrawl).filter(TaskCrawl.status == 'running').all()
        for task in running_tasks:
            task.status = 'failed'
            task.error_message = '手动重置状态'
            task.completed_at = datetime.now()
        db_reset = len(running_tasks)

    return {
        "code": 0,
        "message": f"所有任务状态已重置，更新了 {db_reset} 个数据库任务"
    }


# ==================== 定时任务管理 ====================

class ScheduledTaskCreate(BaseModel):
    """创建定时任务请求模型"""
    platform: str
    channel: Optional[str] = None
    channels: Optional[list] = None
    cron_expression: str  # cron 表达式，例如 "0 0 * * *" 表示每天0点执行
    description: Optional[str] = None
    sort: Optional[str] = ''  # 排序类型: ''=默认, 'hot'=热门(刷is_hot), 'new'=最新(刷is_new)


class ScheduledTaskUpdate(BaseModel):
    """更新定时任务请求模型"""
    cron_expression: Optional[str] = None
    enabled: Optional[bool] = None
    description: Optional[str] = None


def run_scheduled_crawl_process(platform: str, channel: Optional[str] = None, channels: Optional[list] = None, task_id: int = None, sort: str = ''):
    """在独立进程中执行定时爬虫任务（顶层函数，避免pickle问题）"""
    try:
        import sys
        import os
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
        from core.config import Config
        from core.logger import setup_logger
        from core.database import DatabaseManager
        logger = setup_logger('vbox.scheduled_crawl')
        from main import crawl_platform
        config = Config()

        # 更新最后运行时间
        if task_id:
            try:
                DatabaseManager.update_scheduled_task_last_run(task_id)
            except Exception as e:
                logger.warning(f"更新任务最后运行时间失败: {e}")

        # 确定要爬取的频道（防线：过滤数据库中不存在的频道）
        raw_channel_keys = channels if channels else ([channel] if channel else None)
        _sort = sort if sort else None

        if platform == "all":
            platforms = config.get_platforms()
            for p_key in platforms.keys():
                db_channels = set(config.get_channels(p_key).keys())
                ch_list = [ch for ch in (raw_channel_keys or db_channels) if ch in db_channels]
                if not ch_list:
                    logger.warning("后台定时任务: %s 无有效频道，跳过", p_key)
                    continue

                for ch_key in ch_list:
                    logger.info(f"定时任务开始: {p_key}, 频道: {ch_key}, sort={_sort}")
                    crawl_platform(p_key, ch_key, max_items=10, sort=_sort)
                    logger.info(f"定时任务完成: {p_key}, 频道: {ch_key}")
        else:
            # 获取该平台的所有频道（或指定频道）
            db_channels = set(config.get_channels(platform).keys())
            ch_list = [ch for ch in (raw_channel_keys or db_channels) if ch in db_channels]
            if not ch_list:
                logger.warning("后台定时任务: %s 无有效频道，跳过", platform)
                return

            for ch_key in ch_list:
                logger.info(f"定时任务开始: {platform}, 频道: {ch_key}, sort={_sort}")
                crawl_platform(platform, ch_key, max_items=10, sort=_sort)
                logger.info(f"定时任务完成: {platform}, 频道: {ch_key}")
    except Exception as e:
        import traceback
        traceback.print_exc()

def trigger_scheduled_crawl(platform: str, channel: Optional[str] = None, channels: Optional[list] = None, task_id: int = None, sort: str = ''):
    """触发定时爬虫任务"""
    try:
        from core.config import Config
        config = Config()

        # 防线：过滤数据库中不存在的频道（防止定时任务表残留）
        valid_channels = set(config.get_channels(platform).keys())
        if channels:
            channels = [ch for ch in channels if ch in valid_channels]
            if not channels:
                logger.warning("定时任务跳过: %s, 所有指定频道均不在数据库配置中", platform)
                return
        elif channel and channel not in valid_channels:
            logger.warning("定时任务跳过: %s-%s, 频道不在数据库配置中", platform, channel)
            return

        logger.info(f"触发定时任务: {platform}, 频道: {channel or channels}, sort={sort}, 任务ID={task_id}")
        from core.task_scheduler import get_scheduler

        # 使用调度器提交任务
        scheduler = get_scheduler()
        task_ids = scheduler.submit_task(
            platform_key=platform,
            channel_key=channel,
            channels=channels,
            max_items=10,
            task_type="scheduled",
            scheduled_task_id=task_id,
            sort=sort if sort else None
        )

        logger.info(f"定时任务已提交: {len(task_ids)} 个频道任务")

    except Exception as e:
        logger.error(f"启动定时任务失败: {e}", exc_info=True)


def _load_scheduled_tasks_from_db():
    """从数据库加载定时任务到调度器"""
    from core.database import DatabaseManager
    try:
        tasks = DatabaseManager.list_scheduled_tasks()
        for task in tasks:
            if task.get('enabled', True):
                job_id = f"task_{task['id']}"
                # 添加到调度器
                scheduler.add_job(
                    trigger_scheduled_crawl,
                    'cron',
                    args=[task['platform'], task['channel'], task.get('channels'), task['id'], task.get('sort', '')],
                    id=job_id,
                    name=f"{task['platform']} 定时任务",
                    **_parse_cron_expression(task['cron_expression'])
                )
        logger.info(f"已从数据库加载 {len(tasks)} 个定时任务")
    except Exception as e:
        logger.error(f"加载定时任务失败: {e}", exc_info=True)


@app.post("/admin-api/scheduled-tasks")
def create_scheduled_task(data: ScheduledTaskCreate):
    """创建定时任务"""
    try:
        # 验证平台是否存在
        from core.config import Config
        config = Config()
        if data.platform != "all" and not config.get_platform(data.platform):
            raise HTTPException(status_code=400, detail="平台不存在")

        # 先存入数据库
        from core.database import DatabaseManager
        task = DatabaseManager.create_scheduled_task(
            platform=data.platform,
            channel=data.channel,
            channels=data.channels,
            cron_expression=data.cron_expression,
            description=data.description,
            sort=data.sort
        )

        # 添加到调度器
        job_id = f"task_{task['id']}"
        job = scheduler.add_job(
            trigger_scheduled_crawl,
            'cron',
            args=[data.platform, data.channel, data.channels, task['id'], data.sort],
            id=job_id,
            name=f"{data.platform} 定时任务",
            **_parse_cron_expression(data.cron_expression)
        )

        # 更新任务信息，添加 next_run_time
        task['next_run_time'] = job.next_run_time.isoformat() if job.next_run_time else None

        logger.info(f"创建定时任务: {task}")
        return {
            "code": 0,
            "message": "success",
            "data": task
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建定时任务失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/admin-api/scheduled-tasks")
def list_scheduled_tasks():
    """获取定时任务列表"""
    try:
        from core.database import DatabaseManager
        tasks = DatabaseManager.list_scheduled_tasks()

        # 添加 next_run_time
        result = []
        for task in tasks:
            job_id = f"task_{task['id']}"
            job = scheduler.get_job(job_id)
            task['next_run_time'] = job.next_run_time.isoformat() if job and job.next_run_time else None
            result.append(task)

        return {
            "code": 0,
            "message": "success",
            "data": result
        }
    except Exception as e:
        logger.error(f"获取定时任务列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/admin-api/scheduled-tasks/{task_id}")
def update_scheduled_task(task_id: int, data: ScheduledTaskUpdate):
    """更新定时任务"""
    try:
        from core.database import DatabaseManager

        update_data = {}
        if data.cron_expression is not None:
            update_data['cron_expression'] = data.cron_expression
        if data.enabled is not None:
            update_data['enabled'] = data.enabled
        if data.description is not None:
            update_data['description'] = data.description

        # 更新数据库
        task = DatabaseManager.update_scheduled_task(task_id, update_data)
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")

        job_id = f"task_{task_id}"

        # 更新调度器中的任务
        if data.enabled is not None:
            if not data.enabled:
                # 禁用任务：移除
                if scheduler.get_job(job_id):
                    scheduler.remove_job(job_id)
            else:
                # 启用任务：添加或更新
                if scheduler.get_job(job_id):
                    scheduler.remove_job(job_id)
                scheduler.add_job(
                    trigger_scheduled_crawl,
                    'cron',
                    args=[task['platform'], task['channel'], task['id']],
                    id=job_id,
                    name=f"{task['platform']} 定时任务",
                    **_parse_cron_expression(task['cron_expression'])
                )
        elif data.cron_expression is not None:
            # 更新表达式
            if scheduler.get_job(job_id):
                scheduler.remove_job(job_id)
            scheduler.add_job(
                trigger_scheduled_crawl,
                'cron',
                args=[task['platform'], task['channel'], task['id']],
                id=job_id,
                name=f"{task['platform']} 定时任务",
                **_parse_cron_expression(data.cron_expression)
            )

        # 添加 next_run_time
        job = scheduler.get_job(job_id)
        task['next_run_time'] = job.next_run_time.isoformat() if job and job.next_run_time else None

        logger.info(f"更新定时任务: {task}")
        return {
            "code": 0,
            "message": "success",
            "data": task
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新定时任务失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/admin-api/crawl-tasks/{task_id}")
def delete_crawl_task(task_id: int):
    """删除单个爬取任务"""
    try:
        from core.database import DatabaseManager

        result = DatabaseManager.delete_crawl_task(task_id)

        if not result:
            raise HTTPException(status_code=400, detail="任务不存在或正在运行中，无法删除")

        logger.info(f"删除爬取任务: {task_id}")
        return {
            "code": 0,
            "message": "success"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除爬取任务失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


class BatchDeleteRequest(BaseModel):
    """批量删除请求"""
    task_ids: List[int]


@app.post("/admin-api/crawl-tasks/batch-delete")
def batch_delete_crawl_tasks(request: BatchDeleteRequest):
    """批量删除爬取任务"""
    try:
        from core.database import DatabaseManager
        db = DatabaseManager()
        result = db.batch_delete_crawl_tasks(request.task_ids)

        logger.info(f"批量删除爬取任务: 总共{result}")
        return {
            "code": 0,
            "message": "success",
            "data": result
        }
    except Exception as e:
        logger.error(f"批量删除爬取任务失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/admin-api/scheduled-tasks/{task_id}")
def delete_scheduled_task(task_id: int):
    """删除定时任务"""
    try:
        from core.database import DatabaseManager

        # 先移除调度器中的任务
        job_id = f"task_{task_id}"
        if scheduler.get_job(job_id):
            scheduler.remove_job(job_id)

        # 删除数据库中的记录
        DatabaseManager.delete_scheduled_task(task_id)

        logger.info(f"删除定时任务: {task_id}")
        return {
            "code": 0,
            "message": "success"
        }
    except Exception as e:
        logger.error(f"删除定时任务失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 平台和频道管理 API ====================

class PlatformCreate(BaseModel):
    """创建平台请求"""
    key: str
    name: str
    official_site: Optional[str] = ""
    spider: Optional[str] = ""
    rate_limit: Optional[float] = 1.0
    timeout: Optional[int] = 15


class PlatformUpdate(BaseModel):
    """更新平台请求"""
    name: Optional[str] = None
    official_site: Optional[str] = None
    spider: Optional[str] = None
    rate_limit: Optional[float] = None
    timeout: Optional[int] = None


class ChannelCreate(BaseModel):
    """创建频道请求"""
    platform_key: str
    key: str
    name: str
    url: Optional[str] = ""
    output_table: Optional[str] = "series"
    channel_id: Optional[str] = None


class ChannelUpdate(BaseModel):
    """更新频道请求"""
    name: Optional[str] = None
    url: Optional[str] = None
    output_table: Optional[str] = None
    channel_id: Optional[str] = None


class KeywordConfig(BaseModel):
    """关键词配置"""
    positive_keywords: List[str] = []
    trailer_keywords: List[str] = []
    bts_keywords: List[str] = []


@app.get("/admin-api/platforms")
def list_platforms():
    """获取所有平台和频道列表"""
    try:
        config = Config()
        platforms_data = config.get_platforms()

        result = []
        for key, data in platforms_data.items():
            channels = []
            if "channels" in data:
                for ch_key, ch_data in data["channels"].items():
                    channels.append({
                        "key": ch_key,
                        "name": ch_data.get("name", ""),
                        "url": ch_data.get("url", ""),
                        "output_table": ch_data.get("output_table", "series"),
                        "channel_id": ch_data.get("channel_id", None)
                    })

            result.append({
                "key": key,
                "name": data.get("name", ""),
                "official_site": data.get("official_site", ""),
                "spider": data.get("spider", ""),
                "rate_limit": data.get("rate_limit", 1.0),
                "timeout": data.get("timeout", 15),
                "channels": channels,
                "positive_keywords": data.get("positive_keywords", []),
                "trailer_keywords": data.get("trailer_keywords", []),
                "bts_keywords": data.get("bts_keywords", [])
            })

        return {
            "code": 0,
            "message": "success",
            "data": result
        }
    except Exception as e:
        logger.error(f"获取平台列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/admin-api/keyword-template")
def get_keyword_template():
    """获取关键词模板"""
    try:
        config = Config()
        return {
            "code": 0,
            "message": "success",
            "data": config.get_keyword_template()
        }
    except Exception as e:
        logger.error(f"获取关键词模板失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/admin-api/keyword-template")
def update_keyword_template(data: KeywordConfig):
    """更新关键词模板"""
    try:
        config = Config()
        config.update_keyword_template({
            "positive_keywords": data.positive_keywords,
            "trailer_keywords": data.trailer_keywords,
            "bts_keywords": data.bts_keywords
        })
        logger.info("更新关键词模板")
        return {
            "code": 0,
            "message": "success"
        }
    except Exception as e:
        logger.error(f"更新关键词模板失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/admin-api/platforms/{platform_key}/keywords")
def get_platform_keywords(platform_key: str):
    """获取平台关键词配置"""
    try:
        config = Config()
        keywords = config.get_platform_keywords(platform_key)
        return {
            "code": 0,
            "message": "success",
            "data": keywords
        }
    except Exception as e:
        logger.error(f"获取平台关键词配置失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/admin-api/platforms/{platform_key}/keywords")
def update_platform_keywords(platform_key: str, data: KeywordConfig):
    """更新平台关键词配置"""
    try:
        config = Config()
        success = config.update_platform_keywords(platform_key, {
            "positive_keywords": data.positive_keywords,
            "trailer_keywords": data.trailer_keywords,
            "bts_keywords": data.bts_keywords
        })
        if not success:
            raise HTTPException(status_code=404, detail="平台不存在")
        logger.info(f"更新平台关键词配置: {platform_key}")
        return {
            "code": 0,
            "message": "success"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新平台关键词配置失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/admin-api/platforms")
def create_platform(data: PlatformCreate):
    """创建新平台"""
    try:
        config = Config()

        # 检查平台是否已存在
        if data.key in config.get_platforms():
            raise HTTPException(status_code=400, detail="平台已存在")

        platform_data = {
            "name": data.name,
            "official_site": data.official_site,
            "spider": data.spider,
            "rate_limit": data.rate_limit,
            "timeout": data.timeout,
            "channels": {}
        }

        config.create_platform(data.key, platform_data)
        logger.info(f"创建平台: {data.key}")
        return {
            "code": 0,
            "message": "创建成功"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建平台失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/admin-api/platforms/{platform_key}")
def update_platform(platform_key: str, data: PlatformUpdate):
    """更新平台"""
    try:
        config = Config()

        # 检查平台是否存在
        if platform_key not in config.get_platforms():
            raise HTTPException(status_code=404, detail="平台不存在")

        # 构建更新数据
        update_data = {}
        if data.name is not None:
            update_data["name"] = data.name
        if data.official_site is not None:
            update_data["official_site"] = data.official_site
        if data.spider is not None:
            update_data["spider"] = data.spider
        if data.rate_limit is not None:
            update_data["rate_limit"] = data.rate_limit
        if data.timeout is not None:
            update_data["timeout"] = data.timeout

        # 获取现有平台数据并更新
        existing_platform = config.get_platform(platform_key)
        updated_platform = {**existing_platform, **update_data}

        config.update_platform(platform_key, updated_platform)
        logger.info(f"更新平台: {platform_key}")
        return {
            "code": 0,
            "message": "更新成功"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新平台失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/admin-api/platforms/{platform_key}")
def delete_platform(platform_key: str):
    """删除平台"""
    try:
        config = Config()

        if platform_key not in config.get_platforms():
            raise HTTPException(status_code=404, detail="平台不存在")

        config.delete_platform(platform_key)
        logger.info(f"删除平台: {platform_key}")
        return {
            "code": 0,
            "message": "删除成功"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除平台失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/admin-api/platforms/{platform_key}/channels")
def create_channel(platform_key: str, data: ChannelCreate):
    """为平台创建新频道"""
    try:
        config = Config()

        # 检查平台是否存在
        if platform_key not in config.get_platforms():
            raise HTTPException(status_code=404, detail="平台不存在")

        # 检查频道是否已存在
        existing_channels = config.get_channels(platform_key)
        if data.key in existing_channels:
            raise HTTPException(status_code=400, detail="频道已存在")

        channel_data = {
            "name": data.name,
            "url": data.url,
            "output_table": data.output_table,
        }
        if data.channel_id:
            channel_data["channel_id"] = data.channel_id

        config.create_channel(platform_key, data.key, channel_data)
        logger.info(f"创建频道: {platform_key}.{data.key}")
        return {
            "code": 0,
            "message": "创建成功"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建频道失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/admin-api/platforms/{platform_key}/channels/{channel_key}")
def update_channel(platform_key: str, channel_key: str, data: ChannelUpdate):
    """更新频道"""
    try:
        config = Config()

        # 检查平台和频道是否存在
        if platform_key not in config.get_platforms():
            raise HTTPException(status_code=404, detail="平台不存在")

        existing_channels = config.get_channels(platform_key)
        if channel_key not in existing_channels:
            raise HTTPException(status_code=404, detail="频道不存在")

        # 构建更新数据
        update_data = {}
        if data.name is not None:
            update_data["name"] = data.name
        if data.url is not None:
            update_data["url"] = data.url
        if data.output_table is not None:
            update_data["output_table"] = data.output_table
        if data.channel_id is not None:
            update_data["channel_id"] = data.channel_id

        # 获取现有频道数据并更新
        existing_channel = config.get_channel(platform_key, channel_key)
        updated_channel = {**existing_channel, **update_data}

        config.update_channel(platform_key, channel_key, updated_channel)
        logger.info(f"更新频道: {platform_key}.{channel_key}")
        return {
            "code": 0,
            "message": "更新成功"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新频道失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/admin-api/platforms/{platform_key}/channels/{channel_key}")
def delete_channel(platform_key: str, channel_key: str):
    """删除频道"""
    try:
        config = Config()

        if platform_key not in config.get_platforms():
            raise HTTPException(status_code=404, detail="平台不存在")

        existing_channels = config.get_channels(platform_key)
        if channel_key not in existing_channels:
            raise HTTPException(status_code=404, detail="频道不存在")

        config.delete_channel(platform_key, channel_key)
        logger.info(f"删除频道: {platform_key}.{channel_key}")
        return {
            "code": 0,
            "message": "删除成功"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除频道失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


def _parse_cron_expression(expr: str):
    """解析 cron 表达式为 APScheduler 参数"""
    # 标准 cron 表达式格式: 分 时 日 月 周
    parts = expr.strip().split()
    if len(parts) != 5:
        raise ValueError("无效的 cron 表达式，格式应为: 分 时 日 月 周")

    return {
        'minute': parts[0],
        'hour': parts[1],
        'day': parts[2],
        'month': parts[3],
        'day_of_week': parts[4]
    }


@app.put("/admin-api/users/{user_id}/status")
def admin_update_user_status(user_id: int, status: str = Query(..., description="状态: active/banned")):
    """
    更新用户状态
    """
    try:
        from models import User, get_session, format_datetime
        with get_session() as session:
            user = session.query(User).filter(User.id == user_id).first()
            if not user:
                raise HTTPException(status_code=404, detail="用户不存在")
            user.status = status
            user.updated_at = utc_plus_8()
            return {"code": 0, "message": "更新成功", "data": user.to_dict(session)}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新用户状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 用户相关 API ====================

import random
import string
from datetime import timedelta
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# 导入认证模块（有 fallback 机制）
try:
    from core.auth import (
        DEV_MODE,
        create_access_token,
        create_refresh_token,
        get_password_hash,
        verify_password,
        verify_access_token,
        refresh_tokens
    )
    USE_FALLBACK_AUTH = False
except ImportError:
    # 如果 jose 没有安装，使用临时 fallback 模块
    from core.auth_fallback import (
        DEV_MODE,
        create_access_token,
        create_refresh_token,
        get_password_hash,
        verify_password,
        verify_access_token,
        refresh_tokens
    )
    USE_FALLBACK_AUTH = True

# 导入安全模块（有 fallback 机制）
try:
    from core.security import (
        record_login_attempt,
        is_login_locked,
        get_remaining_attempts
    )
    USE_FALLBACK_SECURITY = False
except Exception:
    # 如果 security 模块有问题，创建简单的替代函数
    USE_FALLBACK_SECURITY = True

    def record_login_attempt(*args, **kwargs):
        pass

    def is_login_locked(*args, **kwargs):
        return (False, 0)

    def get_remaining_attempts(*args, **kwargs):
        return 5

# 导入用户操作日志模块（有 fallback 机制）
try:
    from core.logging_utils import log_user_action
    USE_LOGGING_UTILS = True
except Exception:
    # 如果日志模块有问题，创建一个空函数
    USE_LOGGING_UTILS = False

    def log_user_action(*args, **kwargs):
        return None


class SmsSendRequest(BaseModel):
    phone: str
    code_type: str = "login"


class SmsLoginRequest(BaseModel):
    phone: str
    code: str


class PasswordLoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    phone: str
    code: str
    username: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None
    invite_code: Optional[str] = None  # 邀请码（可选）


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class ResetPasswordRequest(BaseModel):
    phone: str
    code: str
    new_password: str

class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


class UpdateProfileRequest(BaseModel):
    username: Optional[str] = None
    nickname: Optional[str] = None
    email: Optional[str] = None
    avatar: Optional[str] = None


# Token 认证依赖
security = HTTPBearer(auto_error=False)


def generate_sms_code(length: int = 6) -> str:
    """生成随机验证码"""
    return ''.join(random.choices(string.digits, k=length))


def generate_invite_code(length: int = 6) -> str:
    """生成随机邀请码（6位纯数字）"""
    chars = string.digits
    return ''.join(random.choices(chars, k=length))


def add_inviter_vip_reward(session, user_id: int, reward_points: int = 20):
    """
    给邀请人添加VIP奖励积分
    当被邀请用户成为VIP时调用

    Args:
        session: 数据库会话
        user_id: 被邀请用户的ID
        reward_points: 奖励积分数，默认20
    """
    from models import User

    user = session.query(User).filter(User.id == user_id).first()
    if not user or not user.invited_by:
        return

    inviter = session.query(User).filter(User.id == user.invited_by).first()
    if inviter:
        inviter.points = (inviter.points or 0) + reward_points
        session.flush()
        logger.info(f"邀请奖励：用户 {inviter.username} 因下级用户 {user.username} 成为VIP，获得 {reward_points} 积分")


def verify_sms_code(phone: str, code: str, code_type: str) -> bool:
    """
    验证短信验证码

    Args:
        phone: 手机号
        code: 验证码
        code_type: 验证码类型

    Returns:
        是否验证通过
    """
    from models import UserSmsCode, get_session

    if DEV_MODE:
        return True

    with get_session() as session:
        sms = session.query(UserSmsCode).filter(
            UserSmsCode.phone == phone,
            UserSmsCode.code == code,
            UserSmsCode.code_type == code_type,
            UserSmsCode.used == False,
            UserSmsCode.expire_at >= utc_plus_8()
        ).first()

        if sms:
            sms.used = True
            return True
        return False


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    获取当前登录用户

    Returns:
        用户信息字典，如果未登录返回 None
    """
    from models import User, get_session, format_datetime

    if not credentials:
        return None

    token = credentials.credentials
    user_id = verify_access_token(token)

    if not user_id:
        return None

    with get_session() as session:
        user = session.query(User).filter(User.id == user_id).first()
        if user:
            return {
                'id': user.id,
                'username': user.username,
                'phone': user.phone,
                'email': user.email,
                'nickname': user.nickname,
                'avatar': user.avatar,
                'is_vip': user.is_vip,
                'vip_expire_at': format_datetime(user.vip_expire_at),
                'invite_code': user.invite_code,
                'invited_by': user.invited_by,
                'points': user.points or 0
            }
        return None


@app.post("/api/sms/send")
def send_sms_code(request: SmsSendRequest):
    """
    发送短信验证码
    开发环境：验证码直接返回在响应中
    生产环境：应调用短信服务商API
    """
    from models import UserSmsCode, get_session

    phone = request.phone.strip()
    code_type = request.code_type

    if not phone or len(phone) != 11 or not phone.startswith('1'):
        return {"code": 1, "message": "手机号格式不正确", "data": None}

    code = generate_sms_code()

    with get_session() as session:
        session.query(UserSmsCode).filter(
            UserSmsCode.phone == phone,
            UserSmsCode.code_type == code_type
        ).delete()

        expire_at = utc_plus_8() + timedelta(minutes=10)
        sms = UserSmsCode(
            phone=phone,
            code=code,
            code_type=code_type,
            expire_at=expire_at
        )
        session.add(sms)

    logger.info(f"发送验证码: 手机号={phone}, 验证码={code}, 类型={code_type}")

    return {
        "code": 0,
        "message": "验证码已发送",
        "data": {
            "expire_seconds": 600,
            "tip": "【开发测试版】验证码直接在响应中返回，请查看 data.code 字段" if DEV_MODE else None,
            "code": code if DEV_MODE else None
        }
    }


@app.post("/api/auth/sms_login")
def sms_login(request: SmsLoginRequest, req: Request = None):
    """短信验证码登录"""
    from models import User, get_session, format_datetime

    phone = request.phone.strip()
    code = request.code.strip()

    # 获取客户端信息
    ip_address = None
    user_agent = None
    if req:
        ip_address = req.client.host if req.client else None
        user_agent = req.headers.get("user-agent")

    if not phone:
        log_user_action(None, "login", {"phone": phone[:7] + "****" if phone else None},
                       ip_address, user_agent, "failed")
        return {"code": 1, "message": "手机号不能为空", "data": None}

    # 检查是否被锁定
    locked, remaining = is_login_locked(phone)
    if locked:
        log_user_action(None, "login", {"phone": phone[:7] + "****", "reason": "locked"},
                       ip_address, user_agent, "failed")
        return {"code": 1, "message": f"登录尝试次数过多，请等待 {remaining // 60} 分钟后再试", "data": None}

    # 验证验证码
    if not verify_sms_code(phone, code, "login"):
        record_login_attempt(phone, success=False)
        remaining_attempts = get_remaining_attempts(phone)
        log_user_action(None, "login", {"phone": phone[:7] + "****", "reason": "invalid_code"},
                       ip_address, user_agent, "failed")
        return {"code": 1, "message": f"验证码无效或已过期，剩余尝试次数 {remaining_attempts}", "data": None}

    user_id = None
    user_username = None
    user_email = None
    user_nickname = None
    user_avatar = None
    user_status = None
    user_is_vip = False
    user_vip_expire_at = None
    user_invite_code = None
    user_invited_by = None
    user_points = 0
    is_new_user = False

    with get_session() as session:
        user = session.query(User).filter(User.phone == phone).first()

        if not user:
            user_username = f"user{phone[-4:]}"
            user = User(
                username=user_username,
                phone=phone,
                nickname=user_username,
                points=10  # 新用户注册送10积分
            )
            session.add(user)
            session.flush()
            is_new_user = True

        # 检查用户状态
        if user.status == "banned":
            log_user_action(user.id, "login", {"phone": phone[:7] + "****", "reason": "banned"},
                           ip_address, user_agent, "failed")
            return {"code": 1, "message": "账号已被禁用", "data": None}

        # 提取用户信息（在session内，避免to_dict()嵌套session）
        user_id = user.id
        user_username = user.username
        user_email = user.email
        user_nickname = user.nickname
        user_avatar = user.avatar
        user_status = user.status
        user_is_vip = user.is_vip or False
        user_vip_expire_at = format_datetime(user.vip_expire_at)
        user_invite_code = user.invite_code
        user_invited_by = user.invited_by
        user_points = user.points or 0

        # 记录成功登录
        record_login_attempt(phone, success=True)

        # 记录用户操作日志
        log_user_action(user_id, "login", {
            "phone": phone[:7] + "****",
            "login_method": "sms",
            "is_new_user": is_new_user
        }, ip_address, user_agent, "success")

    # --- 会话已关闭，生成 token 和返回数据 ---
    access_token = create_access_token(data={"sub": user_id})
    refresh_token = create_refresh_token(data={"sub": user_id})

    return {
        "code": 0,
        "message": "登录成功",
        "data": {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "user": {
                "id": user_id,
                "username": user_username,
                "phone": phone,
                "email": user_email,
                "nickname": user_nickname,
                "avatar": user_avatar,
                "status": user_status,
                "is_vip": user_is_vip,
                "vip_status": "vip" if user_is_vip else "normal",
                "vip_expire_at": user_vip_expire_at,
                "vip_expire_time": user_vip_expire_at,
                "vip_plans": [],
                "invite_code": user_invite_code,
                "invited_by": user_invited_by,
                "points": user_points,
            }
        }
    }


@app.post("/api/auth/password_login")
def password_login(request: PasswordLoginRequest, req: Request = None):
    """密码登录"""
    from models import User, get_session, format_datetime

    username = request.username.strip()
    password = request.password.strip()

    # 获取客户端信息
    ip_address = None
    user_agent = None
    if req:
        ip_address = req.client.host if req.client else None
        user_agent = req.headers.get("user-agent")

    if not username or not password:
        log_user_action(None, "login", {"username": username},
                       ip_address, user_agent, "failed")
        return {"code": 1, "message": "请输入用户名和密码", "data": None}

    # 查找用户（支持手机号或用户名登录）
    phone = None
    if len(username) == 11 and username.startswith('1'):
        phone = username

    # 检查是否被锁定
    locked, remaining = is_login_locked(phone or username)
    if locked:
        log_user_action(None, "login", {"username": username, "reason": "locked"},
                       ip_address, user_agent, "failed")
        return {"code": 1, "message": f"登录尝试次数过多，请等待 {remaining // 60} 分钟后再试", "data": None}

    user_id = None
    user_username = None
    user_phone = None
    user_email = None
    user_nickname = None
    user_avatar = None
    user_status = None
    user_is_vip = False
    user_vip_expire_at = None
    user_invite_code = None
    user_invited_by = None
    user_points = 0

    with get_session() as session:
        # 查找用户
        if phone:
            user = session.query(User).filter(User.phone == phone).first()
        else:
            user = session.query(User).filter(User.username == username).first()

        if not user:
            record_login_attempt(phone or username, success=False)
            remaining_attempts = get_remaining_attempts(phone or username)
            log_user_action(None, "login", {"username": username, "reason": "user_not_found"},
                           ip_address, user_agent, "failed")
            return {"code": 1, "message": f"用户名或密码错误，剩余尝试次数 {remaining_attempts}", "data": None}

        # 检查密码是否设置了密码
        if not user.password_hash:
            record_login_attempt(phone or username, success=False)
            remaining_attempts = get_remaining_attempts(phone or username)
            log_user_action(user.id, "login", {"username": username, "reason": "password_not_set"},
                           ip_address, user_agent, "failed")
            return {"code": 1, "message": "该账号未设置密码，请使用验证码登录", "data": None}

        # 验证密码
        if not verify_password(password, user.password_hash):
            record_login_attempt(phone or username, success=False)
            remaining_attempts = get_remaining_attempts(phone or username)
            log_user_action(user.id, "login", {"username": username, "reason": "wrong_password"},
                           ip_address, user_agent, "failed")
            return {"code": 1, "message": f"用户名或密码错误，剩余尝试次数 {remaining_attempts}", "data": None}

        # 检查用户状态
        if user.status == "banned":
            log_user_action(user.id, "login", {"username": username, "reason": "banned"},
                           ip_address, user_agent, "failed")
            return {"code": 1, "message": "账号已被禁用", "data": None}

        # 提取用户信息（不调用 to_dict()，避免嵌套 session）
        user_id = user.id
        user_username = user.username
        user_phone = user.phone
        user_email = user.email
        user_nickname = user.nickname
        user_avatar = user.avatar
        user_status = user.status
        user_is_vip = user.is_vip or False
        user_vip_expire_at = format_datetime(user.vip_expire_at)
        user_invite_code = user.invite_code
        user_invited_by = user.invited_by
        user_points = user.points or 0

        # 记录成功登录
        record_login_attempt(phone or username, success=True)

        # 记录用户操作日志
        log_user_action(user_id, "login", {
            "username": username,
            "login_method": "password"
        }, ip_address, user_agent, "success")

    # --- 会话已关闭，生成 token 和返回数据 ---
    access_token = create_access_token(data={"sub": user_id})
    refresh_token = create_refresh_token(data={"sub": user_id})

    return {
        "code": 0,
        "message": "登录成功",
        "data": {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "user": {
                "id": user_id,
                "username": user_username,
                "phone": user_phone,
                "email": user_email,
                "nickname": user_nickname,
                "avatar": user_avatar,
                "status": user_status,
                "is_vip": user_is_vip,
                "vip_status": "vip" if user_is_vip else "normal",
                "vip_expire_at": user_vip_expire_at,
                "vip_expire_time": user_vip_expire_at,
                "vip_plans": [],
                "invite_code": user_invite_code,
                "invited_by": user_invited_by,
                "points": user_points,
            }
        }
    }


@app.post("/api/auth/register")
def register(request: RegisterRequest, req: Request = None):
    """用户注册"""
    from models import User, get_session, format_datetime

    phone = request.phone.strip()
    code = request.code.strip()
    username = request.username or f"user{phone[-4:]}"
    email = request.email.strip() if request.email else None
    password = request.password.strip() if request.password else None
    invite_code = request.invite_code.strip().upper() if request.invite_code else None

    # 获取客户端信息
    ip_address = None
    user_agent = None
    if req:
        ip_address = req.client.host if req.client else None
        user_agent = req.headers.get("user-agent")

    if not phone or len(phone) != 11:
        log_user_action(None, "register", {"phone": phone[:7] + "****" if phone else None},
                       ip_address, user_agent, "failed")
        return {"code": 1, "message": "手机号格式不正确", "data": None}

    # 验证验证码
    if not verify_sms_code(phone, code, "register"):
        log_user_action(None, "register", {"phone": phone[:7] + "****", "reason": "invalid_code"},
                       ip_address, user_agent, "failed")
        return {"code": 1, "message": "验证码无效或已过期", "data": None}

    user_id = None
    new_invite_code = None
    inviter_id = None  # 在 session 外保存邀请人ID
    with get_session() as session:
        existing = session.query(User).filter(
            (User.phone == phone) | (User.username == username)
        ).first()

        if existing:
            if existing.phone == phone:
                log_user_action(None, "register", {"phone": phone[:7] + "****", "reason": "phone_exists"},
                               ip_address, user_agent, "failed")
                return {"code": 1, "message": "该手机号已注册", "data": None}
            else:
                log_user_action(None, "register", {"username": username, "reason": "username_exists"},
                               ip_address, user_agent, "failed")
                return {"code": 1, "message": "用户名已被占用", "data": None}

        # 检查邮箱是否已被使用
        if email:
            email_exists = session.query(User).filter(User.email == email).first()
            if email_exists:
                log_user_action(None, "register", {"email": email, "reason": "email_exists"},
                               ip_address, user_agent, "failed")
                return {"code": 1, "message": "该邮箱已被注册", "data": None}

        # 验证邀请码
        if invite_code:
            inviter = session.query(User).filter(User.invite_code == invite_code).first()
            if not inviter:
                return {"code": 1, "message": "邀请码无效", "data": None}
            inviter_id = inviter.id  # 保存邀请人ID

        # 生成唯一邀请码（一次性加载所有已用邀请码到内存，避免循环查询）
        used_codes = set(row[0] for row in session.query(User.invite_code).filter(User.invite_code != None).all())
        new_invite_code = generate_invite_code()
        while new_invite_code in used_codes:
            new_invite_code = generate_invite_code()

        # 密码哈希（在事务内处理，避免嵌套会话）
        password_hash = get_password_hash(password) if password else None

        # 创建用户
        user = User(
            username=username,
            phone=phone,
            email=email,
            nickname=username,
            invite_code=new_invite_code,
            points=10,  # 新用户注册送10积分
            invited_by=inviter_id,
            password_hash=password_hash
        )
        session.add(user)
        session.flush()
        user_id = user.id

        # 邀请奖励：给邀请人增加积分
        if inviter_id:
            inviter = session.query(User).filter(User.id == inviter_id).first()
            if inviter:
                inviter.points = (inviter.points or 0) + 10
                session.flush()

    # --- 会话已关闭/提交，以下操作不嵌套在事务中 ---

    # 生成 JWT tokens
    access_token = create_access_token(data={"sub": user_id})
    refresh_token = create_refresh_token(data={"sub": user_id})

    # 记录注册成功日志
    log_user_action(user_id, "register", {
        "phone": phone[:7] + "****",
        "username": username,
        "has_email": bool(email),
        "has_password": bool(password),
        "invite_code": new_invite_code,
        "invited_by": inviter_id
    }, ip_address, user_agent, "success")

    # 构造返回数据（不调用 to_dict()，避免嵌套会话）
    return {
        "code": 0,
        "message": "注册成功",
        "data": {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "user": {
                "id": user_id,
                "username": username,
                "phone": phone,
                "email": email,
                "nickname": username,
                "avatar": None,
                "status": "active",
                "is_vip": False,
                "vip_status": "normal",
                "vip_expire_at": None,
                "vip_expire_time": None,
                "vip_plans": [],
                "invite_code": new_invite_code,
                "invited_by": inviter_id,
                "points": 10,  # 新用户注册送10积分
                "created_at": None,
                "updated_at": None,
            }
        }
    }


@app.post("/api/auth/refresh")
def refresh_token_endpoint(request: RefreshTokenRequest):
    """刷新访问令牌"""
    tokens = refresh_tokens(request.refresh_token)
    if not tokens:
        return {"code": 1, "message": "刷新令牌无效或已过期", "data": None}

    return {
        "code": 0,
        "message": "刷新成功",
        "data": tokens
    }


@app.post("/api/auth/logout")
def logout(req: Request = None, current_user = Depends(get_current_user)):
    """用户登出"""
    # 获取客户端信息
    ip_address = None
    user_agent = None
    if req:
        ip_address = req.client.host if req.client else None
        user_agent = req.headers.get("user-agent")

    # 记录登出日志
    if current_user:
        log_user_action(current_user['id'], "logout", {}, ip_address, user_agent, "success")

    # 客户端清除token即可，服务端无需特殊处理
    return {
        "code": 0,
        "message": "登出成功",
        "data": None
    }


@app.get("/api/user/info")
def get_user_info(current_user = Depends(get_current_user)):
    """获取当前用户信息"""
    from models import User, get_session

    if not current_user:
        return {"code": 1, "message": "未登录", "data": None}

    # 如果用户没有邀请码，自动生成一个
    if not current_user.get('invite_code'):
        with get_session() as session:
            user = session.query(User).filter(User.id == current_user['id']).first()
            if user and not user.invite_code:
                new_code = generate_invite_code()
                while session.query(User).filter(User.invite_code == new_code).first():
                    new_code = generate_invite_code()
                user.invite_code = new_code
                session.flush()

    return {
        "code": 0,
        "message": "success",
        "data": current_user
    }


@app.get("/api/user/invite-list")
def get_invite_list(
    current_user = Depends(get_current_user),
    user_id: int = Query(None, description="用户ID（当token不可用时使用）")
):
    """获取邀请列表"""
    from models import User, get_session, format_datetime

    # 优先用 token 认证，否则用 user_id 参数
    user = None
    if current_user:
        user_id = current_user['id']

    if not user_id:
        return {"code": 1, "message": "未登录", "data": None}

    with get_session() as session:
        # 获取当前用户信息
        user = session.query(User).filter(User.id == user_id).first()
        if not user:
            return {"code": 1, "message": "用户不存在", "data": None}

        # 如果没有邀请码，自动生成
        if not user.invite_code:
            new_code = generate_invite_code()
            while session.query(User).filter(User.invite_code == new_code).first():
                new_code = generate_invite_code()
            user.invite_code = new_code
            session.flush()

        # 获取邀请的用户列表
        invited_users = session.query(User).filter(
            User.invited_by == user.id
        ).order_by(User.created_at.desc()).all()

        invited_list = []
        for u in invited_users:
            invited_list.append({
                'id': u.id,
                'username': u.username,
                'nickname': u.nickname,
                'phone': u.phone,
                'avatar': u.avatar,
                'is_vip': u.is_vip,
                'created_at': format_datetime(u.created_at)
            })

        return {
            "code": 0,
            "message": "success",
            "data": {
                'invite_code': user.invite_code,
                'points': user.points or 0,
                'invited_count': len(invited_list),
                'vip_count': sum(1 for u in invited_users if u.is_vip),
                'invited_list': invited_list
            }
        }


@app.post("/api/user/withdraw")
def withdraw_points(current_user = Depends(get_current_user), req: Request = None):
    """积分提现"""
    from models import User, UserLog, get_session

    if not current_user:
        return {"code": 1, "message": "未登录", "data": None}

    # 获取客户端信息
    ip_address = None
    user_agent = None
    if req:
        ip_address = req.client.host if req.client else None
        user_agent = req.headers.get("user-agent")

    min_points = 100  # 最低提现积分
    withdraw_amount = 10  # 提现金额（元）

    with get_session() as session:
        user = session.query(User).filter(User.id == current_user['id']).first()
        if not user:
            return {"code": 1, "message": "用户不存在", "data": None}

        user_points = user.points or 0
        if user_points < min_points:
            return {"code": 1, "message": f"积分不足{min_points}，当前积分：{user_points}", "data": None}

        # 扣除积分
        user.points = user_points - min_points

        # 记录日志
        log = UserLog(
            user_id=user.id,
            action_type="withdraw",
            action_detail=json.dumps({"points": min_points, "amount": withdraw_amount}),
            ip_address=ip_address,
            user_agent=user_agent,
            status="success"
        )
        session.add(log)
        session.flush()

        return {
            "code": 0,
            "message": f"提现成功，扣除{min_points}积分，即将到账{withdraw_amount}元",
            "data": {
                'remaining_points': user.points
            }
        }


@app.post("/api/user/change-password")
def change_password(request: ChangePasswordRequest, req: Request = None, current_user = Depends(get_current_user)):
    """修改密码（已登录用户）"""
    from models import User, get_session, format_datetime

    if not current_user:
        return {"code": 1, "message": "未登录", "data": None}

    old_password = request.old_password.strip()
    new_password = request.new_password.strip()

    # 获取客户端信息
    ip_address = None
    user_agent = None
    if req:
        ip_address = req.client.host if req.client else None
        user_agent = req.headers.get("user-agent")

    if not old_password:
        log_user_action(current_user['id'], "change_password", {"reason": "missing_old_password"},
                       ip_address, user_agent, "failed")
        return {"code": 1, "message": "请输入旧密码", "data": None}

    if not new_password or len(new_password) < 6:
        log_user_action(current_user['id'], "change_password", {"reason": "password_too_short"},
                       ip_address, user_agent, "failed")
        return {"code": 1, "message": "新密码长度不能少于6位", "data": None}

    with get_session() as session:
        user = session.query(User).filter(User.id == current_user['id']).first()

        if not user:
            log_user_action(current_user['id'], "change_password", {"reason": "user_not_found"},
                           ip_address, user_agent, "failed")
            return {"code": 1, "message": "用户不存在", "data": None}

        # 如果用户没有设置过密码，需要先设置密码
        if not user.password_hash:
            # 第一次设置密码，不需要验证旧密码
            user.password_hash = get_password_hash(new_password)

            log_user_action(current_user['id'], "change_password", {"action": "set_password"},
                           ip_address, user_agent, "success")
            return {
                "code": 0,
                "message": "密码设置成功",
                "data": None
            }

        # 验证旧密码
        if not verify_password(old_password, user.password_hash):
            log_user_action(current_user['id'], "change_password", {"reason": "wrong_old_password"},
                           ip_address, user_agent, "failed")
            return {"code": 1, "message": "旧密码不正确", "data": None}

        # 更新密码
        user.password_hash = get_password_hash(new_password)

        log_user_action(current_user['id'], "change_password", {},
                       ip_address, user_agent, "success")

        return {
            "code": 0,
            "message": "密码修改成功",
            "data": None
        }


@app.post("/api/user/profile")
def update_profile(request: UpdateProfileRequest, req: Request = None, current_user = Depends(get_current_user)):
    """更新用户基本信息"""
    from models import User, get_session, format_datetime

    if not current_user:
        return {"code": 1, "message": "未登录", "data": None}

    # 获取客户端信息
    ip_address = None
    user_agent = None
    if req:
        ip_address = req.client.host if req.client else None
        user_agent = req.headers.get("user-agent")

    with get_session() as session:
        user = session.query(User).filter(User.id == current_user['id']).first()

        if not user:
            return {"code": 1, "message": "用户不存在", "data": None}

        # 更新字段
        update_fields = {}

        if request.username is not None:
            # 检查用户名是否被占用
            if request.username != user.username:
                existing = session.query(User).filter(User.username == request.username).first()
                if existing and existing.id != user.id:
                    return {"code": 1, "message": "用户名已被占用", "data": None}
            user.username = request.username
            update_fields["username"] = request.username

        if request.nickname is not None:
            user.nickname = request.nickname
            update_fields["nickname"] = request.nickname

        if request.email is not None:
            # 检查邮箱是否被占用
            if request.email != user.email:
                if request.email:
                    existing = session.query(User).filter(User.email == request.email).first()
                    if existing and existing.id != user.id:
                        return {"code": 1, "message": "邮箱已被占用", "data": None}
            user.email = request.email
            update_fields["email"] = request.email

        if request.avatar is not None:
            user.avatar = request.avatar
            update_fields["avatar"] = request.avatar

        log_user_action(user.id, "update_profile", update_fields,
                       ip_address, user_agent, "success")

        return {
            "code": 0,
            "message": "更新成功",
            "data": user.to_dict()
        }


@app.post("/api/auth/reset_password")
def reset_password(request: ResetPasswordRequest, req: Request = None):
    """重置密码（忘记密码）"""
    from models import User, get_session, format_datetime

    phone = request.phone.strip()
    code = request.code.strip()
    new_password = request.new_password.strip()

    # 获取客户端信息
    ip_address = None
    user_agent = None
    if req:
        ip_address = req.client.host if req.client else None
        user_agent = req.headers.get("user-agent")

    if not phone or len(phone) != 11:
        log_user_action(None, "password_reset", {"phone": phone[:7] + "****" if phone else None},
                       ip_address, user_agent, "failed")
        return {"code": 1, "message": "手机号格式不正确", "data": None}
    if not new_password or len(new_password) < 6:
        log_user_action(None, "password_reset", {"phone": phone[:7] + "****" if phone else None},
                       ip_address, user_agent, "failed")
        return {"code": 1, "message": "密码长度不能少于6位", "data": None}

    # 验证验证码
    if not verify_sms_code(phone, code, "reset_password"):
        log_user_action(None, "password_reset", {"phone": phone[:7] + "****", "reason": "invalid_code"},
                       ip_address, user_agent, "failed")
        return {"code": 1, "message": "验证码无效或已过期", "data": None}

    with get_session() as session:
        user = session.query(User).filter(User.phone == phone).first()

        if not user:
            log_user_action(None, "password_reset", {"phone": phone[:7] + "****", "reason": "user_not_found"},
                           ip_address, user_agent, "failed")
            return {"code": 1, "message": "该手机号未注册", "data": None}

        # 检查用户状态
        if user.status == "banned":
            log_user_action(user.id, "password_reset", {"phone": phone[:7] + "****", "reason": "banned"},
                           ip_address, user_agent, "failed")
            return {"code": 1, "message": "账号已被禁用", "data": None}

        # 更新密码
        user.password_hash = get_password_hash(new_password)

        # 记录密码重置成功日志
        log_user_action(user.id, "password_reset", {
            "phone": phone[:7] + "****"
        }, ip_address, user_agent, "success")

        return {
            "code": 0,
            "message": "密码重置成功",
            "data": None
        }


# ==================== 用户管理后台 API ====================

@app.get("/admin-api/users")
def get_users(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    keyword: Optional[str] = None,
    status: Optional[str] = None,
    invited_by: Optional[str] = None  # 改为字符串，后面转换
):
    """获取用户列表（管理员接口）"""
    from models import User, get_session, format_datetime
    from sqlalchemy import or_

    # 转换 invited_by 为整数或 None
    invited_by_int = None
    if invited_by and invited_by.strip():
        try:
            invited_by_int = int(invited_by.strip())
        except ValueError:
            pass

    with get_session() as session:
        query = session.query(User)

        if keyword:
            query = query.filter(
                or_(
                    User.username.contains(keyword),
                    User.phone.contains(keyword),
                    User.email.contains(keyword)
                )
            )

        if status:
            query = query.filter(User.status == status)

        if invited_by_int:
            query = query.filter(User.invited_by == invited_by_int)

        total = query.count()
        offset = (page - 1) * limit
        users = query.order_by(User.created_at.desc()).offset(offset).limit(limit).all()

        return {
            "code": 0,
            "message": "success",
            "data": {
                "items": [u.to_dict(session) for u in users],
                "total": total,
                "page": page,
                "limit": limit
            }
        }


@app.post("/admin-api/users/{user_id}/status")
def update_user_status(
    user_id: int,
    status: str = Query(..., description="用户状态: active/banned")
):
    """更新用户状态（管理员接口）"""
    from models import User, get_session, format_datetime

    if status not in ["active", "banned"]:
        return {"code": 1, "message": "无效的状态值", "data": None}

    with get_session() as session:
        user = session.query(User).filter(User.id == user_id).first()

        if not user:
            return {"code": 1, "message": "用户不存在", "data": None}

        user.status = status

        return {
            "code": 0,
            "message": "更新成功",
            "data": user.to_dict()
        }


@app.post("/admin-api/users/{user_id}/reset-password")
def admin_reset_user_password(user_id: int):
    """管理员重置用户密码（发送验证码）"""
    from models import User, get_session, format_datetime
    import random

    with get_session() as session:
        user = session.query(User).filter(User.id == user_id).first()

        if not user:
            return {"code": 1, "message": "用户不存在", "data": None}

        # 生成临时密码
        temp_password = str(random.randint(100000, 999999))

        # 这里实际应该发送短信或邮件，我们直接返回临时密码
        # 在生产环境中应该通过短信/邮件发送给用户
        return {
            "code": 0,
            "message": "密码重置成功，请通过短信查收新密码",
            "data": {
                "temp_password": temp_password
            }
        }


class AdminSetVipRequest(BaseModel):
    """管理员设置VIP请求"""
    is_vip: bool
    duration_days: Optional[int] = None
    expire_at: Optional[str] = None
    plan_ids: Optional[List[int]] = None
    cancel_plan_ids: Optional[List[int]] = None
    remark: Optional[str] = None


@app.post("/admin-api/users/{user_id}/set-vip")
def admin_set_user_vip(user_id: int, data: AdminSetVipRequest):
    """管理员设置用户VIP"""
    try:
        from models import User, get_session, format_datetime, UserVipPlan, VipPlan
        from models import utc_plus_8
        from datetime import datetime, timedelta

        with get_session() as session:
            user = session.query(User).filter(User.id == user_id).first()

            if not user:
                return {"code": 1, "message": "用户不存在", "data": None}

            # 记录之前是否是VIP（用于判断是否首次成为VIP）
            was_vip = user.is_vip or False

            if data.is_vip:
                # 开启VIP
                user.is_vip = True

                if data.expire_at:
                    # 指定过期时间
                    try:
                        user.vip_expire_at = datetime.strptime(data.expire_at, '%Y-%m-%d %H:%M:%S')
                    except ValueError:
                        return {"code": 1, "message": "过期时间格式错误，应为 YYYY-MM-DD HH:MM:SS", "data": None}
                elif data.duration_days:
                    # 按天数延期
                    if user.vip_expire_at and user.vip_expire_at > utc_plus_8():
                        user.vip_expire_at = user.vip_expire_at + timedelta(days=data.duration_days)
                    else:
                        user.vip_expire_at = utc_plus_8() + timedelta(days=data.duration_days)
                else:
                    return {"code": 1, "message": "请指定过期时间或天数", "data": None}

                # 如果指定了套餐ID数组，记录用户套餐关联（同一套餐去重：存在则更新，不存在则新增）
                if data.plan_ids:
                    for plan_id in data.plan_ids:
                        plan = session.query(VipPlan).filter(VipPlan.id == plan_id).first()
                        if plan:
                            # 检查该用户是否已开通此套餐
                            existing = session.query(UserVipPlan).filter(
                                UserVipPlan.user_id == user_id,
                                UserVipPlan.plan_id == plan_id
                            ).first()

                            if existing:
                                # 已存在则更新到期时间和设备类型
                                existing.expire_at = user.vip_expire_at
                                existing.terminal = plan.devices
                            else:
                                # 不存在则新增记录
                                user_plan = UserVipPlan(
                                    user_id=user_id,
                                    plan_id=plan_id,
                                    terminal=plan.devices,
                                    activated_at=utc_plus_8(),
                                    expire_at=user.vip_expire_at
                                )
                                session.add(user_plan)

                # 如果是首次成为VIP，给邀请人加积分
                if not was_vip and user.invited_by:
                    add_inviter_vip_reward(session, user_id, 20)
            else:
                # 关闭指定套餐
                if data.cancel_plan_ids:
                    for user_vip_plan_id in data.cancel_plan_ids:
                        session.query(UserVipPlan).filter(
                            UserVipPlan.id == user_vip_plan_id,
                            UserVipPlan.user_id == user_id
                        ).delete()

                # 检查用户是否还有其他VIP套餐
                remaining_plans = session.query(UserVipPlan).filter(
                    UserVipPlan.user_id == user_id
                ).all()

                if len(remaining_plans) == 0:
                    # 没有剩余套餐了，关闭整个VIP
                    user.is_vip = False
                    user.vip_expire_at = None

            user.updated_at = utc_plus_8()
            session.commit()

            logger.info(f"管理员设置用户 {user.username} VIP状态: is_vip={data.is_vip}, remark={data.remark}")

            return {
                "code": 0,
                "message": "设置成功",
                "data": user.to_dict()
            }
    except Exception as e:
        logger.error(f"设置用户VIP失败: {e}")
        return {"code": 1, "message": f"设置失败: {str(e)}", "data": None}


@app.get("/admin-api/vip/plans")
def admin_get_vip_plans():
    """获取VIP套餐列表"""
    try:
        from models import VipPlan, get_session

        with get_session() as session:
            plans = session.query(VipPlan).order_by(VipPlan.sort_order, VipPlan.price).all()

            return {
                "code": 0,
                "message": "success",
                "data": [p.to_dict() for p in plans]
            }
    except Exception as e:
        logger.error(f"获取VIP套餐失败: {e}")
        return {"code": 1, "message": f"获取失败: {str(e)}", "data": None}


@app.get("/api/vip/plans")
def get_vip_plans(
    plan_type: Optional[str] = Query(None, description="套餐类型：promotion-优惠期，formal-正式")
):
    """获取VIP套餐列表（公开接口，只返回启用的）"""
    try:
        from models import VipPlan, VipPlanConfig, get_session

        with get_session() as session:
            # 查询套餐
            query = session.query(VipPlan).filter(VipPlan.is_enabled == True)
            if plan_type:
                query = query.filter(VipPlan.plan_type == plan_type)
            plans = query.order_by(VipPlan.sort_order, VipPlan.price).all()

            # 查询配置
            config_query = session.query(VipPlanConfig)
            if plan_type:
                config_query = config_query.filter(VipPlanConfig.plan_type == plan_type)
            configs = config_query.all()

            # 构建配置map
            config_map = {config.plan_type: config.tip_text for config in configs}

            return {
                "code": 0,
                "message": "success",
                "data": {
                    "plans": [p.to_dict() for p in plans],
                    "configs": {
                        config.plan_type: config.to_dict()
                        for config in configs
                    }
                }
            }
    except Exception as e:
        logger.error(f"获取VIP套餐失败: {e}")
        return {"code": 1, "message": f"获取失败: {str(e)}", "data": None}


# ==================== 观看历史 API ====================

class UserWatchHistoryRequest(BaseModel):
    user_id: int
    series_id: int
    episode_id: Optional[int] = None
    progress: int = 0


@app.get("/api/user/watch-history")
def get_watch_history(
    user_id: int = Query(..., description="用户ID"),
    group_by: bool = Query(True, description="是否按剧集聚合"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100)
):
    """获取用户观看历史（支持聚合模式）"""
    try:
        from models import UserWatchHistory, CATEGORY_KEYS, get_video_model, get_video_ep_model, get_session
        from sqlalchemy import desc, func

        with get_session() as session:
            # 查询所有观看历史记录
            all_histories = session.query(UserWatchHistory).filter(
                UserWatchHistory.user_id == user_id
            ).order_by(desc(UserWatchHistory.last_watched)).all()

            if group_by:
                # 聚合模式：按 series_cid 分组
                groups = {}
                for history in all_histories:
                    cid = history.series_cid
                    cat_key = history.category_key or 'tv'
                    if cid not in groups:
                        # 从对应频道表获取剧集信息
                        SeriesModel = get_video_model(cat_key)
                        series = None

                        # 优先按cid查询
                        if cid:
                            series = session.query(SeriesModel).filter(SeriesModel.cid == cid).first()

                        # 如果cid为空，按series_id查询
                        if not series and history.series_id:
                            series = session.query(SeriesModel).filter(SeriesModel.id == history.series_id).first()

                        if not series:
                            continue
                        groups[cid] = {
                            'series': {**series.to_dict(), 'category_key': cat_key},
                            'episodes': [],
                            'latest_watched': history.last_watched.isoformat() if history.last_watched else '',
                        }
                    groups[cid]['episodes'].append({
                        'history_id': history.id,
                        'episode_id': history.episode_id,
                        'play_title': history.play_title or '',
                        'episode_num': '',
                        'last_watched': history.last_watched.isoformat() if history.last_watched else None,
                    })

                # 按最新观看时间排序
                sorted_groups = sorted(
                    groups.values(),
                    key=lambda g: g['latest_watched'],
                    reverse=True
                )

                # 分页
                total = len(sorted_groups)
                offset = (page - 1) * limit
                paged = sorted_groups[offset:offset + limit]

                for g in paged:
                    g['watched_count'] = len(g['episodes'])
                    g['total_episodes'] = g['series'].get('total_episodes', 0)
                    g['episodes'].sort(key=lambda e: str(e.get('episode_num', '')))
                    del g['latest_watched']

                return {
                    "code": 0,
                    "message": "success",
                    "data": {
                        "items": paged,
                        "page": page,
                        "limit": limit,
                        "total": total
                    }
                }

            else:
                # 非聚合模式：逐条返回
                total = len(all_histories)
                offset = (page - 1) * limit
                paged_histories = all_histories[offset:offset + limit]

                history_list = []
                for history in paged_histories:
                    cat_key = history.category_key or 'tv'
                    SeriesModel = get_video_model(cat_key)
                    series = None

                    # 优先按cid查询
                    if history.series_cid:
                        series = session.query(SeriesModel).filter(SeriesModel.cid == history.series_cid).first()

                    # 如果cid为空，按series_id查询
                    if not series and history.series_id:
                        series = session.query(SeriesModel).filter(SeriesModel.id == history.series_id).first()

                    item = {
                        **history.to_dict(),
                        'series': {**series.to_dict(), 'category_key': cat_key} if series else None,
                        'episode': None
                    }
                    history_list.append(item)

                return {
                    "code": 0,
                    "message": "success",
                    "data": {
                        "items": history_list,
                        "page": page,
                        "limit": limit,
                        "total": total
                    }
                }
    except Exception as e:
        logger.error(f"获取观看历史失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/user/watch-progress")
def get_watch_progress(user_id: int = Query(..., description="用户ID")):
    """获取用户所有剧集的观看进度（已看集数）"""
    try:
        from models import UserWatchHistory, get_session
        from sqlalchemy import func

        with get_session() as session:
            # 按 series_cid 分组统计观看数量
            results = session.query(
                UserWatchHistory.series_cid,
                func.count(UserWatchHistory.id).label('cnt')
            ).filter(
                UserWatchHistory.user_id == user_id
            ).group_by(
                UserWatchHistory.series_cid
            ).all()

            progress = {row.series_cid: row.cnt for row in results}

            return {
                "code": 0,
                "message": "success",
                "data": progress
            }
    except Exception as e:
        logger.error(f"获取观看进度失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/user/watch-history")
def update_watch_history(request: UserWatchHistoryRequest):
    """更新观看历史（按分集去重，记录所有看过的分集）"""
    try:
        from models import UserWatchHistory, UserFollow, get_video_ep_model, get_video_model, get_session

        with get_session() as session:
            existing = None
            episode_num = None
            play_title = None
            category_key = getattr(request, 'category_key', None) or 'tv'
            series_cid = getattr(request, 'series_cid', None) or ''

            # 如果series_cid为空，通过series_id查询获取
            if not series_cid and getattr(request, 'series_id', None):
                for cat in ['tv', 'movie', 'variety', 'cartoon', 'child']:
                    SeriesModel = get_video_model(cat)
                    series = session.query(SeriesModel).filter(SeriesModel.id == request.series_id).first()
                    if series:
                        series_cid = series.cid
                        category_key = cat
                        break

            if request.episode_id:
                existing = session.query(UserWatchHistory).filter(
                    UserWatchHistory.user_id == request.user_id,
                    UserWatchHistory.episode_id == request.episode_id
                ).first()

                # 从对应频道表获取分集信息
                EpModel = get_video_ep_model(category_key)
                episode = session.query(EpModel).filter(EpModel.id == request.episode_id).first()
                if episode:
                    episode_num = episode.episode_num
                    play_title = episode.play_title or episode.union_title or f"第{episode.episode_num}集"

            if existing:
                existing.last_watched = utc_plus_8()
                if play_title and not existing.play_title:
                    existing.play_title = play_title
            else:
                history = UserWatchHistory(
                    user_id=request.user_id,
                    category_key=category_key,
                    series_cid=series_cid,
                    series_id=request.series_id,
                    episode_id=request.episode_id,
                    play_title=play_title,
                    last_watched=utc_plus_8()
                )
                session.add(history)

            # 同步更新追剧记录
            if request.episode_id and episode_num and series_cid:
                follow = session.query(UserFollow).filter(
                    UserFollow.user_id == request.user_id,
                    UserFollow.series_cid == series_cid
                ).first()
                if follow:
                    follow.last_episode_id = request.episode_id
                    follow.last_episode_num = episode_num

            return {
                "code": 0,
                "message": "success",
                "data": {"updated": existing is not None}
            }
    except Exception as e:
        logger.error(f"更新观看历史失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/user/watch-history/{history_id}")
def delete_watch_history(history_id: int):
    """删除单条观看历史"""
    try:
        from models import UserWatchHistory, get_session

        with get_session() as session:
            history = session.query(UserWatchHistory).filter(
                UserWatchHistory.id == history_id
            ).first()

            if not history:
                return {"code": 1, "message": "记录不存在", "data": None}

            session.delete(history)

            return {"code": 0, "message": "删除成功", "data": None}
    except Exception as e:
        logger.error(f"删除观看历史失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/user/watch-history")
def clear_watch_history(user_id: int = Query(..., description="用户ID")):
    """清空用户所有观看历史"""
    try:
        from models import UserWatchHistory, get_session

        with get_session() as session:
            session.query(UserWatchHistory).filter(
                UserWatchHistory.user_id == user_id
            ).delete()

            return {"code": 0, "message": "清空成功", "data": None}
    except Exception as e:
        logger.error(f"清空观看历史失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 追剧 API ====================

@app.get("/api/user/follow")
def get_follow_list(
    user_id: int = Query(..., description="用户ID"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100)
):
    """获取用户追剧列表（包含最后观看进度）"""
    try:
        from models import UserFollow, get_video_model, get_video_ep_model, get_session
        from sqlalchemy import desc

        with get_session() as session:
            follows = session.query(UserFollow).filter(
                UserFollow.user_id == user_id
            ).order_by(desc(UserFollow.follow_time)).all()

            total = len(follows)
            offset = (page - 1) * limit
            paged = follows[offset:offset + limit]

            follow_list = []
            for follow in paged:
                cat_key = follow.category_key or 'tv'
                SeriesModel = get_video_model(cat_key)
                series = session.query(SeriesModel).filter(SeriesModel.cid == follow.series_cid).first()
                item = {
                    **follow.to_dict(),
                    'series': {**series.to_dict(), 'category_key': cat_key} if series else None,
                    'last_episode': None
                }
                follow_list.append(item)

            return {
                "code": 0,
                "message": "success",
                "data": {
                    "items": follow_list,
                    "page": page,
                    "limit": limit,
                    "total": total
                }
            }
    except Exception as e:
        logger.error(f"获取追剧列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/user/follow/{series_id}")
def add_follow(
    series_id: int,
    user_id: int = Query(..., description="用户ID")
):
    """添加追剧"""
    try:
        from models import UserFollow, get_video_model, get_session

        with get_session() as session:
            # 通过series_id查找剧集信息获取category_key和cid
            category_key = 'tv'
            series_cid = ''
            for cat in ['tv', 'movie', 'variety', 'cartoon', 'child']:
                SeriesModel = get_video_model(cat)
                series = session.query(SeriesModel).filter(SeriesModel.id == series_id).first()
                if series:
                    category_key = cat
                    series_cid = series.cid
                    break

            existing = session.query(UserFollow).filter(
                UserFollow.user_id == user_id,
                UserFollow.series_cid == series_cid
            ).first() if series_cid else None

            if existing:
                return {"code": 1, "message": "已在追剧中", "data": None}

            follow = UserFollow(
                user_id=user_id,
                category_key=category_key,
                series_cid=series_cid,
                series_id=series_id,
                follow_time=utc_plus_8()
            )
            session.add(follow)

            return {"code": 0, "message": "追更成功", "data": None}
    except Exception as e:
        logger.error(f"添加追剧失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/user/follow/{series_id}")
def remove_follow(
    series_id: int,
    user_id: int = Query(..., description="用户ID")
):
    """取消追剧"""
    try:
        from models import UserFollow, get_video_model, get_session

        with get_session() as session:
            # 通过series_id查找cid
            series_cid = ''
            for cat in ['tv', 'movie', 'variety', 'cartoon', 'child']:
                SeriesModel = get_video_model(cat)
                series = session.query(SeriesModel).filter(SeriesModel.id == series_id).first()
                if series:
                    series_cid = series.cid
                    break

            follow = session.query(UserFollow).filter(
                UserFollow.user_id == user_id,
                UserFollow.series_cid == series_cid
            ).first() if series_cid else None

            if not follow:
                return {"code": 1, "message": "未在追剧中", "data": None}

            session.delete(follow)

            return {"code": 0, "message": "取消成功", "data": None}
    except Exception as e:
        logger.error(f"取消追剧失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/user/follow/check")
def check_follow(
    user_id: int = Query(..., description="用户ID"),
    series_id: int = Query(..., description="剧集ID")
):
    """检查是否已追剧"""
    try:
        from models import UserFollow, get_video_model, get_session

        with get_session() as session:
            series_cid = ''
            for cat in ['tv', 'movie', 'variety', 'cartoon', 'child']:
                SeriesModel = get_video_model(cat)
                series = session.query(SeriesModel).filter(SeriesModel.id == series_id).first()
                if series:
                    series_cid = series.cid
                    break

            exists = session.query(UserFollow).filter(
                UserFollow.user_id == user_id,
                UserFollow.series_cid == series_cid
            ).first() is not None if series_cid else False

            return {
                "code": 0,
                "message": "success",
                "data": {"followed": exists}
            }
    except Exception as e:
        logger.error(f"检查追剧状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/user/follow/updates")
def get_follow_updates(
    user_id: int = Query(..., description="用户ID")
):
    """获取追剧更新通知"""
    try:
        from models import UserFollow, get_video_model, get_video_ep_model, get_session
        from sqlalchemy import desc

        with get_session() as session:
            follows = session.query(UserFollow).filter(
                UserFollow.user_id == user_id
            ).all()

            updates = []
            for follow in follows:
                cat_key = follow.category_key or 'tv'
                SeriesModel = get_video_model(cat_key)
                EpModel = get_video_ep_model(cat_key)
                series = session.query(SeriesModel).filter(SeriesModel.cid == follow.series_cid).first()
                if not series:
                    continue

                latest_episode = session.query(EpModel).\
                    filter(EpModel.series_id == series.id, EpModel.episode_type == 0).\
                    order_by(desc(EpModel.created_at)).first()

                if latest_episode and follow.last_check_time:
                    if latest_episode.created_at > follow.last_check_time:
                        updates.append({
                            'series': {**series.to_dict(), 'category_key': cat_key},
                            'latest_episode': latest_episode.to_dict(),
                            'unread': True
                        })

                follow.last_check_time = utc_plus_8()

            return {
                "code": 0,
                "message": "success",
                "data": updates
            }
    except Exception as e:
        logger.error(f"获取追剧更新失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 收藏 API ====================

@app.get("/api/user/bookmarks")
def get_bookmarks(
    user_id: int = Query(..., description="用户ID"),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100)
):
    """获取用户收藏列表"""
    try:
        from models import UserBookmark, get_video_model, get_session
        from sqlalchemy import desc

        with get_session() as session:
            bookmarks = session.query(UserBookmark).filter(
                UserBookmark.user_id == user_id
            ).order_by(desc(UserBookmark.created_at)).all()

            total = len(bookmarks)
            offset = (page - 1) * limit
            paged = bookmarks[offset:offset + limit]

            items = []
            for bookmark in paged:
                cat_key = bookmark.category_key or 'tv'
                SeriesModel = get_video_model(cat_key)
                series = session.query(SeriesModel).filter(SeriesModel.cid == bookmark.series_cid).first()
                items.append({
                    **bookmark.to_dict(),
                    'series': {**series.to_dict(), 'category_key': cat_key} if series else None
                })

            return {
                "code": 0,
                "message": "success",
                "data": {
                    "items": items,
                    "page": page,
                    "limit": limit,
                    "total": total
                }
            }
    except Exception as e:
        logger.error(f"获取收藏列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/user/bookmarks/{series_id}")
def add_bookmark(
    series_id: int,
    user_id: int = Query(..., description="用户ID")
):
    """添加收藏"""
    try:
        from models import UserBookmark, get_video_model, get_session

        with get_session() as session:
            category_key = 'tv'
            series_cid = ''
            for cat in ['tv', 'movie', 'variety', 'cartoon', 'child']:
                SeriesModel = get_video_model(cat)
                series = session.query(SeriesModel).filter(SeriesModel.id == series_id).first()
                if series:
                    category_key = cat
                    series_cid = series.cid
                    break

            existing = session.query(UserBookmark).filter(
                UserBookmark.user_id == user_id,
                UserBookmark.series_cid == series_cid
            ).first() if series_cid else None

            if existing:
                return {"code": 1, "message": "已收藏", "data": None}

            bookmark = UserBookmark(
                user_id=user_id,
                category_key=category_key,
                series_cid=series_cid,
                series_id=series_id,
                created_at=utc_plus_8()
            )
            session.add(bookmark)

            return {"code": 0, "message": "收藏成功", "data": None}
    except Exception as e:
        logger.error(f"添加收藏失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/user/bookmarks/{series_id}")
def remove_bookmark(
    series_id: int,
    user_id: int = Query(..., description="用户ID")
):
    """取消收藏"""
    try:
        from models import UserBookmark, get_video_model, get_session

        with get_session() as session:
            series_cid = ''
            for cat in ['tv', 'movie', 'variety', 'cartoon', 'child']:
                SeriesModel = get_video_model(cat)
                series = session.query(SeriesModel).filter(SeriesModel.id == series_id).first()
                if series:
                    series_cid = series.cid
                    break

            bookmark = session.query(UserBookmark).filter(
                UserBookmark.user_id == user_id,
                UserBookmark.series_cid == series_cid
            ).first() if series_cid else None

            if not bookmark:
                return {"code": 1, "message": "未收藏", "data": None}

            session.delete(bookmark)

            return {"code": 0, "message": "取消成功", "data": None}
    except Exception as e:
        logger.error(f"取消收藏失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/user/bookmarks/check")
def check_bookmark(
    user_id: int = Query(..., description="用户ID"),
    series_id: int = Query(..., description="剧集ID")
):
    """检查是否已收藏"""
    try:
        from models import UserBookmark, get_video_model, get_session

        with get_session() as session:
            series_cid = ''
            for cat in ['tv', 'movie', 'variety', 'cartoon', 'child']:
                SeriesModel = get_video_model(cat)
                series = session.query(SeriesModel).filter(SeriesModel.id == series_id).first()
                if series:
                    series_cid = series.cid
                    break

            exists = session.query(UserBookmark).filter(
                UserBookmark.user_id == user_id,
                UserBookmark.series_cid == series_cid
            ).first() is not None if series_cid else False

            return {
                "code": 0,
                "message": "success",
                "data": {"bookmarked": exists}
            }
    except Exception as e:
        logger.error(f"检查收藏状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))



# ==================== 实时日志 API ====================
import asyncio
import json


async def log_generator(since_timestamp: str = None):
    """SSE 日志生成器"""
    from core.log_stream import get_memory_log_handler
    handler = get_memory_log_handler()
    last_sent_timestamp = since_timestamp

    while True:
        try:
            logs = handler.get_logs(last_sent_timestamp)
            if logs:
                last_sent_timestamp = logs[-1]['timestamp']
                for log in logs:
                    yield f"data: {json.dumps(log, ensure_ascii=False)}\n\n"

            await asyncio.sleep(0.5)
        except asyncio.CancelledError:
            break


@app.get("/admin-api/logs/stream")
async def stream_logs(since: Optional[str] = None):
    """
    实时日志流（Server-Sent Events）
    """
    return StreamingResponse(
        log_generator(since),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@app.get("/admin-api/logs")
def get_logs(since: Optional[str] = None, task_id: Optional[int] = None):
    """
    获取历史日志
    """
    from core.log_stream import get_memory_log_handler
    handler = get_memory_log_handler()

    # 添加一条测试日志，方便调试
    import logging
    logging.info("系统日志服务已就绪")

    logs_data = handler.get_logs(since, task_id)
    return {
        "code": 0,
        "message": "success",
        "data": logs_data
    }


@app.get("/admin-api/tasks/{task_id}/logs")
def get_task_logs(task_id: int, page: int = Query(1, ge=1), limit: int = Query(100, ge=1, le=1000)):
    """
    获取指定任务的日志（从数据库中读取）
    """
    try:
        from models import TaskCrawlLog, get_session
        with get_session() as session:
            query = session.query(TaskCrawlLog).filter(TaskCrawlLog.task_id == task_id)
            total = query.count()
            offset = (page - 1) * limit
            logs = query.order_by(TaskCrawlLog.created_at.asc()).offset(offset).limit(limit).all()
            return {
                "code": 0,
                "message": "success",
                "data": {
                    "items": [log.to_dict() for log in logs],
                    "total": total,
                    "page": page,
                    "limit": limit
                }
            }
    except Exception as e:
        logger.error(f"获取任务日志失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/admin-api/logs/cleanup")
def cleanup_old_logs(days: int = Query(10, ge=1, description="保留天数")):
    """
    清理指定天数之前的旧日志
    """
    try:
        from core.log_stream import cleanup_old_logs
        deleted = cleanup_old_logs(days)
        return {
            "code": 0,
            "message": "success",
            "data": {"deleted_count": deleted}
        }
    except Exception as e:
        logger.error(f"清理旧日志失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============ 会员套餐管理 ============

class VipPlanCreate(BaseModel):
    name: str
    price: float
    original_price: Optional[float] = None
    duration_days: int
    unit: Optional[str] = None
    save_amount: Optional[float] = 0
    is_recommend: Optional[bool] = False
    is_enabled: Optional[bool] = True
    sort_order: Optional[int] = 0
    plan_type: Optional[str] = "formal"
    duration_type: Optional[str] = "monthly"
    devices: Optional[str] = "pc"


class VipPlanUpdate(BaseModel):
    name: Optional[str] = None
    price: Optional[float] = None
    original_price: Optional[float] = None
    duration_days: Optional[int] = None
    unit: Optional[str] = None
    save_amount: Optional[float] = None
    is_recommend: Optional[bool] = None
    is_enabled: Optional[bool] = None
    sort_order: Optional[int] = None
    plan_type: Optional[str] = None
    duration_type: Optional[str] = None
    devices: Optional[str] = None


# ========== 卡密/订单相关Pydantic模型 ==========

class CdkeyRedeem(BaseModel):
    """卡密兑换请求"""
    code: str


class CdkeyBatchCreate(BaseModel):
    """批量创建卡密请求"""
    plan_id: int
    duration_days: Optional[int] = None
    count: int = 1
    expired_days: Optional[int] = 365


class OrderCreate(BaseModel):
    """创建订单请求"""
    plan_id: int


# ========== 会员用户端API ==========

@app.post("/api/vip/redeem")
def redeem_cdkey(data: CdkeyRedeem, req: Request = None, current_user = Depends(get_current_user)):
    """卡密兑换会员"""
    try:
        from models import VipCdkey, get_session, User
        from models import utc_plus_8, format_datetime
        from datetime import timedelta

        with get_session() as session:
            # 查找卡密
            cdkey = session.query(VipCdkey).filter(VipCdkey.code == data.code).first()
            if not cdkey:
                raise HTTPException(status_code=400, detail="卡密不存在")

            if cdkey.is_used:
                raise HTTPException(status_code=400, detail="卡密已使用")

            if cdkey.expired_at and cdkey.expired_at < utc_plus_8():
                raise HTTPException(status_code=400, detail="卡密已过期")

            # 更新用户会员
            user = session.query(User).filter(User.id == current_user['id']).first()
            was_vip = user.is_vip  # 记录之前是否是VIP
            if user.vip_expire_at and user.vip_expire_at > utc_plus_8():
                # 会员未过期，延期
                user.vip_expire_at = user.vip_expire_at + timedelta(days=cdkey.duration_days)
            else:
                # 新会员或已过期
                user.vip_expire_at = utc_plus_8() + timedelta(days=cdkey.duration_days)

            user.is_vip = True

            # 如果是被邀请用户且首次成为VIP，给邀请人加VIP奖励积分
            if not was_vip:
                add_inviter_vip_reward(session, user.id, 20)

            # 更新卡密状态
            cdkey.is_used = True
            cdkey.used_at = utc_plus_8()
            cdkey.used_by = current_user['id']

            session.commit()

            logger.info(f"用户 {user.username} 兑换卡密成功，获得 {cdkey.duration_days} 天会员")

            return {
                "code": 0,
                "message": "兑换成功",
                "data": {
                    "duration_days": cdkey.duration_days,
                    "expire_at": format_datetime(user.vip_expire_at),
                }
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"卡密兑换失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/vip/status")
def get_vip_status(req: Request = None, current_user = Depends(get_current_user)):
    """获取用户VIP状态"""
    try:
        from models import User, get_session, format_datetime, UserVipPlan, VipPlan

        # 检查用户是否登录
        if not current_user:
            raise HTTPException(status_code=401, detail="未登录")

        with get_session() as session:
            user = session.query(User).filter(User.id == current_user['id']).first()

            from models import utc_plus_8
            is_expired = False
            remaining_days = 0

            if user.vip_expire_at:
                now = utc_plus_8()
                if user.vip_expire_at > now:
                    remaining_days = (user.vip_expire_at - now).days
                else:
                    is_expired = True
                    # 自动更新vip状态
                    user.is_vip = False
                    session.commit()

            # 获取用户已开通的套餐
            vip_plans = []
            user_plans = session.query(UserVipPlan).filter(
                UserVipPlan.user_id == user.id
            ).order_by(UserVipPlan.id.desc()).all()

            seen_plan_ids = set()
            for user_plan in user_plans:
                if user_plan.plan_id in seen_plan_ids:
                    continue
                seen_plan_ids.add(user_plan.plan_id)

                plan = session.query(VipPlan).filter(VipPlan.id == user_plan.plan_id).first()
                if plan:
                    vip_plans.append({
                        'id': user_plan.id,
                        'plan_id': plan.id,
                        'name': plan.name,
                        'terminal': user_plan.terminal,
                        'activated_at': format_datetime(user_plan.activated_at),
                        'expire_at': format_datetime(user_plan.expire_at)
                    })

            return {
                "code": 0,
                "message": "success",
                "data": {
                    "is_vip": user.is_vip,
                    "vip_expire_at": format_datetime(user.vip_expire_at),
                    "remaining_days": remaining_days,
                    "is_expired": is_expired,
                    "vip_plans": vip_plans
                }
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取VIP状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/vip/order")
def create_vip_order(data: OrderCreate, req: Request = None, current_user = Depends(get_current_user)):
    """创建VIP订单"""
    try:
        from models import Order, VipPlan, get_session
        from models import utc_plus_8
        import uuid

        with get_session() as session:
            # 查找套餐
            plan = session.query(VipPlan).filter(VipPlan.id == data.plan_id).first()
            if not plan or not plan.is_enabled:
                raise HTTPException(status_code=400, detail="套餐不存在或已下架")

            # 创建订单
            order_no = f"VIP{utc_plus_8().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:8].upper()}"

            order = Order(
                user_id=current_user['id'],
                order_no=order_no,
                plan_id=plan.id,
                plan_name=plan.name,
                amount=plan.price,
                pay_type='qrcode',
                pay_status='pending'
            )

            session.add(order)
            session.commit()
            session.refresh(order)

            logger.info(f"用户 {current_user['username']} 创建订单: {order_no}")

            return {
                "code": 0,
                "message": "success",
                "data": order.to_dict()
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建订单失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/vip/orders")
def get_my_vip_orders(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    req: Request = None,
    current_user = Depends(get_current_user)
):
    """获取我的VIP订单列表"""
    try:
        from models import Order, get_session

        with get_session() as session:
            query = session.query(Order).filter(Order.user_id == current_user['id'])
            total = query.count()
            offset = (page - 1) * limit
            orders = query.order_by(Order.id.desc()).offset(offset).limit(limit).all()

            return {
                "code": 0,
                "message": "success",
                "data": {
                    "items": [order.to_dict() for order in orders],
                    "total": total,
                    "page": page,
                    "limit": limit
                }
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取订单列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========== 卡密管理后台API ==========

@app.post("/admin-api/cdkeys")
def create_cdkeys(data: CdkeyBatchCreate, req: Request = None):
    """批量创建卡密"""
    try:
        from models import VipCdkey, VipPlan, get_session
        from models import utc_plus_8
        from datetime import timedelta
        import random
        import string

        with get_session() as session:
            # 查找套餐
            plan = session.query(VipPlan).filter(VipPlan.id == data.plan_id).first()
            if not plan:
                raise HTTPException(status_code=404, detail="套餐不存在")

            duration = data.duration_days or plan.duration_days

            created_cdkeys = []
            for _ in range(data.count):
                # 生成卡密
                code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=16))

                expired_at = None
                if data.expired_days:
                    expired_at = utc_plus_8() + timedelta(days=data.expired_days)

                cdkey = VipCdkey(
                    code=code,
                    plan_id=plan.id,
                    duration_days=duration,
                    expired_at=expired_at
                )

                session.add(cdkey)
                created_cdkeys.append(code)

            session.commit()

            logger.info(f"批量创建卡密 {data.count} 张，套餐: {plan.name}")

            return {
                "code": 0,
                "message": "success",
                "data": {
                    "count": len(created_cdkeys),
                    "codes": created_cdkeys
                }
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建卡密失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/admin-api/cdkeys")
def list_cdkeys(
    plan_id: Optional[int] = Query(None, description="套餐ID"),
    is_used: Optional[bool] = Query(None, description="是否已使用"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    req: Request = None
):
    """获取卡密列表"""
    try:
        from models import VipCdkey, get_session

        with get_session() as session:
            query = session.query(VipCdkey)

            if plan_id is not None:
                query = query.filter(VipCdkey.plan_id == plan_id)
            if is_used is not None:
                query = query.filter(VipCdkey.is_used == is_used)

            total = query.count()
            offset = (page - 1) * limit
            cdkeys = query.order_by(VipCdkey.id.desc()).offset(offset).limit(limit).all()

            return {
                "code": 0,
                "message": "success",
                "data": {
                    "items": [cdkey.to_dict() for cdkey in cdkeys],
                    "total": total,
                    "page": page,
                    "limit": limit
                }
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取卡密列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/admin-api/orders")
def list_orders(
    user_id: Optional[int] = Query(None, description="用户ID"),
    pay_status: Optional[str] = Query(None, description="支付状态"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    req: Request = None
):
    """获取订单列表"""
    try:
        from models import Order, get_session

        with get_session() as session:
            query = session.query(Order)

            if user_id is not None:
                query = query.filter(Order.user_id == user_id)
            if pay_status:
                query = query.filter(Order.pay_status == pay_status)

            total = query.count()
            offset = (page - 1) * limit
            orders = query.order_by(Order.id.desc()).offset(offset).limit(limit).all()

            return {
                "code": 0,
                "message": "success",
                "data": {
                    "items": [order.to_dict() for order in orders],
                    "total": total,
                    "page": page,
                    "limit": limit
                }
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取订单列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/admin-api/vip-plans")
def list_vip_plans(
    is_enabled: Optional[bool] = Query(None, description="是否启用"),
    plan_type: Optional[str] = Query(None, description="套餐类型：promotion-优惠期，formal-正式"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100)
):
    """获取会员套餐列表"""
    try:
        from models import VipPlan, get_session
        with get_session() as session:
            query = session.query(VipPlan)
            if is_enabled is not None:
                query = query.filter(VipPlan.is_enabled == is_enabled)
            if plan_type:
                query = query.filter(VipPlan.plan_type == plan_type)
            total = query.count()
            offset = (page - 1) * limit
            plans = query.order_by(VipPlan.sort_order.asc(), VipPlan.id.asc()).offset(offset).limit(limit).all()
            return {
                "code": 0,
                "message": "success",
                "data": {
                    "items": [plan.to_dict() for plan in plans],
                    "total": total,
                    "page": page,
                    "limit": limit
                }
            }
    except Exception as e:
        logger.error(f"获取会员套餐列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/admin-api/vip-plans/{plan_id}")
def get_vip_plan(plan_id: int):
    """获取单个会员套餐详情"""
    try:
        from models import VipPlan, get_session
        with get_session() as session:
            plan = session.query(VipPlan).filter(VipPlan.id == plan_id).first()
            if not plan:
                raise HTTPException(status_code=404, detail="套餐不存在")
            return {
                "code": 0,
                "message": "success",
                "data": plan.to_dict()
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取会员套餐详情失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/admin-api/vip-plans")
def create_vip_plan(data: VipPlanCreate):
    """创建会员套餐"""
    try:
        from models import VipPlan, get_session
        from models import utc_plus_8
        with get_session() as session:
            plan = VipPlan(**data.model_dump())
            session.add(plan)
            session.commit()
            session.refresh(plan)
            logger.info(f"创建会员套餐: {plan.name}")
            return {
                "code": 0,
                "message": "success",
                "data": plan.to_dict()
            }
    except Exception as e:
        logger.error(f"创建会员套餐失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/admin-api/vip-plans/{plan_id}")
def update_vip_plan(plan_id: int, data: VipPlanUpdate):
    """更新会员套餐"""
    try:
        from models import VipPlan, get_session
        with get_session() as session:
            plan = session.query(VipPlan).filter(VipPlan.id == plan_id).first()
            if not plan:
                raise HTTPException(status_code=404, detail="套餐不存在")

            update_data = data.model_dump(exclude_unset=True)
            for key, value in update_data.items():
                setattr(plan, key, value)

            session.commit()
            session.refresh(plan)
            logger.info(f"更新会员套餐: {plan.name}")
            return {
                "code": 0,
                "message": "success",
                "data": plan.to_dict()
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新会员套餐失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/admin-api/vip-plans/{plan_id}")
def delete_vip_plan(plan_id: int):
    """删除会员套餐"""
    try:
        from models import VipPlan, get_session
        with get_session() as session:
            plan = session.query(VipPlan).filter(VipPlan.id == plan_id).first()
            if not plan:
                raise HTTPException(status_code=404, detail="套餐不存在")

            session.delete(plan)
            logger.info(f"删除会员套餐: {plan.name}")
            return {
                "code": 0,
                "message": "success",
                "data": None
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除会员套餐失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============ VIP套餐配置管理 ============

class VipPlanConfigUpdate(BaseModel):
    plan_type: str
    tip_text: Optional[str] = None


@app.get("/admin-api/vip-plan-configs")
def list_vip_plan_configs():
    """获取VIP套餐配置列表"""
    try:
        from models import VipPlanConfig, get_session
        with get_session() as session:
            configs = session.query(VipPlanConfig).all()

            # 如果没有配置，初始化默认配置
            if not configs:
                for plan_type in ["promotion", "formal"]:
                    config = VipPlanConfig(
                        plan_type=plan_type,
                        tip_text=""
                    )
                    session.add(config)
                session.commit()
                configs = session.query(VipPlanConfig).all()

            return {
                "code": 0,
                "message": "success",
                "data": [config.to_dict() for config in configs]
            }
    except Exception as e:
        logger.error(f"获取VIP套餐配置列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/admin-api/vip-plan-configs")
def update_vip_plan_config(data: VipPlanConfigUpdate):
    """更新VIP套餐配置"""
    try:
        from models import VipPlanConfig, get_session
        from models import utc_plus_8
        with get_session() as session:
            config = session.query(VipPlanConfig).filter(
                VipPlanConfig.plan_type == data.plan_type
            ).first()

            if not config:
                config = VipPlanConfig(plan_type=data.plan_type)
                session.add(config)

            if data.tip_text is not None:
                config.tip_text = data.tip_text
            config.updated_at = utc_plus_8()

            session.commit()
            session.refresh(config)

            logger.info(f"更新VIP套餐配置: {data.plan_type}")
            return {
                "code": 0,
                "message": "success",
                "data": config.to_dict()
            }
    except Exception as e:
        logger.error(f"更新VIP套餐配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============ 批量启用/禁用套餐 ============

class BatchUpdateVipPlanStatusRequest(BaseModel):
    plan_ids: list[int]
    is_enabled: bool


@app.put("/admin-api/vip-plans/batch-update-status")
def batch_update_vip_plan_status(data: BatchUpdateVipPlanStatusRequest):
    """批量更新VIP套餐状态"""
    try:
        from models import VipPlan, get_session
        from models import utc_plus_8
        with get_session() as session:
            if not data.plan_ids:
                raise HTTPException(status_code=400, detail="请选择要更新的套餐")

            plans = session.query(VipPlan).filter(VipPlan.id.in_(data.plan_ids)).all()

            for plan in plans:
                plan.is_enabled = data.is_enabled
                plan.updated_at = utc_plus_8()

            session.commit()

            logger.info(f"批量更新VIP套餐状态: {data.plan_ids} -> {data.is_enabled}")
            return {
                "code": 0,
                "message": "success",
                "data": None
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"批量更新VIP套餐状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============ 支付二维码管理 ============

class PayQrcodeCreate(BaseModel):
    name: str
    type: Optional[str] = "wechat"
    image_url: str
    amount: Optional[float] = None
    description: Optional[str] = None
    is_enabled: Optional[bool] = True
    sort_order: Optional[int] = 0


class PayQrcodeUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    image_url: Optional[str] = None
    amount: Optional[float] = None
    description: Optional[str] = None
    is_enabled: Optional[bool] = None
    sort_order: Optional[int] = None


@app.get("/admin-api/payment-qrcodes")
def list_payment_qrcodes(
    qrcode_type: Optional[str] = Query(None, alias="type"),
    is_enabled: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100)
):
    """获取支付二维码列表"""
    try:
        from models import PayQrcode, get_session
        with get_session() as session:
            query = session.query(PayQrcode)
            if qrcode_type:
                query = query.filter(PayQrcode.type == qrcode_type)
            if is_enabled is not None:
                query = query.filter(PayQrcode.is_enabled == is_enabled)
            total = query.count()
            offset = (page - 1) * limit
            qrcodes = query.order_by(PayQrcode.sort_order.asc(), PayQrcode.id.asc()).offset(offset).limit(limit).all()
            return {
                "code": 0,
                "message": "success",
                "data": {
                    "items": [qrcode.to_dict() for qrcode in qrcodes],
                    "total": total,
                    "page": page,
                    "limit": limit
                }
            }
    except Exception as e:
        logger.error(f"获取支付二维码列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/admin-api/payment-qrcodes/{qrcode_id}")
def get_payment_qrcode(qrcode_id: int):
    """获取单个支付二维码详情"""
    try:
        from models import PayQrcode, get_session
        with get_session() as session:
            qrcode = session.query(PayQrcode).filter(PayQrcode.id == qrcode_id).first()
            if not qrcode:
                raise HTTPException(status_code=404, detail="二维码不存在")
            return {
                "code": 0,
                "message": "success",
                "data": qrcode.to_dict()
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取支付二维码详情失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/admin-api/payment-qrcodes")
def create_payment_qrcode(data: PayQrcodeCreate):
    """创建支付二维码"""
    try:
        from models import PayQrcode, get_session
        with get_session() as session:
            qrcode = PayQrcode(**data.model_dump())
            session.add(qrcode)
            session.commit()
            session.refresh(qrcode)
            logger.info(f"创建支付二维码: {qrcode.name}")
            return {
                "code": 0,
                "message": "success",
                "data": qrcode.to_dict()
            }
    except Exception as e:
        logger.error(f"创建支付二维码失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/admin-api/payment-qrcodes/{qrcode_id}")
def update_payment_qrcode(qrcode_id: int, data: PayQrcodeUpdate):
    """更新支付二维码"""
    try:
        from models import PayQrcode, get_session
        with get_session() as session:
            qrcode = session.query(PayQrcode).filter(PayQrcode.id == qrcode_id).first()
            if not qrcode:
                raise HTTPException(status_code=404, detail="二维码不存在")

            update_data = data.model_dump(exclude_unset=True)
            for key, value in update_data.items():
                setattr(qrcode, key, value)

            session.commit()
            session.refresh(qrcode)
            logger.info(f"更新支付二维码: {qrcode.name}")
            return {
                "code": 0,
                "message": "success",
                "data": qrcode.to_dict()
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新支付二维码失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/admin-api/payment-qrcodes/{qrcode_id}")
def delete_payment_qrcode(qrcode_id: int):
    """删除支付二维码"""
    try:
        from models import PayQrcode, get_session
        with get_session() as session:
            qrcode = session.query(PayQrcode).filter(PayQrcode.id == qrcode_id).first()
            if not qrcode:
                raise HTTPException(status_code=404, detail="二维码不存在")

            session.delete(qrcode)
            logger.info(f"删除支付二维码: {qrcode.name}")
            return {
                "code": 0,
                "message": "success",
                "data": None
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除支付二维码失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============ 卡密管理 ============

class VipCdkeyCreate(BaseModel):
    duration_days: int
    plan_id: Optional[int] = None
    count: Optional[int] = 1
    expired_days: Optional[int] = 365


class VipCdkeyUse(BaseModel):
    code: str
    user_id: Optional[int] = None


@app.get("/admin-api/vip-cdkeys")
def list_vip_cdkeys(
    is_used: Optional[bool] = Query(None),
    plan_id: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100)
):
    """获取卡密列表"""
    try:
        from models import VipCdkey, get_session
        from sqlalchemy.orm import joinedload
        with get_session() as session:
            query = session.query(VipCdkey).options(joinedload(VipCdkey.plan))
            if is_used is not None:
                query = query.filter(VipCdkey.is_used == is_used)
            if plan_id:
                query = query.filter(VipCdkey.plan_id == plan_id)
            total = query.count()
            offset = (page - 1) * limit
            cdkeys = query.order_by(VipCdkey.created_at.desc()).offset(offset).limit(limit).all()
            return {
                "code": 0,
                "message": "success",
                "data": {
                    "items": [cdkey.to_dict() for cdkey in cdkeys],
                    "total": total,
                    "page": page,
                    "limit": limit
                }
            }
    except Exception as e:
        logger.error(f"获取卡密列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/admin-api/vip-cdkeys")
def create_vip_cdkeys(data: VipCdkeyCreate):
    """批量生成卡密"""
    import random
    import string
    try:
        from models import VipCdkey, get_session
        from models import utc_plus_8
        count = data.count or 1
        generated = []

        with get_session() as session:
            for _ in range(count):
                # 生成16位随机码
                code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=16))
                expired_at = utc_plus_8() + timedelta(days=data.expired_days) if data.expired_days else None
                cdkey = VipCdkey(
                    code=code,
                    plan_id=data.plan_id,
                    duration_days=data.duration_days,
                    expired_at=expired_at
                )
                session.add(cdkey)
                generated.append(cdkey)

            session.commit()
            for cdkey in generated:
                session.refresh(cdkey)

            logger.info(f"生成{len(generated)}张VIP卡密")
            return {
                "code": 0,
                "message": "success",
                "data": {
                    "items": [cdkey.to_dict() for cdkey in generated],
                    "count": len(generated)
                }
            }
    except Exception as e:
        logger.error(f"生成卡密失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/admin-api/vip-cdkeys/{cdkey_id}")
def delete_vip_cdkey(cdkey_id: int):
    """删除卡密"""
    try:
        from models import VipCdkey, get_session
        with get_session() as session:
            cdkey = session.query(VipCdkey).filter(VipCdkey.id == cdkey_id).first()
            if not cdkey:
                raise HTTPException(status_code=404, detail="卡密不存在")

            session.delete(cdkey)
            logger.info(f"删除VIP卡密: {cdkey.code}")
            return {
                "code": 0,
                "message": "success",
                "data": None
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除卡密失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============ 客户端API（VIP相关） ============

@app.get("/api/vip/plans")
def client_list_vip_plans():
    """客户端：获取启用的会员套餐列表"""
    try:
        from models import VipPlan, VipPlanConfig, get_session
        with get_session() as session:
            plans = session.query(VipPlan).filter(VipPlan.is_enabled == True).order_by(VipPlan.sort_order.asc(), VipPlan.id.asc()).all()

            # 查询所有配置
            configs = session.query(VipPlanConfig).all()

            return {
                "code": 0,
                "message": "success",
                "data": {
                    "plans": [plan.to_dict() for plan in plans],
                    "configs": {
                        config.plan_type: config.to_dict()
                        for config in configs
                    }
                }
            }
    except Exception as e:
        logger.error(f"客户端获取套餐列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/vip/qrcodes")
def client_list_payment_qrcodes():
    """客户端：获取启用的支付二维码列表"""
    try:
        from models import PayQrcode, get_session
        with get_session() as session:
            qrcodes = session.query(PayQrcode).filter(PayQrcode.is_enabled == True).order_by(PayQrcode.sort_order.asc(), PayQrcode.id.asc()).all()
            return {
                "code": 0,
                "message": "success",
                "data": [qrcode.to_dict() for qrcode in qrcodes]
            }
    except Exception as e:
        logger.error(f"客户端获取支付二维码失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/vip/cdkey/exchange")
def client_exchange_cdkey(data: VipCdkeyUse, user_id: int = Query(..., ge=1)):
    """客户端：卡密兑换"""
    try:
        from models import VipCdkey, User, get_session, format_datetime
        from models import utc_plus_8
        with get_session() as session:
            # 查找卡密
            cdkey = session.query(VipCdkey).filter(VipCdkey.code == data.code).first()
            if not cdkey:
                raise HTTPException(status_code=404, detail="卡密不存在")

            if cdkey.is_used:
                raise HTTPException(status_code=400, detail="卡密已使用")

            if cdkey.expired_at and cdkey.expired_at < utc_plus_8():
                raise HTTPException(status_code=400, detail="卡密已过期")

            # 查找用户
            user = session.query(User).filter(User.id == user_id).first()
            if not user:
                raise HTTPException(status_code=404, detail="用户不存在")

            # 计算新的到期时间
            now = utc_plus_8()
            if user.is_vip and user.vip_expire_at and user.vip_expire_at > now:
                # 已有VIP，在原基础上延长
                new_expire_at = user.vip_expire_at + timedelta(days=cdkey.duration_days)
            else:
                # 新开通或已过期
                new_expire_at = now + timedelta(days=cdkey.duration_days)

            # 更新用户
            was_vip = user.is_vip  # 记录之前是否是VIP
            user.is_vip = True
            user.vip_expire_at = new_expire_at

            # 如果是被邀请用户且首次成为VIP，给邀请人加奖励积分
            if not was_vip:
                add_inviter_vip_reward(session, user.id, 20)

            # 标记卡密已使用
            cdkey.is_used = True
            cdkey.used_at = now
            cdkey.used_by = user.id

            logger.info(f"用户{user.username}兑换卡密{cdkey.code}，获得{cdkey.duration_days}天VIP")

            return {
                "code": 0,
                "message": "success",
                "data": {
                    "expire_at": format_datetime(user.vip_expire_at),
                    "duration_days": cdkey.duration_days
                }
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"卡密兑换失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 批量导入和模板下载 API ====================

import io
import csv
import urllib.parse
from datetime import datetime
from fastapi.responses import StreamingResponse
from models import User


def make_content_disposition(filename):
    """生成RFC 5987兼容的Content-Disposition头部"""
    quoted = urllib.parse.quote(filename, safe='')
    return f'attachment; filename*=UTF-8\'\'{quoted}'


# 解析源模板和批量导入
@app.get("/admin-api/parse-sources/template")
def download_parse_source_template():
    """下载解析源导入模板"""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['platform_id', 'key', 'name', 'type', 'url', 'sort_order'])
    writer.writerow(['', 'example1', '示例解析源1', 'json', 'https://example.com/parse', '0'])
    writer.writerow(['2', 'example2', '示例解析源2', 'json', 'https://example.com/parse2', '1'])

    output.seek(0)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode('utf-8-sig')),
        media_type='text/csv',
        headers={'Content-Disposition': make_content_disposition('parse_sources_template.csv')}
    )


@app.post("/admin-api/parse-sources/batch-import")
async def batch_import_parse_sources(file: UploadFile = File(...)):
    """批量导入解析源"""
    try:
        content = await file.read()

        # 尝试多种编码格式解码
        text_content = None
        encodings = ['utf-8-sig', 'gbk', 'gb2312', 'gb18030']
        for encoding in encodings:
            try:
                text_content = content.decode(encoding)
                break
            except UnicodeDecodeError:
                continue

        if text_content is None:
            raise HTTPException(status_code=400, detail="无法解析文件编码，请确保文件为 UTF-8 或 GBK 编码")

        reader = csv.DictReader(io.StringIO(text_content))
        count = 0
        errors = []

        for row in reader:
            try:
                # platform_id 为空时设为 None
                platform_id_str = row.get('platform_id', '').strip()
                platform_id = int(platform_id_str) if platform_id_str else None

                DatabaseManager.create_parse_source(
                    key=row['key'],
                    name=row['name'],
                    url=row['url'],
                    sort_order=int(row.get('sort_order', 0)),
                    platform_id=platform_id,
                    type=row.get('type', 'json')
                )
                count += 1
            except Exception as e:
                errors.append(f"行 {reader.line_num}: {str(e)}")

        return {
            "code": 0,
            "message": f"成功导入 {count} 个解析源" + (f"，错误: {len(errors)}" if errors else ""),
            "data": {"imported": count, "errors": errors}
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"批量导入解析源失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# 频道模板和批量导入
@app.get("/admin-api/channels/template")
def download_channel_template():
    """下载频道导入模板"""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['name', 'key', 'sort_order'])
    writer.writerow(['电视剧', 'tv', '0'])
    writer.writerow(['电影', 'movie', '1'])

    output.seek(0)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode('utf-8-sig')),
        media_type='text/csv',
        headers={'Content-Disposition': make_content_disposition('channels_template.csv')}
    )


@app.post("/admin-api/channels/batch-import")
async def batch_import_channels(file: UploadFile = File(...)):
    """批量导入频道"""
    try:
        content = await file.read()

        # 尝试多种编码格式解码
        text_content = None
        encodings = ['utf-8-sig', 'gbk', 'gb2312', 'gb18030']
        for encoding in encodings:
            try:
                text_content = content.decode(encoding)
                break
            except UnicodeDecodeError:
                continue

        if text_content is None:
            raise HTTPException(status_code=400, detail="无法解析文件编码，请确保文件为 UTF-8 或 GBK 编码")

        reader = csv.DictReader(io.StringIO(text_content))
        count = 0
        errors = []

        for row in reader:
            try:
                DatabaseManager.create_category(
                    name=row['name'],
                    key=row['key'],
                    sort_order=int(row.get('sort_order', 0))
                )
                count += 1
            except Exception as e:
                errors.append(f"行 {reader.line_num}: {str(e)}")

        return {
            "code": 0,
            "message": f"成功导入 {count} 个频道" + (f"，错误: {len(errors)}" if errors else ""),
            "data": {"imported": count, "errors": errors}
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"批量导入频道失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# 平台频道批量导入
@app.get("/admin-api/platforms-v2/{platform_id}/channels/template")
def download_platform_channel_template(platform_id: int):
    """下载平台频道导入模板"""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['category_id', 'channel_key', 'channel_name', 'url', 'output_table', 'channel_id', 'sort_order', 'enabled'])
    writer.writerow(['1', 'tv', '电视剧', 'https://example.com/tv', 'series', '', '0', '1'])
    writer.writerow(['2', 'movie', '电影', 'https://example.com/movie', 'series', '', '1', '1'])

    output.seek(0)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode('utf-8-sig')),
        media_type='text/csv',
        headers={'Content-Disposition': make_content_disposition('platform_channels_template.csv')}
    )


@app.get("/admin-api/platforms-v2/{platform_id}/channels/batch-import")
def get_platform_channels_batch_import(platform_id: int):
    """获取平台频道批量导入页面/模板下载"""
    # 重定向到模板下载
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url=f"/admin-api/platforms-v2/{platform_id}/channels/template")


@app.post("/admin-api/platforms-v2/{platform_id}/channels/batch-import")
async def batch_import_platform_channels(platform_id: int, file: UploadFile = File(...)):
    """批量导入平台频道"""
    try:
        content = await file.read()

        # 尝试多种编码格式解码
        text_content = None
        encodings = ['utf-8-sig', 'gbk', 'gb2312', 'gb18030']
        for encoding in encodings:
            try:
                text_content = content.decode(encoding)
                break
            except UnicodeDecodeError:
                continue

        if text_content is None:
            raise HTTPException(status_code=400, detail="无法解析文件编码，请确保文件为 UTF-8 或 GBK 编码")

        reader = csv.DictReader(io.StringIO(text_content))
        count = 0
        errors = []

        for row in reader:
            try:
                category_id = int(row.get('category_id')) if row.get('category_id') else 1
                DatabaseManager.create_platform_channel(
                    platform_id=platform_id,
                    category_id=category_id,
                    channel_key=row['channel_key'],
                    channel_name=row['channel_name'],
                    url=row['url'],
                    output_table=row.get('output_table', 'series'),
                    channel_id=row.get('channel_id'),
                    sort_order=int(row.get('sort_order', 0)),
                    enabled=row.get('enabled', '1') == '1'
                )
                count += 1
            except Exception as e:
                errors.append(f"行 {reader.line_num}: {str(e)}")

        return {
            "code": 0,
            "message": f"成功导入 {count} 个平台频道" + (f"，错误: {len(errors)}" if errors else ""),
            "data": {"imported": count, "errors": errors}
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"批量导入平台频道失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# 关键词批量操作
@app.delete("/admin-api/platforms-v2/{platform_id}/keywords")
def clear_platform_keywords(platform_id: int):
    """清空平台关键词"""
    try:
        empty_keywords = {"positive": [], "trailer": [], "bts": [], "vip": [], "completed": [], "ongoing": []}
        result = DatabaseManager.update_platform(platform_id, {"keywords": empty_keywords})
        if not result:
            raise HTTPException(status_code=404, detail="平台不存在")
        return {"code": 0, "message": "清空关键词成功"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"清空平台关键词失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class KeywordsBatchAdd(BaseModel):
    type: str  # positive, trailer, bts, vip, completed, ongoing
    keywords: str  # 逗号分隔的关键词字符串


@app.post("/admin-api/platforms-v2/{platform_id}/keywords/batch-add")
def batch_add_keywords(platform_id: int, data: KeywordsBatchAdd):
    """批量添加关键词"""
    from models import AdminPlatform, get_session
    try:
        with get_session() as session:
            platform = session.query(AdminPlatform).filter(AdminPlatform.id == platform_id).first()
            if not platform:
                raise HTTPException(status_code=404, detail="平台不存在")

            # 解析现有关键词
            existing_keywords = {}
            if platform.keywords:
                try:
                    existing_keywords = json.loads(platform.keywords)
                except:
                    pass

            # 确保所有分类都存在
            for key_type in ['positive', 'trailer', 'bts', 'vip', 'completed', 'ongoing']:
                if key_type not in existing_keywords:
                    existing_keywords[key_type] = []

            # 分割新关键词
            new_keywords = [k.strip() for k in data.keywords.split(',') if k.strip()]

            # 添加到指定分类
            added_count = 0
            for kw in new_keywords:
                if kw not in existing_keywords[data.type]:
                    existing_keywords[data.type].append(kw)
                    added_count += 1

            # 更新数据库
            platform.keywords = json.dumps(existing_keywords, ensure_ascii=False)
            session.flush()

            return {
                "code": 0,
                "message": f"成功添加 {added_count} 个关键词",
                "data": {"added": added_count}
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"批量添加关键词失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# 会员套餐模板和批量导入
@app.get("/admin-api/vip-plans/template")
def download_vip_plan_template():
    """下载会员套餐导入模板"""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['name', 'price', 'original_price', 'duration_days', 'unit', 'save_amount', 'is_recommend', 'is_enabled', 'sort_order', 'plan_type', 'duration_type', 'devices'])
    writer.writerow(['月度VIP', '19.9', '29.9', '30', '月度会员', '10', '0', '1', '0', 'formal', 'monthly', 'pc,mobile,tv'])
    writer.writerow(['年度VIP', '149.0', '199.0', '365', '年度会员', '50', '1', '1', '1', 'formal', 'yearly', 'pc,mobile,tv'])

    output.seek(0)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode('utf-8-sig')),
        media_type='text/csv',
        headers={'Content-Disposition': make_content_disposition('vip_plans_template.csv')}
    )


@app.post("/admin-api/vip-plans/batch-import")
async def batch_import_vip_plans(file: UploadFile = File(...)):
    """批量导入会员套餐"""
    try:
        from models import VipPlan, get_session
        content = await file.read()

        # 尝试多种编码格式解码
        text_content = None
        encodings = ['utf-8-sig', 'gbk', 'gb2312', 'gb18030']
        for encoding in encodings:
            try:
                text_content = content.decode(encoding)
                break
            except UnicodeDecodeError:
                continue

        if text_content is None:
            raise HTTPException(status_code=400, detail="无法解析文件编码，请确保文件为 UTF-8 或 GBK 编码")

        reader = csv.DictReader(io.StringIO(text_content))
        count = 0
        errors = []

        with get_session() as session:
            for row in reader:
                try:
                    plan = VipPlan(
                        name=row['name'],
                        price=float(row['price']),
                        original_price=float(row['original_price']) if row.get('original_price') else None,
                        duration_days=int(row['duration_days']),
                        unit=row.get('unit', ''),
                        save_amount=float(row['save_amount']) if row.get('save_amount') else 0,
                        is_recommend=row.get('is_recommend', '0') == '1',
                        is_enabled=row.get('is_enabled', '1') == '1',
                        sort_order=int(row.get('sort_order', 0)),
                        plan_type=row.get('plan_type', 'formal'),
                        duration_type=row.get('duration_type', 'monthly'),
                        devices=row.get('devices', 'pc')
                    )
                    session.add(plan)
                    count += 1
                except Exception as e:
                    errors.append(f"行 {reader.line_num}: {str(e)}")

            session.commit()

        return {
            "code": 0,
            "message": f"成功导入 {count} 个会员套餐" + (f"，错误: {len(errors)}" if errors else ""),
            "data": {"imported": count, "errors": errors}
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"批量导入会员套餐失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# 用户管理导入导出
@app.get("/admin-api/users/template")
def download_user_template():
    """下载用户导入模板"""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['username', 'phone', 'nickname', 'password', 'email', 'status', 'is_vip', 'vip_expire_at'])
    writer.writerow(['testuser1', '13800138001', '测试用户1', '123456', '', 'active', '0', ''])
    writer.writerow(['testuser2', '13800138002', '测试用户2', '123456', 'test@example.com', 'active', '1', '2025-12-31 23:59:59'])

    output.seek(0)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode('utf-8-sig')),
        media_type='text/csv',
        headers={'Content-Disposition': make_content_disposition('users_template.csv')}
    )


@app.get("/admin-api/users/export")
def export_users(
    keyword: Optional[str] = None,
    status: Optional[str] = None,
    invited_by: Optional[str] = None
):
    """导出用户数据"""
    try:
        from models import get_session

        # 转换 invited_by 为整数或 None
        invited_by_int = None
        if invited_by and invited_by.strip():
            try:
                invited_by_int = int(invited_by.strip())
            except ValueError:
                pass

        with get_session() as session:
            query = session.query(User)

            if keyword:
                keyword_like = f'%{keyword}%'
                query = query.filter(
                    (User.username.like(keyword_like)) |
                    (User.phone.like(keyword_like)) |
                    (User.nickname.like(keyword_like))
                )

            if status:
                query = query.filter(User.status == status)

            if invited_by_int:
                query = query.filter(User.invited_by == invited_by_int)

            users = query.order_by(User.created_at.desc()).all()

            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(['ID', '用户名', '手机号', '昵称', '邮箱', '状态', '是否VIP', 'VIP到期时间', '注册时间'])

            for user in users:
                from models import utc_plus_8
                vip_text = '是' if (user.is_vip and user.vip_expire_at and user.vip_expire_at > utc_plus_8()) else '否'
                status_text = '正常' if user.status == 'active' else '禁用'
                writer.writerow([
                    user.id,
                    user.username,
                    user.phone,
                    user.nickname or '',
                    user.email or '',
                    status_text,
                    vip_text,
                    format_datetime(user.vip_expire_at) or '',
                    format_datetime(user.created_at)
                ])

            output.seek(0)
            return StreamingResponse(
                io.BytesIO(output.getvalue().encode('utf-8-sig')),
                media_type='text/csv',
                headers={'Content-Disposition': make_content_disposition(f'users_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv')}
            )
    except Exception as e:
        logger.error(f"导出用户失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/admin-api/users/batch-import")
async def batch_import_users(file: UploadFile = File(...)):
    """批量导入用户"""
    try:
        from models import get_session
        from werkzeug.security import generate_password_hash
        import hashlib

        content = await file.read()
        reader = csv.DictReader(io.StringIO(content.decode('utf-8-sig')))
        count = 0
        errors = []

        with get_session() as session:
            for row in reader:
                try:
                    # 检查必填字段
                    username = row.get('username', '').strip()
                    phone = row.get('phone', '').strip()
                    if not username or not phone:
                        errors.append(f"行 {reader.line_num}: 用户名和手机号必填")
                        continue

                    # 检查是否已存在
                    existing = session.query(User).filter(
                        (User.username == username) | (User.phone == phone)
                    ).first()
                    if existing:
                        errors.append(f"行 {reader.line_num}: 用户名或手机号已存在")
                        continue

                    # 创建用户
                    password = row.get('password', '').strip()
                    if not password:
                        password = '123456'

                    # 密码哈希
                    import hashlib
                    m = hashlib.sha256()
                    m.update(password.encode('utf-8'))
                    password_hash = m.hexdigest()

                    user = User(
                        username=username,
                        phone=phone,
                        nickname=row.get('nickname', ''),
                        email=row.get('email', ''),
                        password_hash=password_hash,
                        status=row.get('status', 'active'),
                        is_vip=row.get('is_vip', '0') == '1'
                    )

                    # 处理VIP到期时间
                    vip_expire_at_str = row.get('vip_expire_at', '')
                    if vip_expire_at_str:
                        try:
                            from datetime import datetime
                            user.vip_expire_at = datetime.strptime(vip_expire_at_str, '%Y-%m-%d %H:%M:%S')
                        except:
                            pass

                    session.add(user)
                    count += 1
                except Exception as e:
                    errors.append(f"行 {reader.line_num}: {str(e)}")

            session.commit()

        return {
            "code": 0,
            "message": f"成功导入 {count} 个用户" + (f"，错误: {len(errors)}" if errors else ""),
            "data": {"imported": count, "errors": errors}
        }
    except Exception as e:
        logger.error(f"批量导入用户失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# 挂载管理后台静态文件（必须在前端根路径之前）
_admin_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'admin', 'dist')
if os.path.isdir(_admin_path):
    app.mount("/admin", StaticFiles(directory=_admin_path, html=True), name="admin")

# 挂载前端静态文件（必须在所有API路由之后）
_frontend_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'client', 'dist')
if os.path.isdir(_frontend_path):
    app.mount("/", StaticFiles(directory=_frontend_path, html=True), name="frontend")


if __name__ == '__main__':
    import os
    import uvicorn
    # 禁用彩色输出，避免Windows CMD乱码
    os.environ['NO_COLOR'] = '1'

    # 初始化数据库，确保新表创建
    from models import init_db
    init_db()

    # 初始化默认管理员账号
    init_default_admin()

    # 暂时注释掉，测试启动问题
    # 初始化日志处理器
    # from core.log_stream import get_memory_log_handler
    # log_handler = get_memory_log_handler()
    # logger.info("日志处理器初始化完成")

    # 初始化任务调度器（多进程版本）
    from core.config import Config
    from core.task_scheduler import get_scheduler
    config = Config()

    crawl_scheduler = get_scheduler(platform_max=2)
    crawl_scheduler.initialize(
        db_path=config.db_path
    )
    crawl_scheduler.start()
    logger.info("任务调度器初始化完成: 平台并发=2, 全局并发将动态计算")

    logger.info("启动 VBox API 服务...")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_config={
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'default': {
                '()': 'uvicorn.logging.DefaultFormatter',
                'fmt': '%(levelprefix)s %(message)s',
                'use_colors': False,
            },
            'access': {
                '()': 'uvicorn.logging.AccessFormatter',
                'fmt': '%(levelprefix)s %(client_addr)s - "%(request_line)s" %(status_code)s',
                'use_colors': False,
            },
        },
        'handlers': {
            'default': {
                'formatter': 'default',
                'class': 'logging.StreamHandler',
                'stream': 'ext://sys.stderr',
            },
            'access': {
                'formatter': 'access',
                'class': 'logging.StreamHandler',
                'stream': 'ext://sys.stdout',
            },
        },
        'loggers': {
            'uvicorn': {'handlers': ['default'], 'level': 'INFO'},
            'uvicorn.error': {'level': 'INFO'},
            'uvicorn.access': {'handlers': ['access'], 'level': 'INFO', 'propagate': False},
        },
    })
