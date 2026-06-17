"""
为定时任务表添加 sort 字段
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from models import engine


def migrate():
    """执行迁移"""
    print("开始迁移：为 task_schedule 表添加 sort 字段...")

    with engine.connect() as conn:
        # 检查列是否已存在
        result = conn.execute(text("PRAGMA table_info(task_schedule)"))
        columns = [row[1] for row in result.fetchall()]

        if 'sort' in columns:
            print("列 sort 已存在，跳过添加")
            return

        # 添加 sort 列
        conn.execute(text("ALTER TABLE task_schedule ADD COLUMN sort VARCHAR(20) DEFAULT ''"))
        conn.commit()
        print("[OK] 迁移完成：task_schedule.sort 添加成功")


if __name__ == "__main__":
    migrate()
