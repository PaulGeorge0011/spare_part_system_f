#!/usr/bin/env python3
"""
将 spare_parts 唯一约束改为「货位号 + 规格型号」，MES 编码可空。
- 删除 (mes_material_code, location_code) 的 UNIQUE
- mes_material_code 改为可空、默认空串
- 规格型号为 NULL 的置为空串以便唯一
- 新增 (location_code, specification_model) 的 UNIQUE

用法: 在 backend/api 目录下执行
  python migrate_spare_part_loc_spec.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text
from app.core.database import engine
from app.core.config import settings


def run():
    url = (settings.DATABASE_URL or "").lower()
    if "mysql" in url or "pymysql" in url:
        _run_mysql()
    elif "sqlite" in url:
        _run_sqlite()
    else:
        print("请对当前数据库手动执行等效 ALTER：删除 uq_spare_part_mes_location，"
              "mes_material_code 可空默认 ''，新增 uq_spare_part_loc_spec (location_code, specification_model)。")


def _run_mysql():
    with engine.connect() as conn:
        trans = conn.begin()
        try:
            # 1. 删除旧联合唯一 (mes_material_code, location_code)
            try:
                conn.execute(text("ALTER TABLE spare_parts DROP INDEX uq_spare_part_mes_location"))
                print("已删除旧唯一约束: uq_spare_part_mes_location")
            except Exception as e:
                if "1091" in str(e) or "check that it exists" in str(e).lower():
                    print("旧唯一约束不存在或已删除，跳过。")
                else:
                    raise

            # 2. 规格型号为 NULL 的置为空串，避免唯一约束下多行 (loc, NULL)
            conn.execute(text("UPDATE spare_parts SET specification_model = '' WHERE specification_model IS NULL"))
            print("已将 specification_model 为 NULL 的置为空串。")

            # 3. mes_material_code 改为可空、默认空串
            try:
                conn.execute(text("""
                    ALTER TABLE spare_parts
                    MODIFY COLUMN mes_material_code VARCHAR(100) NULL DEFAULT ''
                """))
                print("已设置 mes_material_code 可空、默认 ''。")
            except Exception as e:
                print("修改 mes_material_code 时出错（可能已改过）:", e)

            # 4. 新增 (location_code, specification_model) 联合唯一
            try:
                conn.execute(text("""
                    ALTER TABLE spare_parts
                    ADD UNIQUE KEY uq_spare_part_loc_spec (location_code, specification_model)
                """))
                print("已添加联合唯一约束: uq_spare_part_loc_spec (location_code, specification_model)")
            except Exception as e:
                if "1061" in str(e) or "Duplicate key name" in str(e):
                    print("唯一约束 uq_spare_part_loc_spec 已存在，跳过。")
                else:
                    raise

            trans.commit()
        except Exception as e:
            trans.rollback()
            print("迁移失败:", e)
            raise
    print("迁移完成。")


def _run_sqlite():
    with engine.connect() as conn:
        trans = conn.begin()
        try:
            try:
                conn.execute(text("DROP INDEX IF EXISTS uq_spare_part_mes_location"))
                print("已删除旧唯一约束（若存在）。")
            except Exception as e:
                print("删除旧约束时:", e)
            conn.execute(text("UPDATE spare_parts SET specification_model = '' WHERE specification_model IS NULL"))
            try:
                conn.execute(text("""
                    CREATE UNIQUE INDEX IF NOT EXISTS uq_spare_part_loc_spec
                    ON spare_parts(location_code, specification_model)
                """))
                print("已添加联合唯一约束 uq_spare_part_loc_spec。")
            except Exception as e:
                print("添加新约束时:", e)
            trans.commit()
        except Exception as e:
            trans.rollback()
            raise
    print("迁移完成。（SQLite 下 mes_material_code 可空需手工改表或重建表）")


if __name__ == "__main__":
    run()
