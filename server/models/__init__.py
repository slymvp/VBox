"""
数据模型定义
使用 SQLAlchemy ORM 提供数据库抽象层

核心架构：以频道（Category）为大类，每个频道独立表
表名规范：前缀标识大类
- video_*     视频相关（按频道分表）
- user_*      用户相关
- vip_*       会员相关
- pay_*       支付相关
- task_*      任务/爬取相关
- admin_*     管理端相关
"""
from datetime import datetime, timedelta
from contextlib import contextmanager
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, Text, DateTime, ForeignKey, Index
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from sqlalchemy import text
import os
import json

Base = declarative_base()


def utc_plus_8() -> datetime:
    """获取 UTC+8 时区的当前时间（只到秒级）"""
    now = datetime.utcnow() + timedelta(hours=8)
    return now.replace(microsecond=0)


def format_datetime(dt: datetime) -> str:
    """将时间格式化为 UTC+8 时区的24小时格式：YYYY-MM-DD HH:MM:SS"""
    if not dt:
        return None
    return dt.strftime('%Y-%m-%d %H:%M:%S')


# ==================== 频道配置 ====================

CATEGORY_KEYS = ['tv', 'movie', 'variety', 'cartoon', 'child', 'free']


def get_video_table_name(category_key: str) -> str:
    """获取频道对应的剧集表名，如 video_tv"""
    return f'video_{category_key}'


def get_video_ep_table_name(category_key: str) -> str:
    """获取频道对应的分集表名，如 video_tv_ep"""
    return f'video_{category_key}_ep'


# ==================== 动态模型工厂 ====================

_video_models = {}
_video_ep_models = {}


def _create_video_model(category_key: str):
    """动态创建频道剧集模型"""
    table_name = get_video_table_name(category_key)

    attrs = {
        '__tablename__': table_name,
        'id': Column(Integer, primary_key=True, autoincrement=True),
        'platform': Column(String(50), nullable=False, comment='平台：iqiyi, tencent'),
        'cid': Column(String(100), unique=True, nullable=False, index=True, comment='剧集ID'),
        'title': Column(String(500), nullable=False, comment='剧名'),
        'url': Column(Text, comment='播放页URL'),
        'first_vid': Column(String(100), comment='首集VID'),
        'area': Column(String(100), comment='地区'),
        'year': Column(String(20), comment='年份'),
        'score': Column(Float, comment='评分'),
        'tags': Column(Text, comment='标签（JSON数组字符串）'),
        'thumbnail': Column(Text, comment='缩略图URL'),
        'cover_url': Column(Text, comment='封面URL'),
        'description': Column(Text, comment='简介'),
        'actors': Column(Text, comment='演员列表（JSON数组字符串）'),
        'director': Column(Text, comment='导演列表（JSON数组字符串）'),
        'total_episodes': Column(Integer, default=0, comment='总集数'),
        'updated_episodes': Column(Integer, default=0, comment='已更新集数'),
        'is_vip': Column(Integer, default=0, comment='是否VIP：0-免费，1-会员，2-点播'),
        'is_hot': Column(Integer, default=0, comment='是否最热：0-否，1-是'),
        'is_new': Column(Integer, default=0, comment='是否最新：0-否，1-是'),
        'is_finished': Column(Integer, default=0, comment='完结状态：-1 未完结/连载中，0 未知，1 已完结'),
        'created_at': Column(DateTime, default=utc_plus_8, comment='创建时间'),
        'updated_at': Column(DateTime, default=utc_plus_8, onupdate=utc_plus_8, comment='更新时间'),
        '__table_args__': (
            Index(f'idx_{table_name}_platform', 'platform'),
            Index(f'idx_{table_name}_updated', 'updated_at'),
            Index(f'idx_{table_name}_platform_updated', 'platform', 'updated_at'),
        ),
    }

    def to_dict(self):
        return {
            'id': self.id,
            'platform': self.platform,
            'cid': self.cid,
            'title': self.title,
            'url': self.url,
            'first_vid': self.first_vid,
            'area': self.area,
            'year': self.year,
            'score': self.score,
            'tags': self.tags,
            'thumbnail': self.thumbnail,
            'cover_url': self.cover_url,
            'description': self.description,
            'actors': self.actors,
            'director': self.director,
            'total_episodes': self.total_episodes,
            'updated_episodes': self.updated_episodes,
            'is_vip': self.is_vip,
            'is_hot': self.is_hot,
            'is_new': self.is_new,
            'is_finished': self.is_finished,
            'created_at': format_datetime(self.created_at),
            'updated_at': format_datetime(self.updated_at),
        }

    attrs['to_dict'] = to_dict
    model = type(f'Video_{category_key}', (Base,), attrs)
    return model


