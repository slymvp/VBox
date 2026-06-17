"""
添加用户套餐关联表
"""
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from models import engine, get_session

def migrate():
    """执行迁移"""
    print("开始迁移：添加用户套餐关联表...")

    with engine.connect() as conn:
        # 检查表是否已存在
        result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='user_vip_plan'"))
        if result.fetchone():
            print("表 user_vip_plan 已存在，跳过创建")
            return

        # 创建用户套餐关联表
        conn.execute(text("""
            CREATE TABLE user_vip_plan (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                plan_id INTEGER NOT NULL,
                terminal VARCHAR(20),
                activated_at DATETIME,
                expire_at DATETIME,
                created_at DATETIME,
                FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE,
                FOREIGN KEY (plan_id) REFERENCES vip_plan(id)
            )
        """))

        # 创建索引
        conn.execute(text("CREATE INDEX idx_user_vip_plan_user ON user_vip_plan(user_id)"))
        conn.execute(text("CREATE INDEX idx_user_vip_plan_plan ON user_vip_plan(plan_id)"))

        conn.commit()
        print("[OK] 迁移完成：用户套餐关联表创建成功")

if __name__ == "__main__":
    migrate()
