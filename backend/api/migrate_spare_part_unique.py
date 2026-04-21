#!/usr/bin/env python3
"""
将 spare_parts 表唯一约束从「MES编码唯一」改为「(MES编码, 货位号) 联合唯一」。
- 删除 mes_material_code 上的 UNIQUE
- 新增 (mes_material_code, location_code) 的 UNIQUE

用法: 在 backend/api 目录下执行
  python migrate_spare_part_unique.py

或在项目根目录:
  python -m backend.api.migrate_spare_part_unique
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text
from app.core.database import engine
from app.core.config import settings


def run():
    # 仅支持 MySQL
    if "mysql" not in settings.DATABASE_URL and "pymysql" not in settings.DATABASE_URL:
        print("当前仅支持 MySQL，请手动执行等效的 ALTER 语句。")
        return

    with engine.connect() as conn:
        trans = conn.begin()
        try:
            # 1. 查出现有 unique 索引名（mes_material_code 上的）
            try:
                r = conn.execute(
                    text("""
                        SELECT INDEX_NAME FROM information_schema.STATISTICS
                        WHERE TABLE_SCHEMA = DATABASE()
                          AND TABLE_NAME = 'spare_parts'
                          AND COLUMN_NAME = 'mes_material_code'
                          AND NON_UNIQUE = 0
                        LIMIT 1
                    """)
                )
                row = r.fetchone()
                idx_name = row[0] if row else "mes_material_code"
            except Exception as e:
                print("查询索引名失败:", e)
                idx_name = "mes_material_code"

            # 2. 删除 mes_material_code 的 UNIQUE（若存在）
            try:
                conn.execute(text(f"ALTER TABLE spare_parts DROP INDEX `{idx_name}`"))
                print(f"已删除 UNIQUE 索引: {idx_name}")
            except Exception as e:
                if "1091" in str(e) or "check that it exists" in str(e).lower():
                    print("未找到 mes_material_code 的 UNIQUE 索引，可能已迁移或表结构不同，跳过。")
                else:
                    raise

            # 3. 新增 (mes_material_code, location_code) 联合 UNIQUE
            try:
                conn.execute(text("""
                    ALTER TABLE spare_parts
                    ADD UNIQUE KEY uq_spare_part_mes_location (mes_material_code, location_code)
                """))
                print("已添加联合唯一约束: uq_spare_part_mes_location (mes_material_code, location_code)")
            except Exception as e:
                if "1061" in str(e) or "Duplicate key name" in str(e):
                    print("联合唯一约束 uq_spare_part_mes_location 已存在，跳过。")
                else:
                    raise

            trans.commit()
        except Exception as e:
            trans.rollback()
            print("迁移失败:", e)
            raise

    print("迁移完成。")


if __name__ == "__main__":
    run()