def _create_video_ep_model(category_key: str):
    """动态创建频道分集模型"""
    table_name = get_video_ep_table_name(category_key)
    video_table = get_video_table_name(category_key)

    attrs = {
        '__tablename__': table_name,
        'id': Column(Integer, primary_key=True, autoincrement=True),
        'series_id': Column(Integer, ForeignKey(f'{video_table}.id', ondelete='CASCADE'), nullable=False, index=True, comment='关联剧集ID'),
        'episode_num': Column(String(50), nullable=False, comment='集号'),
        'vid': Column(String(100), comment='视频ID'),
        'play_title': Column(String(500), comment='播放标题'),
        'union_title': Column(String(500), comment='联合标题'),
        'episode_type': Column(Integer, default=0, comment='类型：0-正片，1-预告，2-花絮'),
        'duration': Column(String(50), comment='时长'),
        'publish_date': Column(String(50), comment='发布日期'),
        'is_vip': Column(Integer, default=0, comment='是否VIP：0-免费，1-会员，2-点播'),
        'play_url': Column(Text, comment='播放URL'),
        'created_at': Column(DateTime, default=utc_plus_8, comment='创建时间'),
        '__table_args__': (
            Index(f'idx_{table_name}_series', 'series_id'),
            Index(f'idx_{table_name}_vid', 'vid'),
            Index(f'idx_{table_name}_series_num_type', 'series_id', 'episode_num', 'episode_type'),
        ),
    }

    def to_dict(self):
        return {
            'id': self.id,
            'series_id': self.series_id,
            'episode_num': self.episode_num,
            'vid': self.vid,
            'play_title': self.play_title,
            'union_title': self.union_title,
            'episode_type': self.episode_type,
            'duration': self.duration,
            'publish_date': self.publish_date,
            'is_vip': self.is_vip,
            'play_url': self.play_url,
            'created_at': format_datetime(self.created_at),
        }

    attrs['to_dict'] = to_dict
    model = type(f'VideoEp_{category_key}', (Base,), attrs)
    return model


# 初始化所有频道模型，free 是虚拟频道，不需要独立表
for _key in CATEGORY_KEYS:
    if _key != 'free':
        _video_models[_key] = _create_video_model(_key)
        _video_ep_models[_key] = _create_video_ep_model(_key)


def get_video_model(category_key: str):
    """获取频道对应的剧集模型类"""
    if category_key == 'free':
        # free 是虚拟频道，默认使用 tv 的模型作为占位
        return _video_models.get('tv')
    if category_key not in _video_models:
        raise ValueError(f"不支持的频道类型: {category_key}, 支持: {list(_video_models.keys())}")
    return _video_models[category_key]


def get_video_ep_model(category_key: str):
    """获取频道对应的分集模型类"""
    if category_key == 'free':
        # free 是虚拟频道，默认使用 tv 的模型作为占位
        return _video_ep_models.get('tv')
    if category_key not in _video_ep_models:
        raise ValueError(f"不支持的频道类型: {category_key}, 支持: {list(_video_ep_models.keys())}")
    return _video_ep_models[category_key]


# ==================== 任务/爬取相关 ====================

class TaskCrawl(Base):
    """爬取任务记录表"""
    __tablename__ = 'task_crawl'

    id = Column(Integer, primary_key=True, autoincrement=True)
    platform = Column(String(50), nullable=False, comment='平台')
    channel = Column(String(50), nullable=False, comment='频道')
    status = Column(String(20), default='pending', comment='状态：pending, running, completed, failed')
    items_fetched = Column(Integer, default=0, comment='已获取数量')
    error_message = Column(Text, comment='错误信息')
    created_at = Column(DateTime, default=utc_plus_8, comment='创建时间')
    started_at = Column(DateTime, comment='开始时间')
    completed_at = Column(DateTime, comment='完成时间')

    __table_args__ = (
        Index('idx_task_crawl_status', 'status'),
    )

    def to_dict(self):
        result = {
            'id': self.id,
            'platform': self.platform,
            'channel': self.channel,
            'status': self.status,
            'items_fetched': self.items_fetched,
            'error_message': self.error_message,
            'started_at': format_datetime(self.started_at),
            'completed_at': format_datetime(self.completed_at),
        }
        if hasattr(self, 'created_at'):
            result['created_at'] = format_datetime(self.created_at)
        return result


