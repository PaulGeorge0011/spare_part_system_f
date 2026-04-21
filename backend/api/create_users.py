#!/usr/bin/env python3
"""
手动创建或重置默认用户的脚本
用法: python create_users.py
"""
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.database import SessionLocal, engine, Base
from app.core.security import get_password_hash, verify_password
from app.models.user import User
from app.crud.user import get_user_by_username

def create_or_reset_users():
    """创建或重置默认用户"""
    # 确保表存在
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        users_to_create = [
            ("admin", "admin123", "admin"),
            ("clerk", "clerk123", "requisition_clerk"),
        ]
        
        for username, password, role in users_to_create:
            existing_user = get_user_by_username(db, username)
            
            if existing_user:
                # 如果用户已存在，更新密码
                existing_user.password_hash = get_password_hash(password)
                existing_user.role = role
                print(f"✅ 更新用户: {username} ({role})")
            else:
                # 创建新用户
                new_user = User(
                    username=username,
                    password_hash=get_password_hash(password),
                    role=role
                )
                db.add(new_user)
                print(f"✅ 创建用户: {username} ({role})")
        
        db.commit()
        print("\n✅ 所有用户操作完成！")
        
        # 验证用户
        print("\n验证用户:")
        for username, password, role in users_to_create:
            user = get_user_by_username(db, username)
            if user:
                is_valid = verify_password(password, user.password_hash)
                status = "✅ 密码正确" if is_valid else "❌ 密码错误"
                print(f"  {username}: {status} (角色: {user.role})")
            else:
                print(f"  {username}: ❌ 用户不存在")
                
    except Exception as e:
        print(f"❌ 错误: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    print("开始创建/重置用户...")
    create_or_reset_users()
