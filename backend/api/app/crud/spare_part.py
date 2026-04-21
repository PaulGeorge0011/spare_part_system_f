# app/crud/spare_part.py
# 增、删、查、改的底层操作定义
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import or_, func
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
import logging

from app.core.datetime_utils import utc_now
from app.models.spare_part import SparePart
from app.models.image import SparePartImage
from app.schemas.spare_part import SparePartCreate, SparePartUpdate
from app.utils.minio_client import minio_client

logger = logging.getLogger(__name__)

def get_spare_part(db: Session, spare_part_id: int) -> Optional[SparePart]:
    """根据ID获取单个备件"""
    return db.query(SparePart).filter(SparePart.id == spare_part_id).first()

def get_spare_part_by_number(db: Session, part_number: str) -> Optional[SparePart]:
    """根据MES物料编码获取备件（若有多个同MES不同货位则返回第一个，用于兼容旧逻辑）"""
    return db.query(SparePart).filter(SparePart.mes_material_code == part_number).first()


def get_spare_part_by_mes_and_location(
    db: Session, mes_material_code: str, location_code: str
) -> Optional[SparePart]:
    """根据 MES 编码 + 货位号 获取备件（用于兼容旧逻辑）"""
    return (
        db.query(SparePart)
        .filter(
            SparePart.mes_material_code == (mes_material_code or ''),
            SparePart.location_code == location_code,
        )
        .first()
    )


def get_spare_part_by_location_and_spec(
    db: Session, location_code: str, specification_model: Optional[str] = None
) -> Optional[SparePart]:
    """根据 货位号 + 规格型号 获取备件（用于查重：货位号与规格型号都相同时视为重复）"""
    loc = (location_code or '').strip()
    spec = (specification_model or '').strip()
    q = db.query(SparePart).filter(SparePart.location_code == loc)
    if spec:
        q = q.filter(SparePart.specification_model == spec)
    else:
        q = q.filter(or_(SparePart.specification_model.is_(None), SparePart.specification_model == ''))
    return q.first()

def _spare_parts_base_query(
    db: Session,
    keyword: Optional[str] = None,
    mes_code: Optional[str] = None,
    brand: Optional[str] = None,
    applicable_model: Optional[str] = None,
    updated_since: Optional[str] = None,
    storage_location: Optional[str] = None,
    location_prefix: Optional[str] = None,
):
    """构建备件列表的过滤查询（不含 order/offset/limit）"""
    query = db.query(SparePart)
    if mes_code:
        query = query.filter(SparePart.mes_material_code == mes_code)
    elif keyword:
        search = f"%{keyword}%"
        query = query.filter(or_(
            SparePart.location_code.ilike(search),
            SparePart.mes_material_code.ilike(search),
            SparePart.mes_material_desc.ilike(search),
            SparePart.physical_material_desc.ilike(search),
            SparePart.specification_model.ilike(search),
            SparePart.applicable_model.ilike(search),
            SparePart.brand.ilike(search),
            SparePart.storage_location.ilike(search),
            SparePart.unit.ilike(search),
            SparePart.remarks.ilike(search),
            SparePart.physical_image_url.ilike(search),
            SparePart.physical_image_url2.ilike(search)
        ))
    if brand and str(brand).strip():
        query = query.filter(SparePart.brand.ilike(f"%{brand.strip()}%"))
    if applicable_model and str(applicable_model).strip():
        query = query.filter(SparePart.applicable_model.ilike(f"%{applicable_model.strip()}%"))
    if storage_location and str(storage_location).strip():
        query = query.filter(SparePart.storage_location.ilike(f"%{storage_location.strip()}%"))
    if location_prefix and str(location_prefix).strip():
        prefix = str(location_prefix).strip().upper()
        query = query.filter(SparePart.location_code.ilike(f"{prefix}%"))
    if updated_since and str(updated_since).strip():
        delta_map = {"1d": 1, "7d": 7, "30d": 30, "6m": 180, "1y": 365}
        days = delta_map.get(str(updated_since).strip().lower())
        if days is not None:
            cutoff = utc_now().replace(tzinfo=None) - timedelta(days=days)
            query = query.filter(SparePart.updated_at >= cutoff)
    return query