class TaskCrawlLog(Base):
    """爬取任务日志表"""
    __tablename__ = 'task_crawl_log'

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, ForeignKey('task_crawl.id', ondelete='CASCADE'), nullable=False, index=True, comment='关联任务ID')
    level = Column(String(20), nullable=False, comment='日志级别：DEBUG, INFO, WARNING, ERROR')
    message = Column(Text, nullable=False, comment='日志内容')
    created_at = Column(DateTime, default=utc_plus_8, comment='创建时间')

    task = relationship("TaskCrawl")

    __table_args__ = (
        Index('idx_task_crawl_log_task', 'task_id'),
        Index('idx_task_crawl_log_level', 'level'),
        Index('idx_task_crawl_log_created', 'created_at'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'task_id': self.task_id,
            'level': self.level,
            'message': self.message,
            'created_at': format_datetime(self.created_at),
        }


class TaskSchedule(Base):
    """定时任务表"""
    __tablename__ = 'task_schedule'

    id = Column(Integer, primary_key=True, autoincrement=True)
    platform = Column(String(50), nullable=False, comment='平台')
    channel = Column(String(50), comment='频道（可选，单频道）')
    channels = Column(Text, comment='频道列表（JSON数组，多频道）')
    cron_expression = Column(String(100), nullable=False, comment='CRON表达式')
    sort = Column(String(20), default='', comment='排序类型: 空=默认, hot=热门, new=最新')
    enabled = Column(Boolean, default=True, comment='是否启用')
    last_run_at = Column(DateTime, comment='最后运行时间')
    next_run_at = Column(DateTime, comment='下次运行时间')
    description = Column(String(500), comment='任务描述')
    created_at = Column(DateTime, default=utc_plus_8, comment='创建时间')
    updated_at = Column(DateTime, default=utc_plus_8, onupdate=utc_plus_8, comment='更新时间')

    __table_args__ = (
        Index('idx_task_schedule_platform', 'platform'),
        Index('idx_task_schedule_enabled', 'enabled'),
    )

    def to_dict(self):
        channels_list = None
        if self.channels:
            try:
                channels_list = json.loads(self.channels)
            except Exception:
                pass
        return {
            'id': self.id,
            'platform': self.platform,
            'channel': self.channel,
            'channels': channels_list,
            'cron_expression': self.cron_expression,
            'sort': self.sort or '',
            'enabled': self.enabled,
            'last_run_at': format_datetime(self.last_run_at),
            'next_run_at': format_datetime(self.next_run_at),
            'description': self.description,
            'created_at': format_datetime(self.created_at),
            'updated_at': format_datetime(self.updated_at),
        }


# ==================== 用户相关 ====================

class User(Base):
    """用户表"""
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True, comment='用户名')
    phone = Column(String(20), unique=True, nullable=False, index=True, comment='手机号')
    email = Column(String(100), unique=True, index=True, comment='邮箱（可选）')
    password_hash = Column(String(255), comment='密码哈希（可选）')
    nickname = Column(String(100), comment='昵称')
    avatar = Column(String(500), comment='头像URL')
    status = Column(String(20), default='active', comment='状态：active, banned')
    is_vip = Column(Boolean, default=False, comment='是否为VIP会员')
    vip_expire_at = Column(DateTime, comment='VIP到期时间')
    invite_code = Column(String(20), unique=True, index=True, comment='邀请码')
    invited_by = Column(Integer, ForeignKey('user.id'), index=True, comment='邀请人ID')
    points = Column(Integer, default=0, comment='积分/余额')
    created_at = Column(DateTime, default=utc_plus_8, comment='注册时间')
    updated_at = Column(DateTime, default=utc_plus_8, onupdate=utc_plus_8, comment='更新时间')

    __table_args__ = (
        Index('idx_user_phone', 'phone'),
        Index('idx_user_username', 'username'),
        Index('idx_user_email', 'email'),
    )

    def to_dict(self, session=None):
        from models import utc_plus_8, UserVipPlan, VipPlan
        vip_status = 'vip' if (self.is_vip and self.vip_expire_at and self.vip_expire_at > utc_plus_8()) else 'normal'

        # 获取用户已激活的套餐（按plan_id去重，取最新记录）
        vip_plans = []
        try:
            # 如果传入了 session，复用它；否则创建新的
            if session:
                user_plans = session.query(UserVipPlan).filter(
                    UserVipPlan.user_id == self.id
                ).order_by(UserVipPlan.id.desc()).all()

                # 按plan_id去重
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
            else:
                # 无传入 session 时，创建临时 session
                with get_session() as s:
                    user_plans = s.query(UserVipPlan).filter(
                        UserVipPlan.user_id == self.id
                    ).order_by(UserVipPlan.id.desc()).all()

                    seen_plan_ids = set()
                    for user_plan in user_plans:
                        if user_plan.plan_id in seen_plan_ids:
                            continue
                        seen_plan_ids.add(user_plan.plan_id)

                        plan = s.query(VipPlan).filter(VipPlan.id == user_plan.plan_id).first()
                        if plan:
                            vip_plans.append({
                                'id': user_plan.id,
                                'plan_id': plan.id,
                                'name': plan.name,
                                'terminal': user_plan.terminal,
                                'activated_at': format_datetime(user_plan.activated_at),
                                'expire_at': format_datetime(user_plan.expire_at)
                            })
        except Exception:
            pass

        return {
            'id': self.id,
            'username': self.username,
            'phone': self.phone,
            'email': self.email,
            'nickname': self.nickname,
            'avatar': self.avatar,
            'status': self.status,
            'is_vip': self.is_vip,
            'vip_status': vip_status,
            'vip_expire_at': format_datetime(self.vip_expire_at),
            'vip_expire_time': format_datetime(self.vip_expire_at),
            'vip_plans': vip_plans,
            'invite_code': self.invite_code,
            'invited_by': self.invited_by,
            'points': self.points,
            'created_at': format_datetime(self.created_at),
            'updated_at': format_datetime(self.updated_at),
        }


