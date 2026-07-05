"""
初始化平台和频道的完整数据
"""
import sys
import os
import json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import get_session, AdminPlatform, AdminCategory, AdminPlatformChannel


def init_platforms_full():
    with get_session() as session:
        # 获取所有平台和分类
        platforms = session.query(AdminPlatform).all()
        categories = session.query(AdminCategory).all()
        
        # 定义默认的关键词配置
        default_keywords = {
            "positive": ["正片", "第"],
            "trailer": ["预告", "trailer", "teaser", "先导", "前瞻", "片花", "抢先看", "抢先版", "预告片"],
            "bts": ["花絮", "特辑", "独家", "幕后", "制作", "精彩片段", "精彩看点", "加更", "纯享", "尊享", 
                   "未删减", "加长版", "导演版", "彩蛋", "购物车", "小剧场", "番外", "探班", "片场", 
                   "NG", "ng", "路透", "采访", "发布会", "见面会", "开机", "杀青", "剧照", "MV", 
                   "主题曲", "片尾曲", "插曲", "高能", "看点", "策划", "企划", "陪看", 
                   "专访", "访谈", "纪录片", "特别篇", "精彩内容", "人物特辑", "制作特辑", "幕后花絮", 
                   "独家揭秘", "独家探班", "独家专访", "OST", "ost", "先导片", "宣传片"],
            "ongoing": ["更新至", "连载", "更新中", "每周", "每日", "每周更新", "每日更新", "正在更新"]
        }
        
        # 更新平台的关键词配置
        for platform in platforms:
            if not platform.keywords:
                platform.keywords = json.dumps(default_keywords, ensure_ascii=False)
                print(f"为 {platform.name} 设置了默认关键词配置")
        
        session.commit()
        print("平台关键词配置更新完成！")
        
        # 现在创建平台频道关联数据
        category_map = {c.key: c for c in categories}
        
        # 平台默认频道配置
        platform_channel_configs = {
            "tencent": {
                "tv": {"name": "电视剧", "url": "https://v.qq.com/channel/tv"},
                "movie": {"name": "电影", "url": "https://v.qq.com/channel/movie"},
                "variety": {"name": "综艺", "url": "https://v.qq.com/channel/variety"},
                "cartoon": {"name": "动漫", "url": "https://v.qq.com/channel/cartoon"},
                "child": {"name": "少儿", "url": "https://v.qq.com/channel/child"},
                "free": {"name": "免费", "url": "https://v.qq.com/channel/free"},
            },
            "iqiyi": {
                "tv": {"name": "电视剧", "url": "https://www.iqiyi.com/dianshiju/"},
                "movie": {"name": "电影", "url": "https://www.iqiyi.com/dianying/"},
                "variety": {"name": "综艺", "url": "https://www.iqiyi.com/zongyi/"},
                "cartoon": {"name": "动漫", "url": "https://www.iqiyi.com/dongman/"},
                "child": {"name": "少儿", "url": "https://www.iqiyi.com/shaoer/"},
                "free": {"name": "免费", "url": "https://www.iqiyi.com/free/"},
            },
            "youku": {
                "tv": {"name": "电视剧", "url": "https://list.youku.com/category/show/c_97.html"},
                "movie": {"name": "电影", "url": "https://list.youku.com/category/show/c_96.html"},
                "variety": {"name": "综艺", "url": "https://list.youku.com/category/show/c_85.html"},
                "cartoon": {"name": "动漫", "url": "https://list.youku.com/category/show/c_100.html"},
                "child": {"name": "少儿", "url": "https://list.youku.com/category/show/c_99.html"},
                "free": {"name": "免费", "url": "https://list.youku.com/category/show/c_97.html"},
            },
            "mgtv": {
                "tv": {"name": "电视剧", "url": "https://www.mgtv.com/h/112/"},
                "movie": {"name": "电影", "url": "https://www.mgtv.com/h/32/"},
                "variety": {"name": "综艺", "url": "https://www.mgtv.com/h/113/"},
                "cartoon": {"name": "动漫", "url": "https://www.mgtv.com/h/114/"},
                "child": {"name": "少儿", "url": "https://www.mgtv.com/h/115/"},
                "free": {"name": "免费", "url": "https://www.mgtv.com/h/112/"},
            },
            "bilibili": {
                "tv": {"name": "电视剧", "url": "https://www.bilibili.com/guochuang/"},
                "movie": {"name": "电影", "url": "https://www.bilibili.com/movie/"},
                "variety": {"name": "综艺", "url": "https://www.bilibili.com/variety/"},
                "cartoon": {"name": "动漫", "url": "https://www.bilibili.com/anime/"},
                "child": {"name": "少儿", "url": "https://www.bilibili.com/kids/"},
                "free": {"name": "免费", "url": "https://www.bilibili.com/"},
            }
        }
        
        # 创建平台频道关联
        for platform in platforms:
            platform_key = platform.key
            if platform_key in platform_channel_configs:
                for category_key, channel_info in platform_channel_configs[platform_key].items():
                    category = category_map.get(category_key)
                    if not category:
                        continue
                    
                    # 检查是否已存在
                    existing = session.query(AdminPlatformChannel).filter_by(
                        platform_id=platform.id, 
                        category_id=category.id
                    ).first()
                    
                    if not existing:
                        new_channel = AdminPlatformChannel(
                            platform_id=platform.id,
                            category_id=category.id,
                            channel_key=category_key,
                            channel_name=channel_info["name"],
                            url=channel_info["url"],
                            output_table="series",
                            enabled=True
                        )
                        session.add(new_channel)
                        print(f"为 {platform.name} 添加了 {channel_info['name']} 频道")
                    else:
                        print(f"{platform.name} 的 {channel_info['name']} 频道已存在")
        
        session.commit()
        print("平台频道关联配置完成！")


if __name__ == "__main__":
    init_platforms_full()