def get_spare_parts(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    keyword: Optional[str] = None,
    mes_code: Optional[str] = None,
    brand: Optional[str] = None,
    applicable_model: Optional[str] = None,
    storage_location: Optional[str] = None,
    location_prefix: Optional[str] = None,
    updated_since: Optional[str] = None,
) -> List[SparePart]:
    """获取备件列表，支持关键词及品牌/适用机型/存放地/货位号前缀/更新时间段筛选；按 id 升序返回"""
    base = _spare_parts_base_query(
        db, keyword=keyword, mes_code=mes_code,
        brand=brand, applicable_model=applicable_model,
        storage_location=storage_location, location_prefix=location_prefix,
        updated_since=updated_since,
    )
    return base.order_by(SparePart.id).offset(skip).limit(limit).all()


def get_spare_parts_with_total(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    keyword: Optional[str] = None,
    mes_code: Optional[str] = None,
    brand: Optional[str] = None,
    applicable_model: Optional[str] = None,
    storage_location: Optional[str] = None,
    location_prefix: Optional[str] = None,
    updated_since: Optional[str] = None,
    stock_alert: Optional[str] = None,
) -> Tuple[List[SparePart], int, Optional[int], Optional[int]]:
    """
    获取备件列表及符合条件的总条数，用于分页；支持筛选；按 id 升序返回。
    stock_alert: 可选 "zero"(总库存=0) / "low"(总库存=1)；不传则返回 zero_count、low_count。
    总库存 = mes_stock + physical_stock。返回 (items, total, zero_count, low_count)。
    """
    base = _spare_parts_base_query(
        db, keyword=keyword, mes_code=mes_code,
        brand=brand, applicable_model=applicable_model,
        storage_location=storage_location, location_prefix=location_prefix,
        updated_since=updated_since,
    )
    total_stock_expr = func.coalesce(SparePart.mes_stock, 0) + func.coalesce(SparePart.physical_stock, 0)
    zero_count, low_count = None, None
    if stock_alert == "zero":
        base = base.filter(total_stock_expr == 0)
    elif stock_alert == "low":
        base = base.filter(total_stock_expr == 1)
    else:
        zero_count = base.filter(total_stock_expr == 0).count()
        low_count = base.filter(total_stock_expr == 1).count()
    total = base.count()
    items = base.options(selectinload(SparePart.images)).order_by(SparePart.id).offset(skip).limit(limit).all()
    return items, total, zero_count, low_count


def get_spare_part_filter_options(db: Session) -> Dict[str, List[str]]:
    """
    获取备件筛选下拉选项：品牌、适用机型、存放地、货位号首字符（去重排序）
    优化：使用单次查询获取多个字段的去重值，减少数据库往返
    """
    def _distinct_values(column):
        try:
            q = db.query(column).filter(column.isnot(None), column != "").distinct().order_by(column)
            return sorted({r[0] for r in q.all() if r[0]})
        except Exception as e:
            logger.warning("get_spare_part_filter_options distinct %s: %s", getattr(column, "key", column), e)
            return []
    try:
        brands = _distinct_values(SparePart.brand)
        applicable = _distinct_values(SparePart.applicable_model)
        storage = _distinct_values(SparePart.storage_location)
        spec_models = _distinct_values(SparePart.specification_model)
        locs = [r[0] for r in db.query(SparePart.location_code).filter(SparePart.location_code.isnot(None), SparePart.location_code != "").distinct().all() if r[0]]
        prefixes = sorted(set((s[0].upper() if s else "") for s in locs if s))
    except Exception as e:
        logger.warning("get_spare_part_filter_options: %s", e)
        return {"brands": [], "applicable_models": [], "storage_locations": [], "specification_models": [], "location_prefixes": []}
    return {"brands": brands, "applicable_models": applicable, "storage_locations": storage, "specification_models": spec_models, "location_prefixes": prefixes}


def get_spare_parts_for_requisition(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    keyword: Optional[str] = None,
    brand: Optional[str] = None,
    applicable_model: Optional[str] = None,
    specification_model: Optional[str] = None,
    storage_location: Optional[str] = None,
    location_prefix: Optional[str] = None,
) -> Tuple[List[SparePart], int]:
    """
    备件领用查询：关键词搜规格型号、MES编码、物料描述、适用机型、品牌；
    过滤器：规格型号、适用机型、品牌、存放地、货位号前缀(A/B/C/D等)。
    返回 (列表, 总条数)。
    """
    base = _spare_parts_base_query(
        db,
        keyword=keyword,
        brand=brand,
        applicable_model=applicable_model,
        storage_location=storage_location,
        location_prefix=location_prefix,
    )
    if specification_model and str(specification_model).strip():
        base = base.filter(SparePart.specification_model.ilike(f"%{specification_model.strip()}%"))
    total = base.count()
    items = base.order_by(SparePart.id).offset(skip).limit(limit).all()
    return items, total