class UserSmsCode(Base):
    """短信验证码表"""
    __tablename__ = 'user_sms_code'

    id = Column(Integer, primary_key=True, autoincrement=True)
    phone = Column(String(20), nullable=False, index=True, comment='手机号')
    code = Column(String(10), nullable=False, comment='验证码')
    code_type = Column(String(20), default='login', comment='类型：login, register, bind')
    used = Column(Boolean, default=False, comment='是否已使用')
    expire_at = Column(DateTime, nullable=False, comment='过期时间')
    created_at = Column(DateTime, default=utc_plus_8, comment='创建时间')

    __table_args__ = (
        Index('idx_user_sms_phone', 'phone'),
        Index('idx_user_sms_expire', 'expire_at'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'phone': self.phone,
            'code_type': self.code_type,
            'used': self.used,
            'expire_at': format_datetime(self.expire_at),
        }


class UserWatchHistory(Base):
    """观看历史表"""
    __tablename__ = 'user_watch_history'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('user.id', ondelete='CASCADE'), nullable=False, index=True, comment='用户ID')
    category_key = Column(String(20), nullable=False, default='tv', comment='频道标识：tv, movie, variety, cartoon, child')
    series_cid = Column(String(100), nullable=False, index=True, comment='剧集CID（跨频道表定位）')
    series_id = Column(Integer, nullable=False, index=True, comment='频道表内剧集ID')
    episode_id = Column(Integer, comment='频道表内分集ID')
    play_title = Column(String(500), nullable=True, comment='分集名称（冗余）')
    progress = Column(Integer, default=0, comment='观看进度（秒）')
    watch_time = Column(Integer, default=0, comment='累计观看时长（秒）')
    last_watched = Column(DateTime, default=utc_plus_8, comment='最后观看时间')
    created_at = Column(DateTime, default=utc_plus_8, comment='创建时间')

    __table_args__ = (
        Index('idx_user_watch_history_user', 'user_id'),
        Index('idx_user_watch_history_cid', 'series_cid'),
        Index('idx_user_watch_history_user_cid', 'user_id', 'series_cid'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'category_key': self.category_key,
            'series_cid': self.series_cid,
            'series_id': self.series_id,
            'episode_id': self.episode_id,
            'play_title': self.play_title,
            'progress': self.progress,
            'watch_time': self.watch_time,
            'last_watched': format_datetime(self.last_watched),
            'created_at': format_datetime(self.created_at),
        }


class UserFollow(Base):
    """追剧表"""
    __tablename__ = 'user_follow'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('user.id', ondelete='CASCADE'), nullable=False, index=True, comment='用户ID')
    category_key = Column(String(20), nullable=False, default='tv', comment='频道标识：tv, movie, variety, cartoon, child')
    series_cid = Column(String(100), nullable=False, index=True, comment='剧集CID（跨频道表定位）')
    series_id = Column(Integer, nullable=False, comment='频道表内剧集ID')
    follow_time = Column(DateTime, default=utc_plus_8, comment='订阅时间')
    last_check_time = Column(DateTime, default=utc_plus_8, comment='最后检查更新时间')
    last_episode_id = Column(Integer, comment='频道表内最后观看的分集ID')
    last_episode_num = Column(String(50), comment='最后观看的集数')

    __table_args__ = (
        Index('idx_user_follow_user', 'user_id'),
        Index('idx_user_follow_cid', 'series_cid'),
        Index('idx_user_follow_user_cid', 'user_id', 'series_cid', unique=True),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'category_key': self.category_key,
            'series_cid': self.series_cid,
            'series_id': self.series_id,
            'follow_time': format_datetime(self.follow_time),
            'last_check_time': format_datetime(self.last_check_time),
            'last_episode_id': self.last_episode_id,
            'last_episode_num': self.last_episode_num,
        }


class UserBookmark(Base):
    """收藏表"""
    __tablename__ = 'user_bookmark'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('user.id', ondelete='CASCADE'), nullable=False, index=True, comment='用户ID')
    category_key = Column(String(20), nullable=False, default='tv', comment='频道标识：tv, movie, variety, cartoon, child')
    series_cid = Column(String(100), nullable=False, index=True, comment='剧集CID（跨频道表定位）')
    series_id = Column(Integer, nullable=False, comment='频道表内剧集ID')
    created_at = Column(DateTime, default=utc_plus_8, comment='收藏时间')

    __table_args__ = (
        Index('idx_user_bookmark_user', 'user_id'),
        Index('idx_user_bookmark_cid', 'series_cid'),
        Index('idx_user_bookmark_user_cid', 'user_id', 'series_cid', unique=True),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'category_key': self.category_key,
            'series_cid': self.series_cid,
            'series_id': self.series_id,
            'created_at': format_datetime(self.created_at),
        }


