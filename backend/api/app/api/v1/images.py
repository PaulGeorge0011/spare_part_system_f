# app/api/v1/images.py
from fastapi import APIRouter, UploadFile, HTTPException, File, Form, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
#from minio.commonconfig import CopySource
from typing import Optional, List
from datetime import datetime
import uuid
import re
from pathlib import Path
import shutil
import os
import logging
import io

from ...core.config import settings
from ...core.database import get_db
from ...core.datetime_utils import utc_now
from ...utils.minio_client import minio_client
from ...models.image import SparePartImage
from ...schemas.image import (
    TempImageUploadResponse, 
    ImageConfirmResponse,
    ImageDeleteResponse,
    BulkImageConfirmRequest
)
from ...crud.image import (
    create_image_record,
    get_image_by_upload_id,
    confirm_image_record,
    delete_image_record,
    get_images_by_spare_part,
    get_temp_images_by_material
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/images", tags=["图片管理"])


@router.get("/health")
async def images_health():
    """健康检查，用于确认 /images 路由已挂载。无依赖。"""
    return {"ok": True, "service": "images"}


# 本地存储目录（备用）
BASE_DIR = Path("/app")
UPLOAD_DIR = BASE_DIR / settings.IMAGE_UPLOAD_PATH
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

def validate_material_code(material_code: str) -> bool:
    """验证物料编码格式"""
    if not material_code or not material_code.strip():
        return False
    
    pattern = r'^[a-zA-Z0-9_-]{3,50}$'
    return bool(re.match(pattern, material_code))

def validate_image_file(file: UploadFile) -> tuple:
    """验证图片文件"""
    # 验证文件大小
    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)
    
    if file_size > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=400, 
            detail=f"文件大小超过限制 ({file_size} > {settings.MAX_UPLOAD_SIZE})"
        )
    
    # 验证文件扩展名
    file_ext = Path(file.filename).suffix.lower()
    allowed_extensions = [ext.strip() for ext in settings.ALLOWED_IMAGE_EXTENSIONS.split(",")]
    
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件扩展名: {file_ext}"
        )
    
    # 验证MIME类型
    content_type = file.content_type or "application/octet-stream"
    if content_type not in settings.allowed_image_types_list:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型: {content_type}"
        )
    
    return file_size, content_type, file_ext

@router.post("/temp-upload")
async def upload_temp_image(
    file: UploadFile = File(...),
    material_code: str = Form(..., description="MES物料编码")
):
    """临时上传图片（表单提交前）"""
    try:
        # 验证物料编码
        if not validate_material_code(material_code):
            raise HTTPException(
                status_code=400,
                detail="无效的物料编码格式。物料编码只能包含字母、数字、下划线和短横线，长度3-50字符"
            )
        
        # 验证文件
        file_size, content_type, file_ext = validate_image_file(file)
        
        # 上传到MINIO临时存储
        upload_result = minio_client.upload_temp_image(
            file_data=file.file,
            filename=file.filename,
            content_type=content_type,
            material_code=material_code
        )
        
        return TempImageUploadResponse(
            upload_id=upload_result["upload_id"],
            temp_url=upload_result["temp_url"],
            filename=upload_result["filename"],
            material_code=material_code,
            size=file_size
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"临时上传失败: {str(e)}")


