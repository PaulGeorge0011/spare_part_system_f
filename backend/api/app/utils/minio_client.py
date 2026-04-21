# app/utils/minio_client.py
from minio import Minio
from minio.error import S3Error
from minio.commonconfig import CopySource
from pathlib import Path
import io
from typing import Optional, BinaryIO, Union
from datetime import timedelta

from ..core.datetime_utils import utc_now
import uuid
import hashlib
from ..core.config import settings
import redis
import json
import os 
from fastapi import HTTPException


class RedisClient:
    """Redis客户端封装"""
    def __init__(self):
        self.client = redis.from_url(settings.REDIS_URL, decode_responses=True)
    
    def set_temp_image(self, upload_id: str, data: dict, expire_hours: int = None):
        """存储临时图片信息"""
        if expire_hours is None:
            expire_hours = settings.TEMP_IMAGE_EXPIRE_HOURS
        
        key = f"temp_image:{upload_id}"
        self.client.setex(key, expire_hours * 3600, json.dumps(data))
    
    def get_temp_image(self, upload_id: str) -> Optional[dict]:
        """获取临时图片信息"""
        key = f"temp_image:{upload_id}"
        data = self.client.get(key)
        return json.loads(data) if data else None
    
    def delete_temp_image(self, upload_id: str):
        """删除临时图片信息"""
        key = f"temp_image:{upload_id}"
        self.client.delete(key)
    
    def set_image_mapping(self, spare_part_id: int, image_ids: list):
        """存储备件与图片的映射关系"""
        key = f"spare_part_images:{spare_part_id}"
        self.client.setex(key, 3600, json.dumps(image_ids))  # 1小时过期
    
    def get_image_mapping(self, spare_part_id: int) -> list:
        """获取备件的图片ID列表"""
        key = f"spare_part_images:{spare_part_id}"
        data = self.client.get(key)
        return json.loads(data) if data else []