class UserLog(Base):
    """用户操作日志表"""
    __tablename__ = 'user_log'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('user.id', ondelete='CASCADE'), nullable=True, index=True, comment='用户ID（游客为null）')
    action_type = Column(String(50), nullable=False, index=True, comment='操作类型：login, register, logout, password_reset, etc')
    action_detail = Column(Text, comment='操作详情（JSON）')
    ip_address = Column(String(50), comment='IP地址')
    user_agent = Column(Text, comment='User-Agent')
    status = Column(String(20), default='success', comment='状态：success, failed')
    created_at = Column(DateTime, default=utc_plus_8, comment='创建时间')

    __table_args__ = (
        Index('idx_user_log_user', 'user_id'),
        Index('idx_user_log_action', 'action_type'),
        Index('idx_user_log_time', 'created_at'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'action_type': self.action_type,
            'action_detail': self.action_detail,
            'ip_address': self.ip_address,
            'status': self.status,
            'created_at': format_datetime(self.created_at),
        }


# ==================== 会员/支付相关 ====================

class Order(Base):
    """订单表"""
    __tablename__ = 'orders'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False, index=True, comment='用户ID')
    order_no = Column(String(64), unique=True, nullable=False, index=True, comment='订单号')
    plan_id = Column(Integer, ForeignKey('vip_plan.id'), nullable=False, comment='套餐ID')
    plan_name = Column(String(100), comment='套餐名称快照')
    amount = Column(Float, nullable=False, comment='订单金额')
    pay_type = Column(String(20), default='qrcode', comment='支付方式: qrcode-扫码支付')
    pay_status = Column(String(20), default='pending', comment='支付状态: pending-待支付, paid-已支付, refund-已退款')
    pay_time = Column(DateTime, comment='支付时间')
    remark = Column(Text, comment='备注')
    created_at = Column(DateTime, default=utc_plus_8, comment='创建时间')
    updated_at = Column(DateTime, default=utc_plus_8, onupdate=utc_plus_8, comment='更新时间')
    
    plan = relationship("VipPlan")
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'order_no': self.order_no,
            'plan_id': self.plan_id,
            'plan_name': self.plan_name,
            'amount': self.amount,
            'pay_type': self.pay_type,
            'pay_status': self.pay_status,
            'pay_time': format_datetime(self.pay_time),
            'remark': self.remark,
            'created_at': format_datetime(self.created_at),
            'updated_at': format_datetime(self.updated_at),
        }