@router.post("/download-and-upload")
async def download_and_upload_image(
    image_url: str = Form(..., description="图片URL"),
    material_code: str = Form(..., description="MES物料编码")
):
    """
    从URL下载图片并上传到临时存储（用于批量导入）
    返回upload_id，前端可直接用于创建备件
    """
    try:
        try:
            import httpx
        except ImportError:
            raise HTTPException(
                status_code=503,
                detail="请安装 httpx 后重启服务：pip install httpx"
            )
        # 验证物料编码
        if not validate_material_code(material_code):
            raise HTTPException(
                status_code=400,
                detail="无效的物料编码格式"
            )
        
        # 下载图片
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(image_url, follow_redirects=True)
                response.raise_for_status()
            except httpx.HTTPError as e:
                raise HTTPException(
                    status_code=400,
                    detail=f"下载图片失败: {str(e)}"
                )
            
            # 验证Content-Type
            content_type = response.headers.get("content-type", "")
            if not content_type.startswith("image/"):
                # 尝试从URL扩展名判断
                url_lower = image_url.lower()
                if not any(ext in url_lower for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp']):
                    raise HTTPException(
                        status_code=400,
                        detail="URL指向的不是图片文件"
                    )
                # 如果扩展名是图片但Content-Type不对，使用默认类型
                if '.jpg' in url_lower or '.jpeg' in url_lower:
                    content_type = 'image/jpeg'
                elif '.png' in url_lower:
                    content_type = 'image/png'
                elif '.gif' in url_lower:
                    content_type = 'image/gif'
                elif '.webp' in url_lower:
                    content_type = 'image/webp'
                else:
                    content_type = 'image/jpeg'
            
            # 验证文件大小
            file_size = len(response.content)
            if file_size > settings.MAX_UPLOAD_SIZE:
                raise HTTPException(
                    status_code=400,
                    detail=f"图片文件过大 ({file_size} > {settings.MAX_UPLOAD_SIZE})"
                )
            
            # 从URL提取文件名
            try:
                from urllib.parse import urlparse
                url_path = urlparse(image_url).path
                filename = url_path.split('/')[-1] or f"image_{uuid.uuid4().hex[:8]}.jpg"
            except:
                filename = f"image_{uuid.uuid4().hex[:8]}.jpg"
            
            # 确保文件名有扩展名
            if '.' not in filename:
                ext = content_type.split('/')[1] if '/' in content_type else 'jpg'
                filename = f"{filename}.{ext}"
            
            # 创建文件对象
            file_data = io.BytesIO(response.content)
            
            # 上传到MINIO临时存储
            upload_result = minio_client.upload_temp_image(
                file_data=file_data,
                filename=filename,
                content_type=content_type,
                material_code=material_code
            )
            
            return TempImageUploadResponse(
                upload_id=upload_result["upload_id"],
                temp_url=upload_result["temp_url"],
                filename=upload_result["filename"],
                material_code=material_code,
                size=file_size
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"下载并上传图片失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"处理图片失败: {str(e)}")


@router.post("/confirm")
async def confirm_image(
    upload_id: str = Form(...),
    spare_part_id: Optional[int] = Form(None),
    material_code: str = Form(...),
    image_index: int = Form(0, description="图片索引（0:第一张图片，1:第二张图片）"),
    db: Session = Depends(get_db)
):
    """确认图片（表单提交后，将临时图片转为永久）"""
    try:
        # 从Redis获取临时图片信息
        temp_data = minio_client.redis_client.get_temp_image(upload_id)
        if not temp_data:
            raise HTTPException(status_code=404, detail="临时图片记录不存在或已过期")
        
        # 将临时图片移动到正式目录
        material_code = temp_data["material_code"]
        temp_object_name = temp_data["temp_object_name"]
        
        # 使用毫秒级时间戳 + upload_id 生成唯一文件名
        timestamp = utc_now().strftime("%Y%m%d_%H%M%S_%f")
        file_ext = Path(temp_data["filename"]).suffix.lower()
        
        # 获取upload_id的前8位，确保文件名唯一
        upload_id_short = upload_id[:8]
        
        # 如果有图片索引，在文件名中添加索引标识
        if image_index is not None:
            index_str = f"_img{image_index}"
        else:
            index_str = ""
        
        # 生成唯一文件名：timestamp_uploadid_index.ext
        unique_filename = f"{timestamp}_{upload_id_short}{index_str}{file_ext}"
        
        # 生成正式对象路径 - 使用MES物料编码作为文件夹名称
        permanent_object_name = f"spare-parts/{material_code}/{unique_filename}"
        
        # 方法一：直接复制对象（使用字符串格式的源）
        # 在某些MinIO版本中，可以直接使用字符串作为source
        try:
            minio_client.client.copy_object(
                bucket_name=minio_client.bucket_name,
                object_name=permanent_object_name,
                source=temp_object_name  # 直接使用对象名
            )
        except Exception as copy_error:
            # 如果直接复制失败，使用备用方案：下载后重新上传
            logger.warning(f"直接复制失败，使用备用方案: {copy_error}")
            
            # 下载临时文件
            temp_data_response = minio_client.client.get_object(
                bucket_name=minio_client.bucket_name,
                object_name=temp_object_name
            )
            
            # 读取文件内容
            file_content = temp_data_response.read()
            temp_data_response.close()
            
            # 上传到新位置
            minio_client.client.put_object(
                bucket_name=minio_client.bucket_name,
                object_name=permanent_object_name,
                data=io.BytesIO(file_content),
                length=len(file_content),
                content_type=temp_data["content_type"]
            )
        
        # 删除临时对象
        minio_client.client.remove_object(minio_client.bucket_name, temp_object_name)
        
        # 删除Redis中的临时记录
        minio_client.redis_client.delete_temp_image(upload_id)
        
        # 创建数据库记录
        image_data = {
            "material_code": material_code,
            "filename": unique_filename,  # 使用唯一文件名
            "object_name": permanent_object_name,
            "original_filename": temp_data["original_filename"],
            "content_type": temp_data["content_type"],
            "size": temp_data["size"],
            "upload_id": upload_id,
            "is_temp": False,
            "spare_part_id": spare_part_id,
            "confirmed_at": utc_now().replace(tzinfo=None)
        }
        
        image_record = create_image_record(db, image_data)
        
        # 生成永久访问URL
        permanent_url = minio_client.get_presigned_url(permanent_object_name)
        
        return ImageConfirmResponse(
            upload_id=upload_id,
            object_name=permanent_object_name,
            permanent_url=permanent_url,
            filename=unique_filename,  # 返回唯一文件名
            material_code=material_code,
            spare_part_id=spare_part_id,
            image_index=image_index  # 返回图片索引
        )
        
    except Exception as e:
        import traceback
        logger.error(f"确认图片失败: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"确认图片失败: {str(e)}")
@router.post("/bulk-confirm")
async def bulk_confirm_images(
    request: BulkImageConfirmRequest,
    db: Session = Depends(get_db)
):
    """批量确认图片"""
    try:
        results = []
        failed = []
        
        # 按顺序处理每个上传的图片，确保唯一文件名
        for index, upload_id in enumerate(request.upload_ids):
            try:
                # 从Redis获取临时图片信息
                temp_data = minio_client.redis_client.get_temp_image(upload_id)
                if not temp_data:
                    failed.append({"upload_id": upload_id, "error": "临时图片记录不存在"})
                    continue
                
                # 使用毫秒级时间戳 + upload_id + 索引生成唯一文件名
                timestamp = utc_now().strftime("%Y%m%d_%H%M%S_%f")
                file_ext = Path(temp_data["filename"]).suffix.lower()
                upload_id_short = upload_id[:8]
                
                # 根据索引生成唯一文件名
                unique_filename = f"{timestamp}_{upload_id_short}_img{index}{file_ext}"
                
                # 生成正式对象路径 - 使用MES物料编码作为文件夹名称
                material_code = temp_data["material_code"]
                permanent_object_name = f"spare-parts/{material_code}/{unique_filename}"
                
                # 下载并重新上传文件
                temp_data_response = minio_client.client.get_object(
                    bucket_name=minio_client.bucket_name,
                    object_name=temp_data["temp_object_name"]
                )
                
                file_content = temp_data_response.read()
                temp_data_response.close()
                
                # 上传到永久位置
                minio_client.client.put_object(
                    bucket_name=minio_client.bucket_name,
                    object_name=permanent_object_name,
                    data=io.BytesIO(file_content),
                    length=len(file_content),
                    content_type=temp_data["content_type"]
                )
                
                # 删除临时对象
                minio_client.client.remove_object(minio_client.bucket_name, temp_data["temp_object_name"])
                
                # 删除Redis中的临时记录
                minio_client.redis_client.delete_temp_image(upload_id)
                
                # 创建数据库记录
                image_data = {
                    "material_code": material_code,
                    "filename": unique_filename,
                    "object_name": permanent_object_name,
                    "original_filename": temp_data["original_filename"],
                    "content_type": temp_data["content_type"],
                    "size": temp_data["size"],
                    "upload_id": upload_id,
                    "is_temp": 0,
                    "spare_part_id": request.spare_part_id,
                    "confirmed_at": utc_now().replace(tzinfo=None)
                }
                
                image_record = create_image_record(db, image_data)
                
                # 生成永久访问URL
                permanent_url = minio_client.get_presigned_url(permanent_object_name)
                
                results.append({
                    "upload_id": upload_id,
                    "object_name": permanent_object_name,
                    "permanent_url": permanent_url,
                    "filename": unique_filename,
                    "material_code": material_code,
                    "image_index": index
                })
                
            except Exception as e:
                failed.append({"upload_id": upload_id, "error": str(e)})
        
        db.commit()
        
        return {
            "success": len(failed) == 0,
            "message": f"成功确认 {len(results)} 张图片，失败 {len(failed)} 张",
            "confirmed": results,
            "failed": failed
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批量确认失败: {str(e)}")
    

@router.delete("/temp/{upload_id}")
async def delete_temp_image(upload_id: str):
    """删除临时图片"""
    try:
        # 从Redis获取临时图片信息
        temp_data = minio_client.redis_client.get_temp_image(upload_id)
        if not temp_data:
            raise HTTPException(status_code=404, detail="临时图片不存在或已过期")
        
        # 从MINIO删除临时对象
        minio_client.client.remove_object(
            minio_client.bucket_name,
            temp_data["temp_object_name"]
        )
        
        # 从Redis删除记录
        minio_client.redis_client.delete_temp_image(upload_id)
        
        return {"success": True, "message": "临时图片已删除"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除临时图片失败: {str(e)}")

@router.get("/temp/{upload_id}")
async def get_temp_image(upload_id: str):
    """根据upload_id获取临时图片的URL"""
    try:
        # 从Redis获取临时图片信息
        temp_data = minio_client.redis_client.get_temp_image(upload_id)
        if not temp_data:
            raise HTTPException(status_code=404, detail="临时图片记录不存在或已过期")
        
        # 重新生成临时图片的预签名URL，确保URL有效
        temp_url = minio_client.get_presigned_url(temp_data["temp_object_name"])
        
        return {
            "upload_id": upload_id,
            "temp_url": temp_url,
            "filename": temp_data["filename"],
            "material_code": temp_data["material_code"],
            "size": temp_data["size"]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取临时图片失败: {str(e)}")

@router.post("/temp/batch")
async def get_temp_images_batch(upload_ids: List[str]):
    """批量获取临时图片的URL"""
    try:
        images = []
        for upload_id in upload_ids:
            temp_data = minio_client.redis_client.get_temp_image(upload_id)
            if temp_data:
                # 重新生成临时图片的预签名URL
                temp_url = minio_client.get_presigned_url(temp_data["temp_object_name"])
                temp_data["temp_url"] = temp_url
                minio_client.redis_client.set_temp_image(upload_id, temp_data)
                
                images.append({
                    "upload_id": upload_id,
                    "temp_url": temp_url,
                    "filename": temp_data["filename"],
                    "material_code": temp_data["material_code"],
                    "size": temp_data["size"]
                })
        return {"images": images}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批量获取临时图片失败: {str(e)}")

@router.get("/by-spare-part/{spare_part_id}")
async def get_spare_part_images(
    spare_part_id: int,
    db: Session = Depends(get_db)
):
    """获取备件的所有图片（包括临时和永久）"""
    try:
        images = get_images_by_spare_part(db, spare_part_id)
        
        result = []
        for image in images:
            if image.is_temp == 0:  # 永久图片
                url = minio_client.get_presigned_url(image.object_name)
            else:  # 临时图片
                temp_data = minio_client.redis_client.get_temp_image(image.upload_id)
                if temp_data:
                    # 重新生成临时图片URL
                    url = minio_client.get_presigned_url(temp_data["temp_object_name"])
                else:
                    url = ""  # 临时图片已过期
            
            result.append({
                "id": image.id,
                "filename": image.filename,
                "url": url,
                "object_name": image.object_name,
                "is_temp": bool(image.is_temp),
                "size": image.size,
                "uploaded_at": image.uploaded_at,
                "confirmed_at": image.confirmed_at
            })
        
        return {"images": result}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取图片失败: {str(e)}")
@router.get("/by-material/{material_code}")
async def get_images_by_material(material_code: str):
    """根据物料编码获取图片"""
    try:
        # 从MINIO获取图片
        prefix = f"{settings.IMAGE_UPLOAD_PREFIX}{material_code}/"
        objects = minio_client.client.list_objects(
            bucket_name=minio_client.bucket_name,
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
                "url": minio_client.get_presigned_url(obj.object_name)
            })
        
        return {"images": images}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取图片失败: {str(e)}")

@router.delete("/permanent/{image_id}")
async def delete_permanent_image(
    image_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """删除永久图片"""
    try:
        # 获取图片记录
        image_record = db.query(SparePartImage).filter(SparePartImage.id == image_id).first()
        if not image_record:
            raise HTTPException(status_code=404, detail="图片不存在")
        
        # 从MINIO删除图片文件
        object_name = image_record.object_name
        minio_client.client.remove_object(minio_client.bucket_name, object_name)
        
        # 从数据库删除记录
        db.delete(image_record)
        db.commit()
        
        return ImageDeleteResponse(
            success=True,
            message="图片删除成功",
            deleted_ids=[image_id],
            deleted_objects=[object_name]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"删除图片失败: {str(e)}")

@router.delete("/bulk")
async def bulk_delete_images(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    image_ids: List[int] = Form(...)
):
    """批量删除图片"""
    try:
        deleted_ids = []
        deleted_objects = []
        
        for image_id in image_ids:
            # 获取图片记录
            image_record = db.query(SparePartImage).filter(SparePartImage.id == image_id).first()
            if not image_record:
                continue
            
            # 从MINIO删除图片文件
            object_name = image_record.object_name
            if image_record.is_temp == 0:  # 永久图片
                minio_client.client.remove_object(minio_client.bucket_name, object_name)
            else:  # 临时图片
                minio_client.delete_temp_image(image_record.upload_id)
            
            # 从数据库删除记录
            db.delete(image_record)
            deleted_ids.append(image_id)
            deleted_objects.append(object_name)
        
        db.commit()
        
        return ImageDeleteResponse(
            success=True,
            message=f"成功删除 {len(deleted_ids)} 张图片",
            deleted_ids=deleted_ids,
            deleted_objects=deleted_objects
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"批量删除失败: {str(e)}")

@router.post("/upload")
async def upload_image_direct(
    file: UploadFile = File(...),
    material_code: str = Form(..., description="MES物料编码"),
    spare_part_id: Optional[int] = Form(None)
):
    """直接上传图片（兼容旧接口）"""
    try:
        # 验证物料编码
        if not validate_material_code(material_code):
            raise HTTPException(
                status_code=400,
                detail="无效的物料编码格式"
            )
        
        # 验证文件
        file_size, content_type, file_ext = validate_image_file(file)
        
        # 生成唯一文件名：时间戳（毫秒）+ 随机字符串
        timestamp = utc_now().strftime("%Y%m%d_%H%M%S_%f")
        random_str = str(uuid.uuid4())[:8]
        safe_filename = f"{material_code}_{timestamp}_{random_str}{file_ext}"
        
        # 直接上传到MINIO正式目录 - 使用MES物料编码作为文件夹名称
        object_name = f"spare-parts/{material_code}/{safe_filename}"
        
        file.file.seek(0, 2)
        file_size = file.file.tell()
        file.file.seek(0)
        
        minio_client.client.put_object(
            bucket_name=minio_client.bucket_name,
            object_name=object_name,
            data=file.file,
            length=file_size,
            content_type=content_type
        )
        
        # 生成访问URL
        url = minio_client.get_presigned_url(object_name)
        
        return {
            "message": "上传成功",
            "filename": safe_filename,
            "object_name": object_name,
            "url": url,
            "size": file_size,
            "material_code": material_code,
            "spare_part_id": spare_part_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"上传失败: {str(e)}")