def create_spare_part_with_images(
    db: Session, 
    spare_part: SparePartCreate, 
    image_upload_ids: List[str] = None
) -> SparePart:
    """
    创建新的备件记录并关联图片。
    唯一性：货位号 + 规格型号 联合区分，两者都相同时视为重复；MES 编码可空。
    """
    db_item = get_spare_part_by_location_and_spec(
        db, spare_part.location_code, spare_part.specification_model
    )
    if db_item:
        raise ValueError(
            f"货位号 '{spare_part.location_code}' + 规格型号 '{getattr(spare_part, 'specification_model', '') or ''}' 已存在，无法重复创建。"
        )
    
    # 将Pydantic模型转换为字典，再解包给SQLAlchemy模型（MES 可空存空串；规格型号空存空串以便唯一约束）
    spare_part_data = spare_part.model_dump(exclude={"image_upload_ids"}, exclude_unset=True)
    spare_part_data['mes_material_code'] = (spare_part_data.get('mes_material_code') or '').strip() or ''
    spare_part_data['specification_model'] = (spare_part_data.get('specification_model') or '').strip() or ''
    db_spare_part = SparePart(**spare_part_data)
    
    db.add(db_spare_part)
    db.commit()
    db.refresh(db_spare_part)
    
    # 如果有关联的临时图片，确认它们（MES 为空时也可确认）
    if image_upload_ids:
        # 从 app.crud.image 导入函数
        from app.crud.image import get_image_by_upload_id, update_image_record
        
        for index, upload_id in enumerate(image_upload_ids):
            try:
                # 查找图片记录
                image_record = get_image_by_upload_id(db, upload_id)
                if image_record and image_record.is_temp:
                    # 生成图片URL
                    image_url = minio_client.get_presigned_url(image_record.object_name)
                    
                    # ========== 关键修改：更新spare_parts表的对应字段 ==========
                    if index == 0:
                        db_spare_part.physical_image_url = image_url
                    elif index == 1:
                        db_spare_part.physical_image_url2 = image_url
                    
                    # 更新图片记录为永久并关联备件
                    update_data = {
                        "is_temp": False,
                        "spare_part_id": db_spare_part.id,
                        "confirmed_at": utc_now().replace(tzinfo=None)
                    }
                    update_image_record(db, image_record.id, update_data)
                    
            except Exception as e:
                logger.error(f"确认图片失败 {upload_id}: {e}")
    
    # 提交更新后的备件记录
    db.commit()
    db.refresh(db_spare_part)
    
    return db_spare_part

# 保留原有create_spare_part函数以兼容
def create_spare_part(db: Session, spare_part: SparePartCreate) -> SparePart:
    """创建新的备件记录（兼容旧接口）"""
    return create_spare_part_with_images(db, spare_part, [])

