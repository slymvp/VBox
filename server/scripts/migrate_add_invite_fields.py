"""
添加用户邀请相关字段
"""
import sys
import os
import random
import string

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from models import engine, get_session, User


def generate_invite_code(length: int = 6) -> str:
    """生成随机邀请码（6位纯数字）"""
    chars = string.digits
    return ''.join(random.choices(chars, k=length))


def migrate():
    """执行迁移"""
    print("开始迁移：添加用户邀请相关字段...")

    with engine.connect() as conn:
        # 检查字段是否已存在
        result = conn.execute(text("PRAGMA table_info(user)"))
        columns = [row[1] for row in result.fetchall()]

        # 添加 invite_code 字段
        if 'invite_code' not in columns:
            print("添加 invite_code 字段...")
            conn.execute(text("ALTER TABLE user ADD COLUMN invite_code VARCHAR(20)"))
            conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS idx_user_invite_code ON user(invite_code)"))
            conn.commit()
            print("[OK] invite_code 字段添加成功")
        else:
            print("[SKIP] invite_code 字段已存在")

        # 添加 invited_by 字段
        if 'invited_by' not in columns:
            print("添加 invited_by 字段...")
            conn.execute(text("ALTER TABLE user ADD COLUMN invited_by INTEGER"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_user_invited_by ON user(invited_by)"))
            conn.commit()
            print("[OK] invited_by 字段添加成功")
        else:
            print("[SKIP] invited_by 字段已存在")

        # 添加 points 字段
        if 'points' not in columns:
            print("添加 points 字段...")
            conn.execute(text("ALTER TABLE user ADD COLUMN points INTEGER DEFAULT 0"))
            conn.commit()
            print("[OK] points 字段添加成功")
        else:
            print("[SKIP] points 字段已存在")

    # 为现有用户生成邀请码
    print("为现有用户生成邀请码...")
    with get_session() as session:
        users = session.query(User).filter(User.invite_code == None).all()
        for user in users:
            new_code = generate_invite_code()
            while session.query(User).filter(User.invite_code == new_code).first():
                new_code = generate_invite_code()
            user.invite_code = new_code
        session.commit()
        print(f"[OK] 已为 {len(users)} 个用户生成邀请码")

    print("迁移完成！")


if __name__ == "__main__":
    migrate()
