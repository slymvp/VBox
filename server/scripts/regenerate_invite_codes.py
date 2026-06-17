"""
把所有用户邀请码重新生成为6位纯数字
"""
import sys
import os
import random
import string

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import get_session, User


def generate_invite_code(length: int = 6) -> str:
    """生成随机邀请码（6位纯数字）"""
    chars = string.digits
    return ''.join(random.choices(chars, k=length))


def regenerate():
    """重新生成所有用户的邀请码为6位数字"""
    with get_session() as session:
        users = session.query(User).all()
        print(f"共找到 {len(users)} 个用户")
        
        count = 0
        for user in users:
            old_code = user.invite_code
            # 如果已经是6位纯数字，跳过
            if old_code and len(old_code) == 6 and old_code.isdigit():
                continue
            
            # 生成新的6位数字邀请码
            new_code = generate_invite_code()
            while session.query(User).filter(User.invite_code == new_code).first():
                new_code = generate_invite_code()
            
            user.invite_code = new_code
            count += 1
            print(f"  用户 {user.username}: {old_code or '(空)'} → {new_code}")
        
        session.commit()
        print(f"\n完成！共更新 {count} 个用户的邀请码")


if __name__ == "__main__":
    regenerate()