def update_spare_part_with_images(
    db: Session,
    db_item: SparePart,
    spare_part_update: SparePartUpdate,
    image_upload_ids: List[str] = None,
    image_ids_to_delete: List[int] = None
) -> SparePart:
    """更新现有备件记录，支持图片操作"""
    # 注意：这里需要处理MES编码更新的唯一性检查
    update_data = spare_part_update.model_dump(exclude_unset=True, exclude={"image_upload_ids", "image_ids_to_delete"})
    
    # 如果更新了MES编码，需要在业务逻辑层检查唯一性
    # 这里我们只更新数据，唯一性检查由路由层处理
    for field, value in update_data.items():
        setattr(db_item, field, value)
    
    # 删除指定的图片
    if image_ids_to_delete:
        # 从 app.crud.image 导入函数
        from app.crud.image import get_image_by_id, delete_image_record
        
        for image_id in image_ids_to_delete:
            # 获取图片记录以便从MINIO删除文件
            image_record = get_image_by_id(db, image_id)
            if image_record:
                # 从MINIO删除文件
                if not image_record.is_temp:  # 永久图片
                    try:
                        minio_client.client.remove_object(minio_client.bucket_name, image_record.object_name)
                    except Exception as e:
                        logger.error(f"删除MINIO文件失败 {image_record.object_name}: {e}")
                else:  # 临时图片
                    minio_client.delete_temp_image(image_record.upload_id)
                
                # ========== 关键修改：清空spare_parts表的对应字段 ==========
                # 检查并清除spare_parts表中的对应URL
                if db_item.physical_image_url and image_record.object_name in db_item.physical_image_url:
                    db_item.physical_image_url = None
                elif db_item.physical_image_url2 and image_record.object_name in db_item.physical_image_url2:
                    db_item.physical_image_url2 = None
                
                # 从数据库删除记录
                delete_image_record(db, image_id)
        # 确保删除操作在后续查询前已写入会话，避免同步时重新拉到已删除记录
        db.flush()
    
    # 确认新的临时图片
    if image_upload_ids:
        from app.crud.image import get_image_by_upload_id, update_image_record
        
        # 获取当前已有的图片数量，用于确定新图片的索引
        existing_images = db.query(SparePartImage).filter(
            SparePartImage.spare_part_id == db_item.id,
            SparePartImage.is_temp == False
        ).all()
        
        # 计算新的图片索引起点
        start_index = len(existing_images)
        
        for i, upload_id in enumerate(image_upload_ids):
            try:
                # 查找图片记录
                image_record = get_image_by_upload_id(db, upload_id)
                if image_record and image_record.is_temp:
                    # 生成图片URL
                    image_url = minio_client.get_presigned_url(image_record.object_name)
                    
                    # 计算当前图片的索引（现有图片数量 + 当前索引）
                    current_index = start_index + i
                    
                    # ========== 关键修改：更新spare_parts表的对应字段 ==========
                    if current_index == 0:
                        db_item.physical_image_url = image_url
                    elif current_index == 1:
                        db_item.physical_image_url2 = image_url
                    
                    # 更新图片记录为永久并关联备件
                    update_data = {
                        "is_temp": False,
                        "spare_part_id": db_item.id,
                        "confirmed_at": utc_now().replace(tzinfo=None)
                    }
                    update_image_record(db, image_record.id, update_data)
                    
            except Exception as e:
                logger.error(f"确认图片失败 {upload_id}: {e}")
    
    # 图片有变更时，同步spare_parts表的URL字段，避免出现“删了/加了但URL字段不更新”的情况
    if image_ids_to_delete or image_upload_ids:
        try:
            sync_spare_part_images(db, db_item.id)
        except Exception as e:
            logger.error(f"同步备件图片字段失败: {e}")
    
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

# 保留原有update_spare_part函数以兼容
def update_spare_part(
    db: Session,
    db_item: SparePart,
    spare_part_update: SparePartUpdate
) -> SparePart:
    """更新现有备件记录（兼容旧接口）"""
    return update_spare_part_with_images(db, db_item, spare_part_update, [], [])

def delete_spare_part_with_images(db: Session, spare_part_id: int) -> Optional[SparePart]:
    """删除备件记录及其关联的图片"""
    db_item = db.query(SparePart).filter(SparePart.id == spare_part_id).first()
    if not db_item:
        return None
    
    # 获取并删除所有关联的图片
    images = db.query(SparePartImage).filter(SparePartImage.spare_part_id == spare_part_id).all()
    
    for image in images:
        try:
            # 从MINIO删除文件
            if not image.is_temp:  # 永久图片
                minio_client.client.remove_object(minio_client.bucket_name, image.object_name)
            else:  # 临时图片
                minio_client.delete_temp_image(image.upload_id)
            
            # 从数据库删除图片记录
            db.delete(image)
        except Exception as e:
            logger.error(f"删除图片失败 {image.id}: {e}")
    
    # 删除备件记录
    db.delete(db_item)
    db.commit()
    
    return db_item

# 保留原有delete_spare_part函数以兼容
def delete_spare_part(db: Session, spare_part_id: int) -> Optional[SparePart]:
    """删除备件记录（兼容旧接口）"""
    return delete_spare_part_with_images(db, spare_part_id)

def get_spare_part_with_images(db: Session, spare_part_id: int) -> Dict[str, Any]:
    """获取备件及其所有图片"""
    spare_part = get_spare_part(db, spare_part_id)
    if not spare_part:
        return None
    
    images = db.query(SparePartImage).filter(SparePartImage.spare_part_id == spare_part_id).all()
    
    # 为图片生成URL
    image_list = []
    for image in images:
        if not image.is_temp:
            url = minio_client.get_presigned_url(image.object_name)
        else:
            temp_data = minio_client.redis_client.get_temp_image(image.upload_id)
            url = temp_data.get("temp_url", "") if temp_data else ""
        
        image_list.append({
            "id": image.id,
            "filename": image.filename,
            "url": url,
            "is_temp": image.is_temp,
            "size": image.size,
            "uploaded_at": image.uploaded_at
        })
    
    # 将SQLAlchemy对象转换为字典
    result = {
        "id": spare_part.id,
        "location_code": spare_part.location_code,
        "mes_material_code": spare_part.mes_material_code,
        "mes_material_desc": spare_part.mes_material_desc,
        "physical_material_desc": spare_part.physical_material_desc,
        "specification_model": spare_part.specification_model,
        "applicable_model": spare_part.applicable_model,
        "brand": spare_part.brand,
        "mes_stock": spare_part.mes_stock,
        "physical_stock": spare_part.physical_stock,
        "unit": spare_part.unit,
        "storage_location": spare_part.storage_location,
        "physical_image_url": spare_part.physical_image_url,
        "physical_image_url2": spare_part.physical_image_url2,
        "remarks": spare_part.remarks,
        "created_at": spare_part.created_at,
        "updated_at": spare_part.updated_at,
        "is_active": spare_part.is_active,
        "images": image_list
    }
    return result

