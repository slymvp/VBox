"""
数据库操作封装 - 按频道路由
核心架构：以频道（Category）为大类，每个频道独立表
所有视频数据操作都需要传入 category_key 来路由到对应频道表
"""
from contextlib import contextmanager
import json
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Callable

from sqlalchemy import Integer as sqlalchemy_Integer, case

from models import (
    CATEGORY_KEYS, get_video_model, get_video_ep_model,
    get_video_table_name, get_video_ep_table_name,
    TaskCrawl, TaskSchedule,
    get_session, init_db, SessionLocal,
    AdminCategory, AdminPlatform, AdminPlatformChannel, AdminParseSource,
    AdminUser,
    User, UserSmsCode, UserWatchHistory, UserFollow, UserBookmark,
    VipPlan, VipCdkey, PayQrcode,
    Category, Platform, PlatformChannel, ParseSource,
)


def utc_plus_8():
    now = datetime.utcnow() + timedelta(hours=8)
    return now.replace(microsecond=0)


class DatabaseManager:
    """数据库管理器 - 按频道路由"""

    def __init__(self, session_factory: Callable = None):
        self._session_factory = session_factory or SessionLocal

    @contextmanager
    def session_scope(self):
        session = self._session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    # ==================== 视频数据（按频道路由） ====================

    def save_series(self, category_key: str, series_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """保存或更新剧集信息到对应频道表"""
        SeriesModel = get_video_model(category_key)
        with self.session_scope() as session:
            existing = session.query(SeriesModel).filter(SeriesModel.cid == series_data['cid']).first()
            if existing:
                for key, value in series_data.items():
                    if not hasattr(existing, key) or value is None:
                        continue
                    if key == 'tags' and isinstance(value, list):
                        value = json.dumps(value, ensure_ascii=False)
                    existing_val = getattr(existing, key, None)
                    # is_hot/is_new 允许从1更新为0（单独抓热门/最新列表时会刷0）
                    if key in ('is_hot', 'is_new') and value == 0:
                        pass
                    elif value == '' or value == [] or value == 0:
                        if existing_val is not None and existing_val != '' and existing_val != 0:
                            continue
                    setattr(existing, key, value)
                existing.updated_at = utc_plus_8()
                session.flush()
                return {'id': existing.id, 'cid': existing.cid}
            else:
                if isinstance(series_data.get('tags'), list):
                    series_data['tags'] = json.dumps(series_data['tags'], ensure_ascii=False)
                series = SeriesModel(**{k: v for k, v in series_data.items() if hasattr(SeriesModel, k)})
                session.add(series)
                session.flush()
                return {'id': series.id, 'cid': series.cid}

    def admin_create_series(self, category_key: str, series_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """管理端创建新剧集"""
        SeriesModel = get_video_model(category_key)
        with self.session_scope() as session:
            series = SeriesModel(**{k: v for k, v in series_data.items() if hasattr(SeriesModel, k)})
            session.add(series)
            session.flush()
            return series.to_dict()

    def admin_update_series(self, category_key: str, series_id: int, series_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """管理端更新剧集"""
        SeriesModel = get_video_model(category_key)
        with self.session_scope() as session:
            series = session.query(SeriesModel).filter(SeriesModel.id == series_id).first()
            if not series:
                return None
            for key, value in series_data.items():
                if not hasattr(series, key) or key in ['id', 'created_at', 'updated_at']:
                    continue
                setattr(series, key, value)
            series.updated_at = utc_plus_8()
            session.flush()
            return series.to_dict()

    def get_series_by_id(self, category_key: str, series_id: int) -> Optional[Dict[str, Any]]:
        """通过ID获取剧集信息"""
        SeriesModel = get_video_model(category_key)
        with self.session_scope() as session:
            series = session.query(SeriesModel).filter(SeriesModel.id == series_id).first()
            return series.to_dict() if series else None

    def get_series_by_cid(self, category_key: str, cid: str) -> Optional[Dict[str, Any]]:
        """根据CID获取剧集"""
        SeriesModel = get_video_model(category_key)
        with self.session_scope() as session:
            series = session.query(SeriesModel).filter(SeriesModel.cid == cid).first()
            if not series:
                return None
            return series.to_dict()

    def get_series_with_episodes(self, category_key: str, cid: str) -> Optional[Dict[str, Any]]:
        """获取剧集及其所有分集"""
        SeriesModel = get_video_model(category_key)
        EpModel = get_video_ep_model(category_key)
        with self.session_scope() as session:
            series = session.query(SeriesModel).filter(SeriesModel.cid == cid).first()
            if not series:
                return None
            # 问题3：分集按类型 + episode_num 数字升序（CAST AS INTEGER，使 1,2,3...10 顺序正确）
            from sqlalchemy import func
            episodes = (
                session.query(EpModel)
                .filter(EpModel.series_id == series.id)
                .order_by(
                    EpModel.episode_type,
                    func.cast(EpModel.episode_num, sqlalchemy_Integer()),
                )
                .all()
            )
            result = series.to_dict()
            result['episodes'] = [ep.to_dict() for ep in episodes]
            return result

    def find_series_with_episodes_by_cid(self, cid: str) -> Optional[Dict[str, Any]]:
        """跨频道查找剧集及其分集（按cid自动路由到正确的频道表）"""
        for cat_key in CATEGORY_KEYS:
            result = self.get_series_with_episodes(cat_key, cid)
            if result:
                result['category_key'] = cat_key
                return result
        return None

    def list_series(self, category_key: str, platform: Optional[str] = None, keyword: Optional[str] = None, id: Optional[int] = None, sort: Optional[str] = None, page: int = 1, limit: int = 20, year: Optional[str] = None, area: Optional[str] = None, tag: Optional[str] = None, director: Optional[str] = None, actor: Optional[str] = None, min_score: Optional[float] = None) -> Dict[str, Any]:
        """获取剧集列表（从对应频道表查询）"""
        # 免费专区是特殊处理：跨所有频道筛选 is_vip = 0 的内容
        if category_key == 'free':
            return self._list_free_series(
                platform=platform, keyword=keyword, sort=sort, page=page, limit=limit,
                year=year, area=area, tag=tag, director=director, actor=actor, min_score=min_score
            )
        
        SeriesModel = get_video_model(category_key)
        with self.session_scope() as session:
            query = session.query(SeriesModel)
            if id:
                query = query.filter(SeriesModel.id == id)
            if platform:
                query = query.filter(SeriesModel.platform == platform)
            if year:
                query = query.filter(SeriesModel.year == year)
            if area:
                query = query.filter(SeriesModel.area == area)
            if tag:
                query = query.filter(SeriesModel.tags.like(f'%{tag}%'))
            if director:
                query = query.filter(SeriesModel.director.like(f'%{director}%'))
            if actor:
                query = query.filter(SeriesModel.actors.like(f'%{actor}%'))
            if min_score is not None:
                query = query.filter(SeriesModel.score >= min_score)
            if keyword:
                from sqlalchemy import or_
                def escape_like(k: str) -> str:
                    k = k.replace('\\', '\\\\')
                    k = k.replace('%', '\\%')
                    k = k.replace('_', '\\_')
                    return k
                escaped_keyword = escape_like(keyword)
                query = query.filter(
                    or_(
                        SeriesModel.title.like(f'%{escaped_keyword}%', escape='\\'),
                        SeriesModel.description.like(f'%{escaped_keyword}%', escape='\\')
                    )
                )
            total = query.count()
            # 排序：腾讯内容优先，hot/new 以 score 作为二级排序
            tencent_first = case((SeriesModel.platform == 'tencent', 0), else_=1)
            if sort == 'hot':
                query = query.order_by(tencent_first, SeriesModel.is_hot.desc(), SeriesModel.score.desc().nulls_last(), SeriesModel.updated_at.desc())
            elif sort == 'new':
                query = query.order_by(tencent_first, SeriesModel.is_new.desc(), SeriesModel.score.desc().nulls_last(), SeriesModel.updated_at.desc())
            elif sort == 'score':
                query = query.order_by(tencent_first, SeriesModel.score.desc().nulls_last(), SeriesModel.updated_at.desc())
            else:
                query = query.order_by(tencent_first, SeriesModel.score.desc().nulls_last(), SeriesModel.updated_at.desc())
            offset = (page - 1) * limit
            series_list = query.offset(offset).limit(limit).all()
            return {
                'items': [s.to_dict() for s in series_list],
                'total': total,
                'page': page,
                'limit': limit,
            }

    def _list_free_series(self, platform: Optional[str] = None, keyword: Optional[str] = None, sort: Optional[str] = None, page: int = 1, limit: int = 20, year: Optional[str] = None, area: Optional[str] = None, tag: Optional[str] = None, director: Optional[str] = None, actor: Optional[str] = None, min_score: Optional[float] = None) -> Dict[str, Any]:
        """免费专区：跨所有频道筛选 is_vip = 0 的内容"""
        all_items = []
        # 遍历所有非 free 频道
        for cat_key in CATEGORY_KEYS:
            if cat_key == 'free':
                continue
            # 获取该频道的免费内容
            SeriesModel = get_video_model(cat_key)
            with self.session_scope() as session:
                query = session.query(SeriesModel).filter(SeriesModel.is_vip == 0)
                if platform:
                    query = query.filter(SeriesModel.platform == platform)
                if year:
                    query = query.filter(SeriesModel.year == year)
                if area:
                    query = query.filter(SeriesModel.area == area)
                if tag:
                    query = query.filter(SeriesModel.tags.like(f'%{tag}%'))
                if director:
                    query = query.filter(SeriesModel.director.like(f'%{director}%'))
                if actor:
                    query = query.filter(SeriesModel.actors.like(f'%{actor}%'))
                if min_score is not None:
                    query = query.filter(SeriesModel.score >= min_score)
                if keyword:
                    from sqlalchemy import or_
                    def escape_like(k: str) -> str:
                        k = k.replace('\\', '\\\\')
                        k = k.replace('%', '\\%')
                        k = k.replace('_', '\\_')
                        return k
                    escaped_keyword = escape_like(keyword)
                    query = query.filter(
                        or_(
                            SeriesModel.title.like(f'%{escaped_keyword}%', escape='\\'),
                            SeriesModel.description.like(f'%{escaped_keyword}%', escape='\\')
                        )
                    )
                series_list = query.all()
                # 加入 category_key
                for s in series_list:
                    item = s.to_dict()
                    item['category_key'] = cat_key
                    all_items.append(item)
        
        # 排序：腾讯内容优先，hot/new 以 score 作为二级排序
        if sort == 'hot':
            all_items.sort(key=lambda x: x.get('updated_at', ''), reverse=True)
            all_items.sort(key=lambda x: -(float(x.get('score', 0) or 0)))
            all_items.sort(key=lambda x: -(x.get('is_hot', 0)))
            all_items.sort(key=lambda x: x.get('platform') != 'tencent')
        elif sort == 'new':
            all_items.sort(key=lambda x: x.get('updated_at', ''), reverse=True)
            all_items.sort(key=lambda x: -(float(x.get('score', 0) or 0)))
            all_items.sort(key=lambda x: -(x.get('is_new', 0)))
            all_items.sort(key=lambda x: x.get('platform') != 'tencent')
        elif sort == 'score':
            all_items.sort(key=lambda x: x.get('updated_at', ''), reverse=True)
            all_items.sort(key=lambda x: -(float(x.get('score', 0) or 0)))
            all_items.sort(key=lambda x: x.get('platform') != 'tencent')
        else:
            all_items.sort(key=lambda x: x.get('updated_at', ''), reverse=True)
            all_items.sort(key=lambda x: -(float(x.get('score', 0) or 0)))
            all_items.sort(key=lambda x: x.get('platform') != 'tencent')
        
        total = len(all_items)
        offset = (page - 1) * limit
        items = all_items[offset:offset + limit]
        
        return {
            'items': items,
            'total': total,
            'page': page,
            'limit': limit,
        }

    def update_series_episodes_count(self, category_key: str, cid: str, total_episodes: int, updated_episodes: int):
        """更新剧集的分集数量"""
        SeriesModel = get_video_model(category_key)
        with self.session_scope() as session:
            series = session.query(SeriesModel).filter(SeriesModel.cid == cid).first()
            if series:
                series.total_episodes = total_episodes
                series.updated_episodes = updated_episodes
                series.updated_at = utc_plus_8()

    # ==================== 分集数据（按频道路由） ====================

    def save_episodes(self, category_key: str, series_id: int, episodes_data: List[Dict[str, Any]]) -> int:
        """保存分集信息到对应频道表"""
        EpModel = get_video_ep_model(category_key)
        with self.session_scope() as session:
            count = 0
            # 问题1：预先查出所有已存记录，在内存中做去重，避免同 session 内 flush 前查不到新增记录导致重复入库
            existing_by_vid = {}
            existing_by_ep_key = {}
            for ep in session.query(EpModel).filter(EpModel.series_id == series_id).all():
                if ep.vid:
                    existing_by_vid[ep.vid] = ep
                existing_by_ep_key[(ep.episode_num, ep.episode_type)] = ep

            for ep_data in episodes_data:
                episode_type = ep_data.get('episode_type', 0)
                episode_num = ep_data.get('episode_num', '')
                vid = ep_data.get('vid', '')

                existing = None
                if vid:
                    existing = existing_by_vid.get(vid)
                if not existing:
                    existing = existing_by_ep_key.get((episode_num, episode_type))

                if not existing:
                    episode = EpModel(
                        series_id=series_id,
                        episode_num=episode_num,
                        vid=vid,
                        play_title=ep_data.get('play_title', ''),
                        union_title=ep_data.get('union_title', ''),
                        episode_type=episode_type,
                        duration=ep_data.get('duration', ''),
                        publish_date=ep_data.get('publish_date', ''),
                        is_vip=ep_data.get('is_vip', 0),
                        play_url=ep_data.get('play_url', ''),
                    )
                    session.add(episode)
                    # 同步更新内存去重集合，防止同一批数据中有重复 vid
                    if vid:
                        existing_by_vid[vid] = episode
                    existing_by_ep_key[(episode_num, episode_type)] = episode
                    count += 1
                else:
                    updated = False
                    for key in ['vid', 'play_title', 'union_title', 'episode_type', 'duration', 'publish_date', 'play_url']:
                        new_val = ep_data.get(key, '')
                        old_val = getattr(existing, key, '') or ''
                        if new_val and new_val != old_val:
                            setattr(existing, key, new_val)
                            updated = True
                    # is_vip 是整数，0 也是有效值，需单独处理
                    new_vip = ep_data.get('is_vip', None)
                    if new_vip is not None and new_vip != getattr(existing, 'is_vip', None):
                        existing.is_vip = new_vip
                        updated = True
                    if updated:
                        count += 1
            return count

    def batch_save_series_and_episodes(self, category_key: str, items_data: List[Dict[str, Any]], sort: str = None) -> int:
        """批量保存剧集和分集（单次session，减少DB开销）
        :param category_key: 频道标识（tv, movie, variety, cartoon, child）
        :param items_data: 剧集数据列表
        :param sort: 排序类型，'hot'=只刷is_hot, 'new'=只刷is_new, None=全量保存
        返回成功保存的剧集数
        """
        SeriesModel = get_video_model(category_key)
        EpModel = get_video_ep_model(category_key)
        saved_count = 0
        is_mark_only = sort in ('hot', 'new')  # 只刷新标记字段，不更新其他数据

        with self.session_scope() as session:
            for item in items_data:
                try:
                    series_data = item.get('series_data', {})
                    episodes_data = item.get('episodes_data', [])

                    # 查找已有记录
                    existing = session.query(SeriesModel).filter(
                        SeriesModel.cid == series_data['cid']
                    ).first()

                    if existing:
                        if is_mark_only:
                            # 只刷新 is_hot/is_new 标记字段，其他数据不更新
                            if sort == 'hot':
                                setattr(existing, 'is_hot', series_data.get('is_hot', 1))
                            elif sort == 'new':
                                setattr(existing, 'is_new', series_data.get('is_new', 1))
                            existing.updated_at = utc_plus_8()
                        else:
                            # 全量保存：更新已有记录（只覆盖非空值）
                            for key, value in series_data.items():
                                if not hasattr(existing, key) or value is None:
                                    continue
                                if key == 'tags' and isinstance(value, list):
                                    value = json.dumps(value, ensure_ascii=False)
                                existing_val = getattr(existing, key, None)
                                # is_hot/is_new 允许从1更新为0（单独抓热门/最新列表时会刷0）
                                if key in ('is_hot', 'is_new') and value == 0:
                                    pass  # 允许清零
                                elif value == '' or value == [] or value == 0:
                                    if existing_val is not None and existing_val != '' and existing_val != 0:
                                        continue
                                setattr(existing, key, value)
                            existing.updated_at = utc_plus_8()
                        series_id = existing.id
                    else:
                        if is_mark_only:
                            # 只刷新标记模式：数据库不存在的剧跳过，不新增
                            continue
                        # 新增记录
                        if isinstance(series_data.get('tags'), list):
                            series_data['tags'] = json.dumps(series_data['tags'], ensure_ascii=False)
                        series = SeriesModel(**{k: v for k, v in series_data.items() if hasattr(SeriesModel, k)})
                        session.add(series)
                        session.flush()  # 获取id
                        series_id = series.id

                    # 保存分集（只刷新标记模式跳过，不需要分集数据）
                    if not is_mark_only and episodes_data and series_id:
                        # 问题1：预先加载已有记录到内存，防止同 session 内重复插入
                        existing_by_vid = {}
                        existing_by_ep_key = {}
                        for ep in session.query(EpModel).filter(EpModel.series_id == series_id).all():
                            if ep.vid:
                                existing_by_vid[ep.vid] = ep
                            existing_by_ep_key[(ep.episode_num, ep.episode_type)] = ep

                        for ep_data in episodes_data:
                            episode_type = ep_data.get('episode_type', 0)
                            episode_num = ep_data.get('episode_num', '')
                            vid = ep_data.get('vid', '')
                            existing_ep = None
                            if vid:
                                existing_ep = existing_by_vid.get(vid)
                            if not existing_ep:
                                existing_ep = existing_by_ep_key.get((episode_num, episode_type))
                            if not existing_ep:
                                episode = EpModel(
                                    series_id=series_id,
                                    episode_num=episode_num,
                                    vid=vid,
                                    play_title=ep_data.get('play_title', ''),
                                    union_title=ep_data.get('union_title', ''),
                                    episode_type=episode_type,
                                    duration=ep_data.get('duration', ''),
                                    publish_date=ep_data.get('publish_date', ''),
                                    is_vip=ep_data.get('is_vip', 0),
                                    play_url=ep_data.get('play_url', ''),
                                )
                                session.add(episode)
                                # 同步更新内存集合
                                if vid:
                                    existing_by_vid[vid] = episode
                                existing_by_ep_key[(episode_num, episode_type)] = episode
                            else:
                                for key in ['vid', 'play_title', 'union_title', 'episode_type', 'duration', 'publish_date', 'play_url']:
                                    new_val = ep_data.get(key, '')
                                    old_val = getattr(existing_ep, key, '') or ''
                                    if new_val and new_val != old_val:
                                        setattr(existing_ep, key, new_val)
                                # is_vip 整数字段单独处理（0 也是有效值）
                                new_vip = ep_data.get('is_vip', None)
                                if new_vip is not None and new_vip != getattr(existing_ep, 'is_vip', None):
                                    existing_ep.is_vip = new_vip

                    saved_count += 1

                except Exception as e:
                    import logging
                    logging.getLogger(__name__).error('批量保存单条失败: %s, 错误: %s', series_data.get('title', '未知'), e)
                    continue

        return saved_count

    def list_episodes(self, category_key: str, series_id: Optional[int] = None, keyword: Optional[str] = None, page: int = 1, limit: int = 20) -> Dict[str, Any]:
        """获取分集列表"""
        EpModel = get_video_ep_model(category_key)
        with self.session_scope() as session:
            from sqlalchemy import func, or_
            query = session.query(EpModel)
            if series_id:
                query = query.filter(EpModel.series_id == series_id)
            if keyword:
                # 关键词筛选播放标题或联合标题
                def escape_like(k: str) -> str:
                    k = k.replace('\\', '\\\\')
                    k = k.replace('%', '\\%')
                    k = k.replace('_', '\\_')
                    return k
                escaped_keyword = escape_like(keyword)
                query = query.filter(
                    or_(
                        EpModel.play_title.like(f'%{escaped_keyword}%', escape='\\'),
                        EpModel.union_title.like(f'%{escaped_keyword}%', escape='\\')
                    )
                )
            total = query.count()
            # 问题3：按 episode_type + CAST(episode_num AS INTEGER) 排序，保证正片顺序正确
            query = query.order_by(
                EpModel.episode_type,
                func.cast(EpModel.episode_num, sqlalchemy_Integer()),
            )
            offset = (page - 1) * limit
            episodes = query.offset(offset).limit(limit).all()
            return {
                'items': [ep.to_dict() for ep in episodes],
                'total': total,
                'page': page,
                'limit': limit
            }

    def admin_create_episode(self, category_key: str, episode_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        EpModel = get_video_ep_model(category_key)
        with self.session_scope() as session:
            episode = EpModel(**{k: v for k, v in episode_data.items() if hasattr(EpModel, k)})
            session.add(episode)
            session.flush()
            return episode.to_dict()

    def admin_update_episode(self, category_key: str, episode_id: int, episode_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        EpModel = get_video_ep_model(category_key)
        with self.session_scope() as session:
            episode = session.query(EpModel).filter(EpModel.id == episode_id).first()
            if not episode:
                return None
            for key, value in episode_data.items():
                if not hasattr(episode, key) or key in ['id', 'created_at']:
                    continue
                setattr(episode, key, value)
            session.flush()
            return episode.to_dict()

    def delete_episode(self, category_key: str, episode_id: int) -> bool:
        EpModel = get_video_ep_model(category_key)
        with self.session_scope() as session:
            episode = session.query(EpModel).filter(EpModel.id == episode_id).first()
            if not episode:
                return False
            session.delete(episode)
            return True

    # ==================== 跨频道查询 ====================

    def list_series_all(self, platform: Optional[str] = None, keyword: Optional[str] = None, sort: Optional[str] = None, page: int = 1, limit: int = 20, year: Optional[str] = None, area: Optional[str] = None, tag: Optional[str] = None, director: Optional[str] = None, actor: Optional[str] = None, min_score: Optional[float] = None) -> Dict[str, Any]:
        """跨所有频道表查询剧集列表（首页用）"""
        all_items = []
        for cat_key in CATEGORY_KEYS:
            result = self.list_series(cat_key, platform=platform, keyword=keyword, sort=sort, page=1, limit=1000, year=year, area=area, tag=tag, director=director, actor=actor, min_score=min_score)
            for item in result['items']:
                item['category_key'] = cat_key
                all_items.append(item)
        # 排序：腾讯内容优先，hot=按评分降序，latest=按更新时间+评分降序（默认）
        if sort == 'hot':
            all_items.sort(key=lambda x: float(x.get('score', 0) or 0), reverse=True)
            all_items.sort(key=lambda x: x.get('platform') != 'tencent')
        else:
            all_items.sort(key=lambda x: x.get('updated_at', ''), reverse=True)
            all_items.sort(key=lambda x: -(float(x.get('score', 0) or 0)))
            all_items.sort(key=lambda x: x.get('platform') != 'tencent')
        total = len(all_items)
        offset = (page - 1) * limit
        items = all_items[offset:offset + limit]
        return {
            'items': items,
            'total': total,
            'page': page,
            'limit': limit,
        }

    def search_series_all(self, keyword: str, platform: Optional[str] = None, page: int = 1, limit: int = 20) -> Dict[str, Any]:
        """跨所有频道表搜索"""
        return self.list_series_all(platform=platform, keyword=keyword, page=page, limit=limit)

    def get_filter_options(self, category_key: str, platform: Optional[str] = None) -> Dict[str, Any]:
        """获取筛选选项（去重的年份、地区、标签、导演、演员列表）"""
        import json as _json
        from models import CATEGORY_KEYS
        
        all_years = set()
        all_areas = set()
        all_tags = set()
        all_directors = set()
        all_actors = set()

        with self.session_scope() as session:
            # 如果是 'free' 分类，需要查询所有表中的免费内容
            if category_key == 'free':
                for cat_key in CATEGORY_KEYS:
                    if cat_key == 'free':
                        continue  # 跳过虚拟分类本身没有表
                    SeriesModel = get_video_model(cat_key)
                    query = session.query(SeriesModel).filter(SeriesModel.is_vip == 0)
                    if platform:
                        query = query.filter(SeriesModel.platform == platform)
                    
                    years = [r[0] for r in query.with_entities(SeriesModel.year).distinct().all() if r[0]]
                    areas = [r[0] for r in query.with_entities(SeriesModel.area).distinct().all() if r[0]]
                    
                    all_years.update(years)
                    all_areas.update(areas)
                    
                    rows = query.with_entities(SeriesModel.tags, SeriesModel.director, SeriesModel.actors).all()
                    for tags_str, director_str, actors_str in rows:
                        if tags_str:
                            try:
                                for t in _json.loads(tags_str):
                                    if t and isinstance(t, str):
                                        all_tags.add(t.strip())
                            except Exception:
                                pass
                        if director_str:
                            try:
                                for d in _json.loads(director_str):
                                    if d and isinstance(d, str):
                                        all_directors.add(d.strip())
                            except Exception:
                                pass
                        if actors_str:
                            try:
                                for a in _json.loads(actors_str):
                                    if a and isinstance(a, str):
                                        all_actors.add(a.strip())
                            except Exception:
                                pass
            else:
                # 普通分类，直接查询对应表
                SeriesModel = get_video_model(category_key)
                query = session.query(SeriesModel)
                if platform:
                    query = query.filter(SeriesModel.platform == platform)

                years = [r[0] for r in query.with_entities(SeriesModel.year).distinct().order_by(SeriesModel.year.desc()).all() if r[0]]
                areas = [r[0] for r in query.with_entities(SeriesModel.area).distinct().order_by(SeriesModel.area).all() if r[0]]
                
                all_years.update(years)
                all_areas.update(areas)
                
                rows = query.with_entities(SeriesModel.tags, SeriesModel.director, SeriesModel.actors).all()
                for tags_str, director_str, actors_str in rows:
                    if tags_str:
                        try:
                            for t in _json.loads(tags_str):
                                if t and isinstance(t, str):
                                    all_tags.add(t.strip())
                        except Exception:
                            pass
                    if director_str:
                        try:
                            for d in _json.loads(director_str):
                                if d and isinstance(d, str):
                                    all_directors.add(d.strip())
                        except Exception:
                            pass
                    if actors_str:
                        try:
                            for a in _json.loads(actors_str):
                                if a and isinstance(a, str):
                                    all_actors.add(a.strip())
                        except Exception:
                            pass

            return {
                'years': sorted(list(all_years), reverse=True),
                'areas': sorted(list(all_areas)),
                'tags': sorted(all_tags),
                'directors': sorted(all_directors),
                'actors': sorted(all_actors),
            }

    def get_stats(self) -> Dict[str, Any]:
        """获取统计数据（聚合所有频道表，使用 GROUP BY 优化）"""
        total_series = 0
        total_episodes = 0
        platform_stats = {}     # platform → {total, vip, free, ppp}
        category_stats = {}     # category → {total, finished, ongoing}
        vip_stats = {'free': 0, 'vip': 0, 'ppp': 0}
        finish_stats = {'finished': 0, 'ongoing': 0, 'unknown': 0}
        ep_quality_stats = {'complete': 0, 'incomplete': 0, 'no_data': 0}
        last_update = None
        total_users = 0
        total_platforms = 0

        with self.session_scope() as session:
            for cat_key in CATEGORY_KEYS:
                SeriesModel = get_video_model(cat_key)
                EpModel = get_video_ep_model(cat_key)

                # 一次 GROUP BY 查询获取：剧集总数 + 平台分布 + VIP分布 + 完结分布 + 分集质量
                from sqlalchemy import func, case, and_
                aggr = session.query(
                    SeriesModel.platform,
                    func.count(SeriesModel.id).label('total'),
                    func.sum(case(
                        (SeriesModel.is_vip == 0, 1), else_=0
                    )).label('free_cnt'),
                    func.sum(case(
                        (SeriesModel.is_vip == 1, 1), else_=0
                    )).label('vip_cnt'),
                    func.sum(case(
                        (SeriesModel.is_vip == 2, 1), else_=0
                    )).label('ppp_cnt'),
                    func.sum(case(
                        (SeriesModel.is_finished == 1, 1), else_=0
                    )).label('finished_cnt'),
                    func.sum(case(
                        (SeriesModel.is_finished == -1, 1), else_=0
                    )).label('ongoing_cnt'),
                    func.max(SeriesModel.updated_at).label('max_updated'),
                    # 分集完整度：updated_episodes >= total_episodes 且 total_episodes > 0
                    func.sum(case(
                        (and_(
                            SeriesModel.total_episodes > 0,
                            SeriesModel.updated_episodes >= SeriesModel.total_episodes
                        ), 1), else_=0
                    )).label('complete_ep_cnt'),
                    func.sum(case(
                        (SeriesModel.total_episodes > 0, 1), else_=0
                    )).label('has_total_cnt'),
                ).group_by(SeriesModel.platform).all()

                cat_total = 0
                cat_finished = 0
                cat_ongoing = 0

                for row in aggr:
                    plat = row[0]
                    n = int(row[1] or 0)
                    free_n = int(row[2] or 0)
                    vip_n = int(row[3] or 0)
                    ppp_n = int(row[4] or 0)
                    finished_n = int(row[5] or 0)
                    ongoing_n = int(row[6] or 0)
                    max_upd = row[7]
                    complete_ep_n = int(row[8] or 0)
                    has_total_n = int(row[9] or 0)

                    cat_total += n
                    cat_finished += finished_n
                    cat_ongoing += ongoing_n

                    # 分集质量
                    ep_quality_stats['complete'] += complete_ep_n
                    ep_quality_stats['incomplete'] += (has_total_n - complete_ep_n)
                    ep_quality_stats['no_data'] += (n - has_total_n)

                    # 平台级聚合
                    if plat not in platform_stats:
                        platform_stats[plat] = {'total': 0, 'vip': 0, 'free': 0, 'ppp': 0}
                    platform_stats[plat]['total'] += n
                    platform_stats[plat]['vip'] += vip_n
                    platform_stats[plat]['free'] += free_n
                    platform_stats[plat]['ppp'] += ppp_n

                    # 全局 VIP 统计
                    vip_stats['free'] += free_n
                    vip_stats['vip'] += vip_n
                    vip_stats['ppp'] += ppp_n

                    # 全局完结统计
                    finish_stats['finished'] += finished_n
                    finish_stats['ongoing'] += ongoing_n

                    # 各频道最后更新时间
                    if max_upd and (last_update is None or max_upd > last_update):
                        last_update = max_upd

                total_series += cat_total
                cat_unknown = cat_total - cat_finished - cat_ongoing
                category_stats[cat_key] = {
                    'total': cat_total,
                    'finished': cat_finished,
                    'ongoing': cat_ongoing,
                    'unknown': cat_unknown,
                }

                # 分集总数（每个频道一次查询）
                total_episodes += session.query(func.count(EpModel.id)).scalar() or 0

            finish_stats['unknown'] = total_series - finish_stats['finished'] - finish_stats['ongoing']

            # 统计用户和平台数量
            total_users = session.query(func.count(User.id)).scalar() or 0
            total_platforms = session.query(func.count(AdminPlatform.id)).scalar() or 0

        # 为兼容旧前端，同时提供简单格式的 platform_stats/category_stats
        platform_stats_simple = {k: v['total'] for k, v in platform_stats.items()}
        category_stats_simple = {k: v['total'] for k, v in category_stats.items()}

        return {
            'total_series': total_series,
            'total_episodes': total_episodes,
            'total_users': total_users,
            'total_platforms': total_platforms,
            # 简单格式（兼容旧版）
            'platform_stats': platform_stats_simple,
            'category_stats': category_stats_simple,
            # 详细格式（新字段）
            'platform_stats_detail': platform_stats,
            'category_stats_detail': category_stats,
            'vip_stats': vip_stats,
            'finish_stats': finish_stats,
            'ep_quality_stats': ep_quality_stats,
            'last_update': last_update.isoformat() if last_update else None,
        }

    def clear_all_data(self):
        """清空所有视频数据（所有频道表）"""
        result = {'deleted_series': 0, 'deleted_episodes': 0, 'deleted_tasks': 0}
        with self.session_scope() as session:
            for cat_key in CATEGORY_KEYS:
                EpModel = get_video_ep_model(cat_key)
                SeriesModel = get_video_model(cat_key)
                result['deleted_episodes'] += session.query(EpModel).delete(synchronize_session=False)
                result['deleted_series'] += session.query(SeriesModel).delete()
            result['deleted_tasks'] = session.query(TaskCrawl).delete()
        return result

    def clear_platform_data(self, platform: str):
        """清空指定平台的所有数据（所有频道表）"""
        result = {'deleted_series': 0, 'deleted_episodes': 0}
        with self.session_scope() as session:
            for cat_key in CATEGORY_KEYS:
                EpModel = get_video_ep_model(cat_key)
                SeriesModel = get_video_model(cat_key)
                series_ids = session.query(SeriesModel.id).filter(SeriesModel.platform == platform).all()
                series_ids = [s[0] for s in series_ids]
                if series_ids:
                    result['deleted_episodes'] += session.query(EpModel).filter(EpModel.series_id.in_(series_ids)).delete(synchronize_session=False)
                result['deleted_series'] += session.query(SeriesModel).filter(SeriesModel.platform == platform).delete()
        return result

    # ==================== 爬取任务 ====================

    def create_crawl_task(self, platform: str, channel: str) -> int:
        with self.session_scope() as session:
            task = TaskCrawl(platform=platform, channel=channel, status='pending')
            session.add(task)
            session.flush()
            return task.id

    def start_crawl_task(self, task_id: int):
        with self.session_scope() as session:
            task = session.query(TaskCrawl).filter(TaskCrawl.id == task_id).first()
            if task:
                task.status = 'running'
                task.started_at = utc_plus_8()

    def complete_crawl_task(self, task_id: int, items_fetched: int, error_message: Optional[str] = None):
        with self.session_scope() as session:
            task = session.query(TaskCrawl).filter(TaskCrawl.id == task_id).first()
            if task:
                task.status = 'failed' if error_message else 'completed'
                task.items_fetched = items_fetched
                task.error_message = error_message
                task.completed_at = utc_plus_8()

    def delete_crawl_task(self, task_id: int) -> bool:
        with self.session_scope() as session:
            task = session.query(TaskCrawl).filter(TaskCrawl.id == task_id).first()
            if not task:
                return False
            if task.status == 'running':
                return False
            session.delete(task)
            return True

    def batch_delete_crawl_tasks(self, task_ids: List[int]) -> Dict[str, Any]:
        # 先停止运行中的任务
        from core.task_scheduler import get_scheduler
        scheduler = get_scheduler()
        
        stopped_count = 0
        with scheduler.state_lock:
            for task_id, task in list(scheduler.tasks.items()):
                if getattr(task, 'db_task_id', None) in task_ids:
                    if task.status.value == 'running':
                        scheduler.stop_task(task_id)
                        stopped_count += 1
        
        # 然后删除任务
        with self.session_scope() as session:
            tasks = session.query(TaskCrawl).filter(
                TaskCrawl.id.in_(task_ids)
            ).all()
            deleted_count = 0
            for task in tasks:
                session.delete(task)
                deleted_count += 1
            return {'deleted_count': deleted_count, 'stopped_count': stopped_count, 'total_count': len(task_ids)}

    def list_crawl_tasks(self, page: int = 1, limit: int = 20) -> Dict[str, Any]:
        with self.session_scope() as session:
            query = session.query(TaskCrawl)
            total = query.count()
            offset = (page - 1) * limit
            try:
                tasks = query.order_by(TaskCrawl.created_at.desc()).offset(offset).limit(limit).all()
            except AttributeError:
                tasks = query.order_by(TaskCrawl.id.desc()).offset(offset).limit(limit).all()
            return {
                'items': [t.to_dict() for t in tasks],
                'total': total,
                'page': page,
                'limit': limit
            }

    # ==================== 定时任务 ====================

    def list_scheduled_tasks(self) -> list:
        with self.session_scope() as session:
            tasks = session.query(TaskSchedule).order_by(TaskSchedule.created_at.desc()).all()
            return [t.to_dict() for t in tasks]

    def get_scheduled_task(self, task_id: int):
        with self.session_scope() as session:
            task = session.query(TaskSchedule).filter(TaskSchedule.id == task_id).first()
            return task.to_dict() if task else None

    def create_scheduled_task(self, platform: str, channel: str = None, channels: list = None, cron_expression: str = None, description: str = None, sort: str = ''):
        with self.session_scope() as session:
            task = TaskSchedule(
                platform=platform, channel=channel,
                channels=json.dumps(channels) if channels else None,
                cron_expression=cron_expression, description=description, enabled=True,
                sort=sort or '',
            )
            session.add(task)
            session.flush()
            return task.to_dict()

    def update_scheduled_task(self, task_id: int, data: dict):
        with self.session_scope() as session:
            task = session.query(TaskSchedule).filter(TaskSchedule.id == task_id).first()
            if not task:
                return None
            for key, value in data.items():
                if hasattr(task, key):
                    setattr(task, key, value)
            session.flush()
            return task.to_dict()

    def delete_scheduled_task(self, task_id: int) -> bool:
        with self.session_scope() as session:
            task = session.query(TaskSchedule).filter(TaskSchedule.id == task_id).first()
            if not task:
                return False
            session.delete(task)
            return True

    def update_scheduled_task_last_run(self, task_id: int):
        with self.session_scope() as session:
            task = session.query(TaskSchedule).filter(TaskSchedule.id == task_id).first()
            if task:
                task.last_run_at = utc_plus_8()

    # ==================== 频道管理 ====================

    def list_categories(self, enabled_only=False):
        with self.session_scope() as session:
            query = session.query(AdminCategory)
            if enabled_only:
                query = query.filter(AdminCategory.enabled == True)
            query = query.order_by(AdminCategory.sort_order, AdminCategory.id)
            return [c.to_dict() for c in query.all()]

    def get_category(self, category_id):
        with self.session_scope() as session:
            category = session.query(AdminCategory).filter(AdminCategory.id == category_id).first()
            return category.to_dict() if category else None

    def get_category_by_key(self, key):
        with self.session_scope() as session:
            category = session.query(AdminCategory).filter(AdminCategory.key == key).first()
            return category.to_dict() if category else None

    def create_category(self, key, name, icon=None, description=None, sort_order=0):
        with self.session_scope() as session:
            category = AdminCategory(key=key, name=name, icon=icon, description=description, sort_order=sort_order, enabled=True)
            session.add(category)
            session.flush()
            return category.to_dict()

    def update_category(self, category_id, data):
        with self.session_scope() as session:
            category = session.query(AdminCategory).filter(AdminCategory.id == category_id).first()
            if not category:
                return None
            for k, v in data.items():
                if hasattr(category, k):
                    setattr(category, k, v)
            session.flush()
            return category.to_dict()

    def delete_category(self, category_id):
        with self.session_scope() as session:
            category = session.query(AdminCategory).filter(AdminCategory.id == category_id).first()
            if not category:
                return False
            session.delete(category)
            return True

    # ==================== 平台管理 ====================

    def list_platforms(self, enabled_only=False):
        with self.session_scope() as session:
            query = session.query(AdminPlatform)
            if enabled_only:
                query = query.filter(AdminPlatform.enabled == True)
            query = query.order_by(AdminPlatform.sort_order, AdminPlatform.id)
            return [p.to_dict() for p in query.all()]

    def get_platform(self, platform_id):
        with self.session_scope() as session:
            platform = session.query(AdminPlatform).filter(AdminPlatform.id == platform_id).first()
            return platform.to_dict() if platform else None

    def get_platform_by_key(self, key):
        with self.session_scope() as session:
            platform = session.query(AdminPlatform).filter(AdminPlatform.key == key).first()
            return platform.to_dict() if platform else None

    def create_platform(self, key, name, official_site=None, spider=None, rate_limit=1.0, timeout=15, icon=None, 
                         user_agent=None, keywords=None, config=None, sort_order=0):
        with self.session_scope() as session:
            platform = AdminPlatform(
                key=key, name=name, spider=spider,
                official_site=official_site, rate_limit=rate_limit,
                timeout=timeout, icon=icon, user_agent=user_agent,
                keywords=json.dumps(keywords, ensure_ascii=False) if keywords else None,
                config=json.dumps(config, ensure_ascii=False) if config else None,
                sort_order=sort_order, enabled=True
            )
            session.add(platform)
            session.flush()
            return platform.to_dict()

    def update_platform(self, platform_id, data):
        with self.session_scope() as session:
            platform = session.query(AdminPlatform).filter(AdminPlatform.id == platform_id).first()
            if not platform:
                return None
            for k, v in data.items():
                if hasattr(platform, k):
                    if k in ['keywords', 'config', 'positive_keywords', 'trailer_keywords', 'bts_keywords', 'extra_config']:
                        if v is not None:
                            setattr(platform, k, json.dumps(v, ensure_ascii=False))
                        else:
                            setattr(platform, k, None)
                    else:
                        setattr(platform, k, v)
            session.flush()
            return platform.to_dict()

    def delete_platform(self, platform_id):
        with self.session_scope() as session:
            platform = session.query(AdminPlatform).filter(AdminPlatform.id == platform_id).first()
            if not platform:
                return False
            session.delete(platform)
            return True

    # ==================== 平台频道配置 ====================

    def list_platform_channels(self, category_id=None, platform_id=None, enabled_only=False):
        with self.session_scope() as session:
            query = session.query(AdminPlatformChannel)
            if category_id:
                query = query.filter(AdminPlatformChannel.category_id == category_id)
            if platform_id:
                query = query.filter(AdminPlatformChannel.platform_id == platform_id)
            if enabled_only:
                query = query.filter(AdminPlatformChannel.enabled == True)
            query = query.order_by(AdminPlatformChannel.sort_order, AdminPlatformChannel.id)
            return [pc.to_dict() for pc in query.all()]

    def get_platform_channel(self, pc_id):
        with self.session_scope() as session:
            pc = session.query(AdminPlatformChannel).filter(AdminPlatformChannel.id == pc_id).first()
            return pc.to_dict() if pc else None
    
    def get_platform_channel_by_platform_and_key(self, platform_id, channel_key):
        with self.session_scope() as session:
            pc = session.query(AdminPlatformChannel).filter(
                AdminPlatformChannel.platform_id == platform_id,
                AdminPlatformChannel.channel_key == channel_key
            ).first()
            return pc.to_dict() if pc else None

    def create_platform_channel(self, platform_id, category_id, channel_key, channel_name, url, output_table='series', channel_id=None, sort_order=0, config=None, enabled=True):
        with self.session_scope() as session:
            pc = AdminPlatformChannel(
                platform_id=platform_id, category_id=category_id,
                channel_key=channel_key, channel_name=channel_name,
                url=url, output_table=output_table,
                channel_id=channel_id, sort_order=sort_order,
                config=json.dumps(config, ensure_ascii=False) if config else None,
                enabled=enabled
            )
            session.add(pc)
            session.flush()
            return pc.to_dict()

    def update_platform_channel(self, pc_id, data):
        with self.session_scope() as session:
            pc = session.query(AdminPlatformChannel).filter(AdminPlatformChannel.id == pc_id).first()
            if not pc:
                return None
            for k, v in data.items():
                if hasattr(pc, k):
                    setattr(pc, k, v)
            session.flush()
            return pc.to_dict()

    def delete_platform_channel(self, pc_id):
        """删除平台频道配置"""
        with self.session_scope() as session:
            pc = session.query(PlatformChannel).filter(PlatformChannel.id == pc_id).first()
            if not pc:
                return False
            session.delete(pc)
            return True
    
    # ==================== 解析源管理 ====================
    
    def list_parse_sources(self, enabled_only=False, platform_id=None):
        """获取解析源列表"""
        with self.session_scope() as session:
            query = session.query(ParseSource)
            if enabled_only:
                query = query.filter(ParseSource.enabled == True)
            if platform_id is not None:
                query = query.filter(ParseSource.platform_id == platform_id)
            query = query.order_by(ParseSource.sort_order, ParseSource.id)
            return [ps.to_dict() for ps in query.all()]
    
    def get_parse_source(self, ps_id):
        """获取单个解析源"""
        with self.session_scope() as session:
            ps = session.query(ParseSource).filter(ParseSource.id == ps_id).first()
            return ps.to_dict() if ps else None
    
    def get_parse_source_by_key(self, key):
        """通过 key 获取解析源"""
        with self.session_scope() as session:
            ps = session.query(ParseSource).filter(ParseSource.key == key).first()
            return ps.to_dict() if ps else None
    
    def create_parse_source(self, key, name, url, sort_order=0, platform_id=None, type='json'):
        """创建解析源"""
        with self.session_scope() as session:
            ps = ParseSource(
                key=key,
                name=name,
                type=type,
                url=url,
                platform_id=platform_id,
                sort_order=sort_order,
                enabled=True
            )
            session.add(ps)
            session.flush()
            return ps.to_dict()
    
    def update_parse_source(self, ps_id, data):
        """更新解析源"""
        with self.session_scope() as session:
            ps = session.query(ParseSource).filter(ParseSource.id == ps_id).first()
            if not ps:
                return None
            for k, v in data.items():
                if hasattr(ps, k):
                    setattr(ps, k, v)
            session.flush()
            return ps.to_dict()
    
    def delete_parse_source(self, ps_id):
        """删除解析源"""
        with self.session_scope() as session:
            ps = session.query(ParseSource).filter(ParseSource.id == ps_id).first()
            if not ps:
                return False
            session.delete(ps)
            return True


# 全局默认实例
db = DatabaseManager()

# 向后兼容：类方法委托到全局实例
_instance_methods = {
    'save_series': db.save_series,
    'save_episodes': db.save_episodes,
    'get_series_by_cid': db.get_series_by_cid,
    'get_series_with_episodes': db.get_series_with_episodes,
    'find_series_with_episodes_by_cid': db.find_series_with_episodes_by_cid,
    'list_series': db.list_series,
    'list_series_all': db.list_series_all,
    'search_series_all': db.search_series_all,
    'update_series_episodes_count': db.update_series_episodes_count,
    'create_crawl_task': db.create_crawl_task,
    'start_crawl_task': db.start_crawl_task,
    'complete_crawl_task': db.complete_crawl_task,
    'clear_all_data': db.clear_all_data,
    'clear_platform_data': db.clear_platform_data,
    'get_stats': db.get_stats,

    'admin_create_series': db.admin_create_series,
    'admin_update_series': db.admin_update_series,
    'get_series_by_id': db.get_series_by_id,
    'list_episodes': db.list_episodes,
    'admin_create_episode': db.admin_create_episode,
    'admin_update_episode': db.admin_update_episode,
    'delete_episode': db.delete_episode,
    'list_crawl_tasks': db.list_crawl_tasks,
    'list_scheduled_tasks': db.list_scheduled_tasks,
    'get_scheduled_task': db.get_scheduled_task,
    'create_scheduled_task': db.create_scheduled_task,
    'update_scheduled_task': db.update_scheduled_task,
    'delete_scheduled_task': db.delete_scheduled_task,
    'update_scheduled_task_last_run': db.update_scheduled_task_last_run,
    'list_categories': db.list_categories,
    'get_category': db.get_category,
    'get_category_by_key': db.get_category_by_key,
    'create_category': db.create_category,
    'update_category': db.update_category,
    'delete_category': db.delete_category,
    'list_platforms': db.list_platforms,
    'get_platform': db.get_platform,
    'get_platform_by_key': db.get_platform_by_key,
    'create_platform': db.create_platform,
    'update_platform': db.update_platform,
    'delete_platform': db.delete_platform,
    'list_platform_channels': db.list_platform_channels,
    'create_platform_channel': db.create_platform_channel,
    'update_platform_channel': db.update_platform_channel,
    'delete_platform_channel': db.delete_platform_channel,
    'list_parse_sources': db.list_parse_sources,
    'get_parse_source': db.get_parse_source,
    'get_parse_source_by_key': db.get_parse_source_by_key,
    'create_parse_source': db.create_parse_source,
    'update_parse_source': db.update_parse_source,
    'delete_parse_source': db.delete_parse_source,
    'batch_save_series_and_episodes': db.batch_save_series_and_episodes,
    'get_filter_options': db.get_filter_options,
}


def _make_delegate(method_name):
    method = _instance_methods[method_name]
    @classmethod
    def _class_method(cls, *args, **kwargs):
        return method(*args, **kwargs)
    return _class_method


for _name in _instance_methods:
    setattr(DatabaseManager, _name, _make_delegate(_name))
