"""
初始化数据库基础数据

运行方式：cd server && python scripts/init_db.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import DatabaseManager
from models import get_session, VipPlan, VipPlanConfig, PayQrcode, AdminCategory, AdminPlatform, AdminPlatformChannel


def init_categories():
    """初始化频道数据"""
    print("\n=== 初始化频道数据 ===")
    categories = [
        {"key": "tv", "name": "电视剧", "sort_order": 1},
        {"key": "movie", "name": "电影", "sort_order": 2},
        {"key": "variety", "name": "综艺", "sort_order": 3},
        {"key": "cartoon", "name": "动漫", "sort_order": 4},
        {"key": "child", "name": "少儿", "sort_order": 5},
        {"key": "free", "name": "免费", "sort_order": 6},
    ]

    with get_session() as session:
        for cat_data in categories:
            existing = session.query(AdminCategory).filter(AdminCategory.key == cat_data["key"]).first()
            if not existing:
                cat = AdminCategory(**cat_data, enabled=True)
                session.add(cat)
                print(f"  新增频道: {cat_data['name']}")
            else:
                print(f"  频道已存在: {cat_data['name']}")
        session.commit()
    print("  OK 频道数据初始化完成")


def init_platforms():
    """初始化平台数据"""
    print("\n=== 初始化平台数据 ===")
    platforms = [
        {"key": "tencent", "name": "腾讯视频", "spider": "spiders.tencent_spider.TencentSpider", "sort_order": 1},
        {"key": "iqiyi", "name": "爱奇艺", "spider": "spiders.iqiyi_spider.IqiyiSpider", "sort_order": 2},
        {"key": "youku", "name": "优酷", "spider": "spiders.youku_spider.YoukuSpider", "sort_order": 3},
        {"key": "mgtv", "name": "芒果TV", "spider": "spiders.mgtv_spider.MgtvSpider", "sort_order": 4},
        {"key": "sohu", "name": "搜狐视频", "spider": "spiders.sohu_spider.SohuSpider", "sort_order": 5},
        {"key": "bilibili", "name": "哔哩哔哩", "spider": "spiders.bilibili_spider.BilibiliSpider", "sort_order": 6},
    ]

    with get_session() as session:
        for plat_data in platforms:
            existing = session.query(AdminPlatform).filter(AdminPlatform.key == plat_data["key"]).first()
            if not existing:
                plat = AdminPlatform(**plat_data, enabled=True)
                session.add(plat)
                print(f"  新增平台: {plat_data['name']}")
            else:
                print(f"  平台已存在: {plat_data['name']}")
        session.commit()

        # 获取平台的ID，为创建频道关联做准备
        platform_map = {
            p.key: p.id
            for p in session.query(AdminPlatform).all()
        }
        category_map = {
            c.key: c.id
            for c in session.query(AdminCategory).all()
        }

    return platform_map, category_map


def init_platform_channels(platform_map, category_map):
    """初始化平台-频道关联数据"""
    print("\n=== 初始化平台频道关联数据 ===")
    # 为每个平台关联所有的频道
    for platform_key, platform_id in platform_map.items():
        for category_key, category_id in category_map.items():
            with get_session() as session:
                existing = (
                    session.query(AdminPlatformChannel)
                    .filter(
                        AdminPlatformChannel.platform_id == platform_id,
                        AdminPlatformChannel.category_id == category_id
                    )
                    .first()
                )
                if not existing:
                    ch = AdminPlatformChannel(
                        platform_id=platform_id,
                        category_id=category_id,
                        enabled=True
                    )
                    session.add(ch)
        print(f"  平台 {platform_key} 关联所有频道")
    print("  OK 平台频道关联数据初始化完成")


def init_vip_plans():
    """初始化VIP套餐数据"""
    print("\n=== 初始化VIP套餐数据 ===")
    plans = [
        {
            "name": "月度VIP",
            "price": 19.9,
            "original_price": 30.0,
            "duration_days": 30,
            "unit": "约0.66元/天",
            "save_amount": 10.1,
            "is_recommend": False,
            "is_enabled": True,
            "sort_order": 1,
            "plan_type": "formal",
            "duration_type": "monthly",
            "devices": "pc"
        },
        {
            "name": "季度VIP",
            "price": 49.9,
            "original_price": 90.0,
            "duration_days": 90,
            "unit": "约0.55元/天",
            "save_amount": 40.1,
            "is_recommend": True,
            "is_enabled": True,
            "sort_order": 2,
            "plan_type": "formal",
            "duration_type": "quarterly",
            "devices": "pc"
        },
        {
            "name": "年度VIP",
            "price": 149.0,
            "original_price": 360.0,
            "duration_days": 365,
            "unit": "约0.41元/天",
            "save_amount": 211.0,
            "is_recommend": False,
            "is_enabled": True,
            "sort_order": 3,
            "plan_type": "formal",
            "duration_type": "yearly",
            "devices": "pc"
        },
        {
            "name": "永久VIP",
            "price": 399.0,
            "original_price": 999.0,
            "duration_days": 0,
            "unit": "永久有效",
            "save_amount": 600.0,
            "is_recommend": False,
            "is_enabled": True,
            "sort_order": 4,
            "plan_type": "formal",
            "duration_type": "permanent",
            "devices": "pc"
        },
    ]

    with get_session() as session:
        for plan_data in plans:
            existing = session.query(VipPlan).filter(VipPlan.name == plan_data["name"]).first()
            if not existing:
                plan = VipPlan(**plan_data)
                session.add(plan)
                print(f"  新增套餐: {plan_data['name']}")
            else:
                print(f"  套餐已存在: {plan_data['name']}")
        session.commit()
    print("  OK VIP套餐数据初始化完成")


def init_vip_plan_configs():
    """初始化VIP套餐配置"""
    print("\n=== 初始化VIP套餐配置 ===")
    configs = [
        {"plan_type": "formal", "tip_text": "限时特惠，开通即享海量高清内容"},
        {"plan_type": "promotion", "tip_text": "优惠活动进行中，新用户首月仅需9.9元"},
    ]

    with get_session() as session:
        for cfg_data in configs:
            existing = session.query(VipPlanConfig).filter(VipPlanConfig.plan_type == cfg_data["plan_type"]).first()
            if not existing:
                cfg = VipPlanConfig(**cfg_data)
                session.add(cfg)
                print(f"  新增配置: {cfg_data['plan_type']}")
            else:
                existing.tip_text = cfg_data["tip_text"]
                print(f"  更新配置: {cfg_data['plan_type']}")
        session.commit()
    print("  OK VIP套餐配置初始化完成")


def init_pay_qrcodes():
    """初始化支付二维码"""
    print("\n=== 初始化支付二维码 ===")
    qrcodes = [
        {
            "name": "微信支付",
            "type": "wechat",
            "image_url": "/static/wechat_qrcode.png",
            "sort_order": 1
        },
        {
            "name": "支付宝",
            "type": "alipay",
            "image_url": "/static/alipay_qrcode.png",
            "sort_order": 2
        },
    ]

    with get_session() as session:
        for qr_data in qrcodes:
            existing = session.query(PayQrcode).filter(PayQrcode.type == qr_data["type"]).first()
            if not existing:
                qr = PayQrcode(**qr_data, is_enabled=True)
                session.add(qr)
                print(f"  新增二维码: {qr_data['name']}")
            else:
                print(f"  二维码已存在: {qr_data['name']}")
        session.commit()
    print("  OK 支付二维码初始化完成")


def main():
    print("开始初始化数据库基础数据...")
    
    init_categories()
    init_platforms()
    init_vip_plans()
    init_vip_plan_configs()
    init_pay_qrcodes()

    print("\n" + "="*60)
    print("OK 所有基础数据初始化完成！")
    print("="*60)


if __name__ == "__main__":
    main()
