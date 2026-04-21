# test_import.py
import sys
print("Testing imports...")

# 单独测试sqlalchemy的Decimal导入
from sqlalchemy.types import DECIMAL as Decimal
print("✓ Decimal import OK")

# 测试数据库连接和模型定义
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import declarative_base

Base = declarative_base()
class TestModel(Base):
    __tablename__ = 'test_table'
    id = Column(Integer, primary_key=True)
    value = Column(String(50))

engine = create_engine('sqlite:///:memory:')
Base.metadata.create_all(engine)
print("✓ SQLAlchemy model definition and table creation OK")

print("\nAll tests passed!")