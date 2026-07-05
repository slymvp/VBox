import sqlite3
import os

db_path = os.path.join('data', 'vbox.db')
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 检查所有平台
print('=== 当前数据库中的平台 ===')
cursor.execute('SELECT id, key, name FROM admin_platform ORDER BY id')
platforms = cursor.fetchall()
for p in platforms:
    print(f'平台ID: {p[0]}, key: {p[1]}, 名称: {p[2]}')

# 检查是否有搜狐平台
print('\n=== 检查搜狐平台 ===')
cursor.execute("SELECT id, key, name FROM admin_platform WHERE key = 'sohu' OR name LIKE '%搜狐%'")
sohu_platforms = cursor.fetchall()
if sohu_platforms:
    print('找到搜狐平台:')
    for p in sohu_platforms:
        print(f'  平台ID: {p[0]}, key: {p[1]}, 名称: {p[2]}')
else:
    print('数据库中未找到搜狐平台')

# 检查剧集表中是否有搜狐平台的剧集
print('\n=== 检查剧集表中的搜狐平台数据 ===')
categories = ['tv', 'movie', 'variety', 'cartoon', 'child']
for category in categories:
    table_name = f'admin_series_{category}'
    try:
        cursor.execute(f"SELECT COUNT(*) FROM {table_name} WHERE platform = 'sohu'")
        count = cursor.fetchone()[0]
        print(f'{category}表中搜狐平台剧集数量: {count}')
    except:
        print(f'{category}表不存在或查询失败')

conn.close()