class VipPlan(Base):
    """会员套餐表"""
    __tablename__ = 'vip_plan'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, comment='套餐名称')
    price = Column(Float, nullable=False, comment='价格')
    original_price = Column(Float, comment='原价')
    duration_days = Column(Integer, nullable=False, comment='有效天数，0表示永久')
    unit = Column(String(100), comment='单位描述')
    save_amount = Column(Float, default=0, comment='节省金额')
    is_recommend = Column(Boolean, default=False, comment='是否推荐')
    is_enabled = Column(Boolean, default=True, comment='是否启用')
    sort_order = Column(Integer, default=0, comment='排序')
    plan_type = Column(String(20), default='formal', comment='套餐类型：promotion-优惠期，formal-正式')
    duration_type = Column(String(20), default='monthly', comment='时长类型：monthly-月度，quarterly-季度，yearly-年度，permanent-永久')
    devices = Column(String(100), default='pc', comment='支持的设备类型：pc-PC端，mobile-移动端，tv-TV端')
    created_at = Column(DateTime, default=utc_plus_8, comment='创建时间')
    updated_at = Column(DateTime, default=utc_plus_8, onupdate=utc_plus_8, comment='更新时间')

    __table_args__ = (
        Index('idx_vip_plan_enabled', 'is_enabled'),
        Index('idx_vip_plan_sort', 'sort_order'),
        Index('idx_vip_plan_type', 'plan_type'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'price': self.price,
            'original_price': self.original_price,
            'duration_days': self.duration_days,
            'unit': self.unit,
            'save_amount': self.save_amount,
            'is_recommend': self.is_recommend,
            'is_enabled': self.is_enabled,
            'sort_order': self.sort_order,
            'plan_type': self.plan_type,
            'duration_type': self.duration_type,
            'devices': self.devices,
            'created_at': format_datetime(self.created_at),
            'updated_at': format_datetime(self.updated_at),
        }


class UserVipPlan(Base):
    """用户套餐关联表"""
    __tablename__ = 'user_vip_plan'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('user.id', ondelete='CASCADE'), nullable=False, index=True, comment='用户ID')
    plan_id = Column(Integer, ForeignKey('vip_plan.id'), nullable=False, index=True, comment='套餐ID')
    terminal = Column(String(20), comment='激活终端：mobile-移动端，tv-TV端，pc-PC端')
    activated_at = Column(DateTime, default=utc_plus_8, comment='激活时间')
    expire_at = Column(DateTime, comment='到期时间')
    created_at = Column(DateTime, default=utc_plus_8, comment='创建时间')

    __table_args__ = (
        Index('idx_user_vip_plan_user', 'user_id'),
        Index('idx_user_vip_plan_plan', 'plan_id'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'plan_id': self.plan_id,
            'terminal': self.terminal,
            'activated_at': format_datetime(self.activated_at),
            'expire_at': format_datetime(self.expire_at),
            'created_at': format_datetime(self.created_at),
        }


class VipPlanConfig(Base):
    """会员套餐配置表"""
    __tablename__ = 'vip_plan_config'

    id = Column(Integer, primary_key=True, autoincrement=True)
    plan_type = Column(String(20), unique=True, nullable=False, comment='套餐类型：promotion-优惠期，formal-正式')
    tip_text = Column(Text, comment='提示语，显示在会员中心')
    created_at = Column(DateTime, default=utc_plus_8, comment='创建时间')
    updated_at = Column(DateTime, default=utc_plus_8, onupdate=utc_plus_8, comment='更新时间')

    __table_args__ = (
        Index('idx_vip_plan_config_type', 'plan_type'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'plan_type': self.plan_type,
            'tip_text': self.tip_text,
            'created_at': format_datetime(self.created_at),
            'updated_at': format_datetime(self.updated_at),
        }


class VipCdkey(Base):
    """VIP卡密表"""
    __tablename__ = 'vip_cdkey'

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(100), unique=True, nullable=False, index=True, comment='卡密')
    plan_id = Column(Integer, ForeignKey('vip_plan.id'), comment='关联套餐ID')
    duration_days = Column(Integer, nullable=False, comment='会员天数')
    is_used = Column(Boolean, default=False, comment='是否已使用')
    used_at = Column(DateTime, comment='使用时间')
    used_by = Column(Integer, ForeignKey('user.id'), comment='使用用户ID')
    created_at = Column(DateTime, default=utc_plus_8, comment='创建时间')
    expired_at = Column(DateTime, comment='卡密过期时间')

    plan = relationship("VipPlan")
    user = relationship("User")

    __table_args__ = (
        Index('idx_vip_cdkey_code', 'code'),
        Index('idx_vip_cdkey_used', 'is_used'),
        Index('idx_vip_cdkey_expired', 'expired_at'),
    )

    def to_dict(self):
        result = {
            'id': self.id,
            'code': self.code,
            'plan_id': self.plan_id,
            'duration_days': self.duration_days,
            'is_used': self.is_used,
            'used_at': format_datetime(self.used_at),
            'used_by': self.used_by,
            'created_at': format_datetime(self.created_at),
            'expired_at': format_datetime(self.expired_at),
        }
        if self.plan:
            result['plan_name'] = self.plan.name
        return result


class PayQrcode(Base):
    """支付二维码表"""
    __tablename__ = 'pay_qrcode'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, comment='名称')
    type = Column(String(50), nullable=False, default='wechat', comment='类型：wechat, alipay')
    image_url = Column(String(500), nullable=False, comment='二维码图片URL')
    amount = Column(Float, comment='固定金额，为空表示动态金额')
    description = Column(String(500), comment='说明')
    is_enabled = Column(Boolean, default=True, comment='是否启用')
    sort_order = Column(Integer, default=0, comment='排序')
    created_at = Column(DateTime, default=utc_plus_8, comment='创建时间')
    updated_at = Column(DateTime, default=utc_plus_8, onupdate=utc_plus_8, comment='更新时间')

    __table_args__ = (
        Index('idx_pay_qrcode_type', 'type'),
        Index('idx_pay_qrcode_enabled', 'is_enabled'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'type': self.type,
            'image_url': self.image_url,
            'amount': self.amount,
            'description': self.description,
            'is_enabled': self.is_enabled,
            'sort_order': self.sort_order,
            'created_at': format_datetime(self.created_at),
            'updated_at': format_datetime(self.updated_at),
        }


# ==================== 管理端相关 ====================

class AdminParseSource(Base):
    """视频解析源表"""
    __tablename__ = 'admin_parse_source'

    id = Column(Integer, primary_key=True, autoincrement=True)
    platform_id = Column(Integer, ForeignKey('admin_platform.id', ondelete='CASCADE'), nullable=True, index=True, comment='关联平台ID，为空表示通用')
    key = Column(String(100), unique=True, nullable=False, index=True, comment='解析源键名')
    name = Column(String(200), nullable=False, comment='解析源名称')
    type = Column(String(20), nullable=False, default='json', comment='解析源类型：json, video, search')
    url = Column(String(500), nullable=False, comment='解析接口地址前缀')
    sort_order = Column(Integer, default=0, comment='排序')
    success_count = Column(Integer, default=0, comment='成功次数（持久化到DB）')
    fail_count = Column(Integer, default=0, comment='失败次数（持久化到DB）')
    enabled = Column(Boolean, default=True, comment='是否启用')
    created_at = Column(DateTime, default=utc_plus_8, comment='创建时间')
    updated_at = Column(DateTime, default=utc_plus_8, onupdate=utc_plus_8, comment='更新时间')

    __table_args__ = (
        Index('idx_admin_parse_source_key', 'key'),
        Index('idx_admin_parse_source_platform', 'platform_id'),
        Index('idx_admin_parse_source_enabled', 'enabled'),
        Index('idx_admin_parse_source_sort', 'sort_order'),
    )

    def to_dict(self):
        total = (self.success_count or 0) + (self.fail_count or 0)
        rate = round((self.success_count or 0) / total * 100, 1) if total > 0 else None
        return {
            'id': self.id,
            'platform_id': self.platform_id,
            'key': self.key,
            'name': self.name,
            'type': self.type,
            'url': self.url,
            'sort_order': self.sort_order,
            'success_count': self.success_count or 0,
            'fail_count': self.fail_count or 0,
            'success_rate': rate,
            'enabled': self.enabled,
            'created_at': format_datetime(self.created_at),
            'updated_at': format_datetime(self.updated_at),
        }


class AdminUser(Base):
    """管理端用户表"""
    __tablename__ = 'admin_user'

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(100), unique=True, nullable=False, index=True, comment='用户名')
    password_hash = Column(String(255), nullable=False, comment='密码哈希')
    role = Column(String(20), nullable=False, default='operator', comment='角色：admin-管理员, operator-操作员')
    nickname = Column(String(100), nullable=True, comment='昵称')
    is_active = Column(Boolean, default=True, comment='是否启用')
    last_login = Column(DateTime, nullable=True, comment='最后登录时间')
    created_at = Column(DateTime, default=utc_plus_8, comment='创建时间')
    updated_at = Column(DateTime, default=utc_plus_8, onupdate=utc_plus_8, comment='更新时间')

    __table_args__ = (
        Index('idx_admin_user_role', 'role'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'role': self.role,
            'nickname': self.nickname,
            'is_active': self.is_active,
            'last_login': format_datetime(self.last_login),
            'created_at': format_datetime(self.created_at),
            'updated_at': format_datetime(self.updated_at),
        }


class AdminCategory(Base):
    """频道大分类表"""
    __tablename__ = 'admin_category'

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(50), unique=True, nullable=False, index=True, comment='频道标识，例如：tv, movie')
    name = Column(String(100), nullable=False, comment='频道名称，例如：电视剧')
    icon = Column(String(500), nullable=True, comment='图标URL')
    description = Column(Text, nullable=True, comment='描述')
    sort_order = Column(Integer, default=0, comment='排序')
    enabled = Column(Boolean, default=True, comment='是否启用')
    created_at = Column(DateTime, default=utc_plus_8, comment='创建时间')
    updated_at = Column(DateTime, default=utc_plus_8, onupdate=utc_plus_8, comment='更新时间')

    __table_args__ = (
        Index('idx_admin_category_key', 'key'),
        Index('idx_admin_category_enabled', 'enabled'),
        Index('idx_admin_category_sort', 'sort_order'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'key': self.key,
            'name': self.name,
            'icon': self.icon,
            'description': self.description,
            'sort_order': self.sort_order,
            'enabled': self.enabled,
            'created_at': format_datetime(self.created_at),
            'updated_at': format_datetime(self.updated_at),
        }


class AdminPlatform(Base):
    """视频平台表"""
    __tablename__ = 'admin_platform'

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(50), unique=True, nullable=False, index=True, comment='平台标识，例如：iqiyi')
    name = Column(String(100), nullable=False, comment='平台名称，例如：爱奇艺')
    official_site = Column(String(500), nullable=True, comment='官网地址')
    spider = Column(String(500), nullable=True, comment='爬虫类路径')
    rate_limit = Column(Float, default=1.0, comment='请求频率限制（秒）')
    timeout = Column(Integer, default=15, comment='请求超时（秒）')
    icon = Column(String(500), nullable=True, comment='平台图标')
    user_agent = Column(Text, nullable=True, comment='请求 User-Agent')
    keywords = Column(Text, nullable=True, comment='关键词配置（JSON）')
    config = Column(Text, nullable=True, comment='扩展配置（JSON）')
    sort_order = Column(Integer, default=0, comment='排序')
    enabled = Column(Boolean, default=True, comment='是否启用')
    created_at = Column(DateTime, default=utc_plus_8, comment='创建时间')
    updated_at = Column(DateTime, default=utc_plus_8, onupdate=utc_plus_8, comment='更新时间')

    __table_args__ = (
        Index('idx_admin_platform_key', 'key'),
        Index('idx_admin_platform_enabled', 'enabled'),
        Index('idx_admin_platform_sort', 'sort_order'),
    )

    def to_dict(self):
        keywords_dict = None
        if self.keywords:
            try:
                keywords_dict = json.loads(self.keywords)
            except:
                pass
        config_dict = None
        if self.config:
            try:
                config_dict = json.loads(self.config)
            except:
                pass
        return {
            'id': self.id,
            'key': self.key,
            'name': self.name,
            'official_site': self.official_site,
            'spider': self.spider,
            'rate_limit': self.rate_limit,
            'timeout': self.timeout,
            'icon': self.icon,
            'user_agent': self.user_agent,
            'keywords': keywords_dict,
            'config': config_dict,
            'sort_order': self.sort_order,
            'enabled': self.enabled,
            'created_at': format_datetime(self.created_at),
            'updated_at': format_datetime(self.updated_at),
        }


