#!/usr/bin/env python3
"""
添加 users.real_name 和 operation_logs.real_name 列。
用于支持用户真实姓名、领用人、操作人展示。

用法: 在 backend/api 目录下执行
  python migrate_add_real_name.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text
from app.core.database import engine
from app.core.config import settings


def run():
    db_url = (settings.DATABASE_URL or "").lower()
    with engine.connect() as conn:
        trans = conn.begin()
        try:
            def add_column_safe(table: str, col_def: str, col_name: str = "real_name"):
                try:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col_def}"))
                    print(f"{table}.{col_name} 已添加")
                except Exception as e:
                    err = str(e).lower()
                    if "duplicate" in err or "already exists" in err:
                        print(f"{table}.{col_name} 已存在，跳过")
                    else:
                        raise

            if "sqlite" in db_url:
                add_column_safe("users", "real_name VARCHAR(100)")
                add_column_safe("operation_logs", "real_name VARCHAR(100)")
            elif "mysql" in db_url or "pymysql" in db_url:
                add_column_safe("users", "real_name VARCHAR(100) NULL COMMENT '真实姓名（领用时作为领用人）'")
                add_column_safe("operation_logs", "real_name VARCHAR(100) NULL COMMENT '操作人真实姓名'")
            elif "postgresql" in db_url:
                conn.execute(text('ALTER TABLE users ADD COLUMN IF NOT EXISTS real_name VARCHAR(100)'))
                conn.execute(text('ALTER TABLE operation_logs ADD COLUMN IF NOT EXISTS real_name VARCHAR(100)'))
                print("real_name 列已添加")
            else:
                print("请手动执行: ALTER TABLE users ADD COLUMN real_name VARCHAR(100);")
                print("            ALTER TABLE operation_logs ADD COLUMN real_name VARCHAR(100);")
                trans.rollback()
                return
            trans.commit()
            print("迁移完成")
        except Exception as e:
            trans.rollback()
            print("迁移失败:", e)
            raise


if __name__ == "__main__":
    run()