# app/crud/spare_part.py

def sync_spare_part_images(db: Session, spare_part_id: int) -> Optional[Dict[str, Any]]:
    """同步备件的图片数据到spare_parts表的字段"""
    try:
        # 获取备件记录
        spare_part = db.query(SparePart).filter(SparePart.id == spare_part_id).first()
        
        if not spare_part:
            return None
        
        # 获取该备件的所有永久图片，按上传时间排序
        images = db.query(SparePartImage).filter(
            SparePartImage.spare_part_id == spare_part_id,
            SparePartImage.is_temp == False
        ).order_by(SparePartImage.uploaded_at.asc()).all()
        
        # 更新spare_parts表的URL字段
        updated = False
        for idx, image in enumerate(images[:2]):  # 只更新前两张图片
            try:
                image_url = minio_client.get_presigned_url(image.object_name)
                
                if idx == 0:
                    if spare_part.physical_image_url != image_url:
                        spare_part.physical_image_url = image_url
                        updated = True
                        logger.info(f"更新备件 {spare_part_id} 的physical_image_url: {image_url}")
                elif idx == 1:
                    if spare_part.physical_image_url2 != image_url:
                        spare_part.physical_image_url2 = image_url
                        updated = True
                        logger.info(f"更新备件 {spare_part_id} 的physical_image_url2: {image_url}")
            except Exception as e:
                logger.error(f"生成图片URL失败: {e}")
                continue
        
        if updated:
            db.commit()
            db.refresh(spare_part)
        
        # 返回同步后的结果
        return {
            "id": spare_part.id,
            "mes_material_code": spare_part.mes_material_code,
            "physical_image_url": spare_part.physical_image_url,
            "physical_image_url2": spare_part.physical_image_url2,
            "updated": updated,
            "images_count": len(images)
        }
    
    except Exception as e:
        logger.error(f"同步备件图片失败: {e}")
        db.rollback()
        return None


def batch_update_mes_stock_by_mes_code(
    db: Session,
    items: List[Dict[str, Any]],
) -> Tuple[int, int, List[Dict[str, Any]]]:
    """
    按 MES 编码批量更新 MES 库存。
    items: [ {"mes_material_code": str, "mes_stock": number}, ... ]
    返回 (成功数, 跳过数, 错误列表 [{row, message}]).
    """
    updated_count = 0
    skipped_count = 0
    errors: List[Dict[str, Any]] = []
    for idx, item in enumerate(items, start=1):
        mes_code = (item.get("mes_material_code") or "").strip()
        if not mes_code:
            skipped_count += 1
            errors.append({"row": idx, "message": "MES编码为空，已跳过"})
            continue
        try:
            mes_stock_val = item.get("mes_stock")
            if mes_stock_val is None:
                skipped_count += 1
                errors.append({"row": idx, "message": f"MES编码 {mes_code}：未提供MES库存，已跳过"})
                continue
            if isinstance(mes_stock_val, str):
                try:
                    mes_stock_val = float(mes_stock_val)
                except ValueError:
                    errors.append({"row": idx, "message": f"MES编码 {mes_code}：MES库存非数字，已跳过"})
                    skipped_count += 1
                    continue
            mes_stock_int = int(round(float(mes_stock_val)))
            if mes_stock_int < 0:
                mes_stock_int = 0
        except (TypeError, ValueError):
            errors.append({"row": idx, "message": f"MES编码 {mes_code}：MES库存格式错误，已跳过"})
            skipped_count += 1
            continue
        existing = get_spare_part_by_number(db, mes_code)
        if not existing:
            skipped_count += 1
            errors.append({"row": idx, "message": f"MES编码 {mes_code} 未找到对应备件，已跳过"})
            continue
        existing.mes_stock = mes_stock_int
        updated_count += 1
    return updated_count, skipped_count, errors