class AdminPlatformChannel(Base):
    """平台频道配置表"""
    __tablename__ = 'admin_platform_channel'

    id = Column(Integer, primary_key=True, autoincrement=True)
    platform_id = Column(Integer, ForeignKey('admin_platform.id', ondelete='CASCADE'), nullable=False, index=True, comment='关联平台ID')
    category_id = Column(Integer, ForeignKey('admin_category.id', ondelete='CASCADE'), nullable=False, index=True, comment='关联频道ID')
    channel_key = Column(String(50), nullable=False, comment='该平台下的频道标识')
    channel_name = Column(String(100), nullable=True, comment='该平台下的频道名称')
    url = Column(String(1000), nullable=False, comment='爬取地址')
    output_table = Column(String(50), default='series', comment='输出表')
    channel_id = Column(String(100), nullable=True, comment='平台特定的频道ID')
    config = Column(Text, nullable=True, comment='扩展配置（JSON）')
    enabled = Column(Boolean, default=True, comment='是否启用')
    sort_order = Column(Integer, default=0, comment='排序')
    created_at = Column(DateTime, default=utc_plus_8, comment='创建时间')
    updated_at = Column(DateTime, default=utc_plus_8, onupdate=utc_plus_8, comment='更新时间')

    platform = relationship("AdminPlatform")
    category = relationship("AdminCategory")

    __table_args__ = (
        Index('idx_admin_pc_platform', 'platform_id'),
        Index('idx_admin_pc_category', 'category_id'),
        Index('idx_admin_pc_platform_category', 'platform_id', 'category_id', unique=True),
    )

    def to_dict(self):
        config_dict = None
        if self.config:
            try:
                config_dict = json.loads(self.config)
            except:
                pass
        return {
            'id': self.id,
            'platform_id': self.platform_id,
            'category_id': self.category_id,
            'channel_key': self.channel_key,
            'channel_name': self.channel_name,
            'url': self.url,
            'output_table': self.output_table,
            'channel_id': self.channel_id,
            'config': config_dict,
            'enabled': self.enabled,
            'sort_order': self.sort_order,
            'created_at': format_datetime(self.created_at),
            'updated_at': format_datetime(self.updated_at),
            'platform': self.platform.to_dict() if self.platform else None,
            'category': self.category.to_dict() if self.category else None,
        }