class MinioClient:
    def __init__(self):
        # 内部连接地址（Docker网络内使用）
        self.internal_endpoint = os.getenv("MINIO_ENDPOINT", "minio:9000")
        
        # 外部访问地址（前端浏览器访问）
        # 优先使用 MINIO_PUBLIC_ENDPOINT 环境变量；未设置时使用 /minio 相对路径（通过 Nginx 代理）
        self.public_endpoint = os.getenv("MINIO_PUBLIC_ENDPOINT", "/minio")
        
        self.access_key = os.getenv("MINIO_ACCESS_KEY", "admin")
        self.secret_key = os.getenv("MINIO_SECRET_KEY", "06002336fwbMINIO")
        self.secure = False  # 本地开发使用 HTTP
        
        # 初始化 MinIO 客户端
        self.client = Minio(
            endpoint=self.internal_endpoint,
            access_key=self.access_key,
            secret_key=self.secret_key,
            secure=self.secure
        )
        
        self.bucket_name = settings.MINIO_BUCKET_NAME
        self.redis_client = RedisClient()
        
        # 确保bucket存在
        self._ensure_bucket_exists()
        # 确保机械备件最终目录前缀存在（与 spare-parts 同级）
        self._ensure_mechanical_prefix_exists()
    
    def _ensure_bucket_exists(self):
        """确保MINIO bucket存在"""
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
                print(f"Bucket '{self.bucket_name}' created successfully")
        except S3Error as e:
            print(f"Error ensuring bucket exists: {e}")
            raise
    
    def _ensure_mechanical_prefix_exists(self):
        """确保机械备件最终目录 spare-parts-machine 在 MinIO 中存在（通过占位对象创建前缀）"""
        try:
            prefix = (getattr(settings, "IMAGE_UPLOAD_PREFIX_MECHANICAL", None) or "spare-parts-machine/").rstrip("/") + "/"
            placeholder_key = f"{prefix}.keep"
            # 若已存在则跳过
            try:
                self.client.stat_object(self.bucket_name, placeholder_key)
                return
            except S3Error:
                pass
            self.client.put_object(
                bucket_name=self.bucket_name,
                object_name=placeholder_key,
                data=io.BytesIO(b""),
                length=0,
                content_type="application/octet-stream",
            )
            print(f"MinIO prefix '{prefix}' (spare-parts-machine) created successfully")
        except S3Error as e:
            print(f"Warning: could not ensure mechanical prefix: {e}")
    
    def upload_temp_image(self, file_data: BinaryIO, filename: str, content_type: str, material_code: str) -> dict:
        """上传临时图片到MINIO"""
        try:
            # 生成唯一ID和临时文件名
            upload_id = str(uuid.uuid4())
            timestamp = utc_now().strftime("%Y%m%d_%H%M%S")
            file_ext = Path(filename).suffix.lower()
            
            # 生成临时对象路径（包含upload_id）
            temp_object_name = f"temp/{material_code}_{timestamp}_{upload_id[:8]}{file_ext}"
            
            # 获取文件大小
            file_data.seek(0, 2)
            file_size = file_data.tell()
            file_data.seek(0)
            
            # 上传到MINIO临时目录
            self.client.put_object(
                bucket_name=self.bucket_name,
                object_name=temp_object_name,
                data=file_data,
                length=file_size,
                content_type=content_type
            )
            
            # 生成临时访问URL
            temp_url = self.get_presigned_url(temp_object_name)
            
            # 存储临时图片信息到Redis
            temp_data = {
                "upload_id": upload_id,
                "material_code": material_code,
                "original_filename": filename,
                "temp_object_name": temp_object_name,
                "filename": f"{material_code}_{timestamp}{file_ext}",
                "content_type": content_type,
                "size": file_size,
                "uploaded_at": utc_now().isoformat()
            }
            self.redis_client.set_temp_image(upload_id, temp_data)
            
            return {
                "upload_id": upload_id,
                "temp_object_name": temp_object_name,
                "temp_url": temp_url,
                "filename": temp_data["filename"],
                "size": file_size
            }
            
        except Exception as e:
            raise Exception(f"MINIO upload failed: {e}")
    
    def confirm_temp_image(self, upload_id: str, spare_part_id: Optional[int] = None,
                          image_index: Optional[int] = None,
                          target_prefix: Optional[str] = None) -> dict:
        """确认临时图片，移动到正式目录
        
        Args:
            upload_id: 上传ID
            spare_part_id: 备件ID
            image_index: 图片索引（0表示第一张，1表示第二张），用于生成唯一的文件名
            target_prefix: 目标目录前缀，如 spare-parts/ 或 spare-parts-machine/；不传则用配置的 IMAGE_UPLOAD_PREFIX
        """
        try:
            # 从Redis获取临时图片信息
            temp_data = self.redis_client.get_temp_image(upload_id)
            if not temp_data:
                raise Exception("临时图片记录不存在或已过期")
            
            material_code = temp_data["material_code"]
            temp_object_name = temp_data["temp_object_name"]
            prefix = (target_prefix or settings.IMAGE_UPLOAD_PREFIX).rstrip("/") + "/"
            
            # 生成正式对象路径
            # 使用毫秒级时间戳确保唯一性
            timestamp = utc_now().strftime("%Y%m%d_%H%M%S_%f")
            file_ext = Path(temp_data["filename"]).suffix.lower()
            
            # 使用upload_id确保唯一性，避免重复命名
            upload_id_short = upload_id[:8]
            
            # 如果有图片索引，在文件名中添加索引标识
            if image_index is not None:
                index_str = f"_img{image_index}"
            else:
                index_str = ""
            
            # 生成唯一文件名：timestamp_uploadid_index.ext
            unique_filename = f"{timestamp}_{upload_id_short}{index_str}{file_ext}"
            
            # 根据是否有备件ID决定存储路径（使用指定 prefix，如 spare-parts/ 或 spare-parts-machine/）
            if spare_part_id:
                permanent_object_name = f"{prefix}{spare_part_id}/{unique_filename}"
            else:
                permanent_object_name = f"{prefix}{material_code}/{unique_filename}"
            
            # 复制对象（从临时目录到正式目录）
            self.client.copy_object(
                bucket_name=self.bucket_name,
                object_name=permanent_object_name,
                source=CopySource(self.bucket_name, temp_object_name)
            )
            
            # 删除临时对象
            self.client.remove_object(self.bucket_name, temp_object_name)
            
            # 删除Redis中的临时记录
            self.redis_client.delete_temp_image(upload_id)
            
            # 如果有关联的备件ID，更新映射关系
            if spare_part_id:
                current_images = self.redis_client.get_image_mapping(spare_part_id)
                current_images.append(upload_id)
                self.redis_client.set_image_mapping(spare_part_id, current_images)
            
            # 生成永久访问URL
            permanent_url = self.get_presigned_url(permanent_object_name)
            
            return {
                "object_name": permanent_object_name,
                "url": permanent_url,
                "filename": unique_filename,
                "material_code": material_code,
                "spare_part_id": spare_part_id,
                "upload_id": upload_id,
                "image_index": image_index,
                "content_type": temp_data.get("content_type"),
                "size": temp_data.get("size"),
                "original_filename": temp_data.get("original_filename"),
            }
            
        except Exception as e:
            # 如果失败，尝试删除临时对象
            try:
                if 'temp_object_name' in locals():
                    self.client.remove_object(self.bucket_name, temp_object_name)
            except:
                pass
            raise Exception(f"确认图片失败: {e}")
    
    def delete_temp_image(self, upload_id: str) -> bool:
        """删除临时图片"""
        try:
            # 从Redis获取临时图片信息
            temp_data = self.redis_client.get_temp_image(upload_id)
            if not temp_data:
                return False
            
            # 从MINIO删除临时对象
            self.client.remove_object(self.bucket_name, temp_data["temp_object_name"])
            
            # 从Redis删除记录
            self.redis_client.delete_temp_image(upload_id)
            
            return True
        except Exception as e:
            print(f"删除临时图片失败: {e}")
            return False
    
    def delete_permanent_image(self, object_name: str) -> bool:
        """删除永久图片"""
        try:
            self.client.remove_object(self.bucket_name, object_name)
            return True
        except S3Error as e:
            print(f"删除永久图片失败: {e}")
            return False
    
    def get_presigned_url(self, object_name: str, expires_hours: int = 24) -> str:
        base_url = self.public_endpoint.rstrip('/')
        return f"{base_url}/{self.bucket_name}/{object_name}"
    
    def get_direct_url(self, object_name: str) -> str:
        """生成直接访问的URL（无预签名）"""
        # 直接构建URL，不包含签名参数
        return f"{self.public_endpoint}/{self.bucket_name}/{object_name}"
    
    def list_images_by_material(self, material_code: str) -> list:
        """根据物料编码列出图片"""
        try:
            prefix = f"{settings.IMAGE_UPLOAD_PREFIX}{material_code}/"
            objects = self.client.list_objects(
                bucket_name=self.bucket_name,
                prefix=prefix,
                recursive=True
            )
            
            images = []
            for obj in objects:
                images.append({
                    "object_name": obj.object_name,
                    "filename": Path(obj.object_name).name,
                    "size": obj.size,
                    "last_modified": obj.last_modified,
                    "url": self.get_presigned_url(obj.object_name)
                })
            
            return images
        except S3Error as e:
            raise Exception(f"列出图片失败: {e}")
    
    def list_images_by_spare_part(self, spare_part_id: int) -> list:
        """根据备件ID列出图片"""
        try:
            prefix = f"{settings.IMAGE_UPLOAD_PREFIX}{spare_part_id}/"
            objects = self.client.list_objects(
                bucket_name=self.bucket_name,
                prefix=prefix,
                recursive=True
            )
            
            images = []
            for obj in objects:
                images.append({
                    "object_name": obj.object_name,
                    "filename": Path(obj.object_name).name,
                    "size": obj.size,
                    "last_modified": obj.last_modified,
                    "url": self.get_presigned_url(obj.object_name)
                })
            
            return images
        except S3Error as e:
            print(f"列出备件图片失败: {e}")
            return []
    
    def get_image_info(self, object_name: str) -> dict:
        """获取图片信息"""
        try:
            stat = self.client.stat_object(self.bucket_name, object_name)
            return {
                "object_name": object_name,
                "filename": Path(object_name).name,
                "size": stat.size,
                "content_type": stat.content_type,
                "last_modified": stat.last_modified,
                "url": self.get_presigned_url(object_name)
            }
        except S3Error as e:
            raise HTTPException(status_code=404, detail=f"图片不存在: {object_name}")

# 创建全局MINIO客户端实例
minio_client = MinioClient()