# ==================== 数据库引擎和会话工厂 ====================

data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
os.makedirs(data_dir, exist_ok=True)
DB_PATH = os.path.join(data_dir, 'vbox.db')
# 新数据库文件，避免被占用的 vbox.db
engine = create_engine(
    f'sqlite:///{DB_PATH}',
    echo=False,
    connect_args={
        'timeout': 30,
        'check_same_thread': False,
    },
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """初始化数据库，创建所有表"""
    # 启用WAL模式提高并发性能
    try:
        with engine.connect() as conn:
            conn.execute(text("PRAGMA journal_mode=WAL"))
            conn.execute(text("PRAGMA busy_timeout=30000"))
            conn.commit()
    except Exception as e:
        print(f"设置WAL模式失败: {e}")

    # 删除旧表（数据不需要保留）
    old_tables = [
        'series', 'episodes',
        'crawl_tasks', 'crawl_task_logs', 'scheduled_tasks', 'spider_keywords',
        'users', 'sms_codes', 'watch_history', 'follow_series', 'bookmarks',
        'vip_plans', 'vip_cdkeys', 'payment_qrcodes',
        'categories', 'platforms', 'platform_channels',
    ]
    try:
        with engine.connect() as conn:
            for old_table in old_tables:
                result = conn.execute(text(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{old_table}'"))
                if result.fetchone():
                    print(f"删除旧表: {old_table}")
                    conn.execute(text(f'DROP TABLE IF EXISTS "{old_table}"'))
            conn.commit()
    except Exception as e:
        print(f"删除旧表失败: {e}")

    # 创建所有新表
    Base.metadata.create_all(bind=engine)

    # 迁移：为已有表添加新列（SQLite ALTER TABLE 只支持 ADD COLUMN）
    _migrations = {
        'admin_parse_source': [
            ('success_count', 'INTEGER DEFAULT 0'),
            ('fail_count', 'INTEGER DEFAULT 0'),
        ],
    }
    try:
        with engine.connect() as conn:
            for table_name, columns in _migrations.items():
                for col_name, col_def in columns:
                    try:
                        conn.execute(text(f'ALTER TABLE {table_name} ADD COLUMN {col_name} {col_def}'))
                        print(f"迁移: 表 {table_name} 添加列 {col_name}")
                    except Exception:
                        pass  # 列已存在
            conn.commit()
    except Exception as e:
        print(f"迁移失败: {e}")

    print(f"数据库初始化完成，频道表: {[get_video_table_name(k) for k in CATEGORY_KEYS]}")


@contextmanager
def get_session():
    """获取数据库会话（上下文管理器，自动处理提交和回滚）"""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()



# ==================== 向后兼容的别名，用于旧代码导入 ====================
Category = AdminCategory
Platform = AdminPlatform
PlatformChannel = AdminPlatformChannel
ParseSource = AdminParseSource
CrawlTask = TaskCrawl
ScheduledTask = TaskSchedule

# 临时使用 tv 作为默认的 Video_tv 别名，用于旧代码
Video_tv = get_video_model('tv')
Video_tv_ep = get_video_ep_model('tv')
Series = Video_tv
Episode = Video_tv_ep


if __name__ == '__main__':
    init_db()
    print(f"数据库已初始化: {DB_PATH}")

