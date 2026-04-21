# app/crud/mechanical_spare_part.py
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from typing import List, Optional, Dict, Any, Tuple
from datetime import timedelta
import logging

from app.core.datetime_utils import utc_now
from app.core.config import settings
from app.models.mechanical_spare_part import MechanicalSparePart
from app.models.mechanical_spare_part_image import MechanicalSparePartImage
from app.schemas.mechanical_spare_part import MechanicalSparePartCreate, MechanicalSparePartUpdate
from app.utils.minio_client import minio_client

logger = logging.getLogger(__name__)


def get_mechanical_spare_part(db: Session, part_id: int) -> Optional[MechanicalSparePart]:
    return db.query(MechanicalSparePart).filter(MechanicalSparePart.id == part_id).first()


def get_mechanical_spare_part_by_location_and_spec(
    db: Session, location_code: str, specification_model: Optional[str] = None
) -> Optional[MechanicalSparePart]:
    loc = (location_code or "").strip()
    spec = (specification_model or "").strip()
    q = db.query(MechanicalSparePart).filter(MechanicalSparePart.location_code == loc)
    if spec:
        q = q.filter(MechanicalSparePart.specification_model == spec)
    else:
        q = q.filter(or_(MechanicalSparePart.specification_model.is_(None), MechanicalSparePart.specification_model == ""))
    return q.first()


def get_mechanical_spare_part_by_mes(db: Session, mes_material_code: str) -> Optional[MechanicalSparePart]:
    """根据 MES 物料编码获取机械备件（若有多个则返回第一个）"""
    code = (mes_material_code or "").strip()
    if not code:
        return None
    return db.query(MechanicalSparePart).filter(MechanicalSparePart.mes_material_code == code).first()


def _mechanical_base_query(
    db: Session,
    keyword: Optional[str] = None,
    brand: Optional[str] = None,
    applicable_model: Optional[str] = None,
    storage_location: Optional[str] = None,
    location_prefix: Optional[str] = None,
    updated_since: Optional[str] = None,
):
    query = db.query(MechanicalSparePart)
    if keyword:
        search = f"%{keyword}%"
        query = query.filter(or_(
            MechanicalSparePart.location_code.ilike(search),
            MechanicalSparePart.mes_material_code.ilike(search),
            MechanicalSparePart.mes_material_desc.ilike(search),
            MechanicalSparePart.physical_material_desc.ilike(search),
            MechanicalSparePart.specification_model.ilike(search),
            MechanicalSparePart.applicable_model.ilike(search),
            MechanicalSparePart.brand.ilike(search),
            MechanicalSparePart.storage_location.ilike(search),
            MechanicalSparePart.drawing_no.ilike(search),
            MechanicalSparePart.custodian.ilike(search),
            MechanicalSparePart.remarks.ilike(search),
        ))
    if brand and str(brand).strip():
        query = query.filter(MechanicalSparePart.brand.ilike(f"%{brand.strip()}%"))
    if applicable_model and str(applicable_model).strip():
        query = query.filter(MechanicalSparePart.applicable_model.ilike(f"%{applicable_model.strip()}%"))
    if storage_location and str(storage_location).strip():
        query = query.filter(MechanicalSparePart.storage_location.ilike(f"%{storage_location.strip()}%"))
    if location_prefix and str(location_prefix).strip():
        prefix = str(location_prefix).strip().upper()
        query = query.filter(MechanicalSparePart.location_code.ilike(f"{prefix}%"))
    if updated_since and str(updated_since).strip():
        delta_map = {"1d": 1, "7d": 7, "30d": 30, "6m": 180, "1y": 365}
        days = delta_map.get(str(updated_since).strip().lower())
        if days is not None:
            cutoff = utc_now().replace(tzinfo=None) - timedelta(days=days)
            query = query.filter(MechanicalSparePart.updated_at >= cutoff)
    return query


def get_mechanical_spare_parts_with_total(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    keyword: Optional[str] = None,
    brand: Optional[str] = None,
    applicable_model: Optional[str] = None,
    storage_location: Optional[str] = None,
    location_prefix: Optional[str] = None,
    updated_since: Optional[str] = None,
    stock_alert: Optional[str] = None,
) -> Tuple[List[MechanicalSparePart], int, Optional[int], Optional[int]]:
    """列表+总数；stock_alert=zero/low 时筛选；否则返回 zero_count、low_count。总库存=mes_stock+physical_stock。"""
    base = _mechanical_base_query(
        db, keyword=keyword, brand=brand, applicable_model=applicable_model,
        storage_location=storage_location, location_prefix=location_prefix, updated_since=updated_since,
    )
    total_stock_expr = func.coalesce(MechanicalSparePart.mes_stock, 0) + func.coalesce(MechanicalSparePart.physical_stock, 0)
    zero_count, low_count = None, None
    if stock_alert == "zero":
        base = base.filter(total_stock_expr == 0)
    elif stock_alert == "low":
        base = base.filter(total_stock_expr == 1)
    else:
        zero_count = base.filter(total_stock_expr == 0).count()
        low_count = base.filter(total_stock_expr == 1).count()
    total = base.count()
    items = base.order_by(MechanicalSparePart.id).offset(skip).limit(limit).all()
    return items, total, zero_count, low_count


def get_mechanical_spare_part_filter_options(db: Session) -> Dict[str, List[str]]:
    def _distinct(column):
        try:
            q = db.query(column).filter(column.isnot(None), column != "").distinct().order_by(column)
            return sorted({r[0] for r in q.all() if r[0]})
        except Exception as e:
            logger.warning("get_mechanical_spare_part_filter_options %s: %s", getattr(column, "key", column), e)
            return []
    try:
        brands = _distinct(MechanicalSparePart.brand)
        applicable = _distinct(MechanicalSparePart.applicable_model)
        storage = _distinct(MechanicalSparePart.storage_location)
        spec_models = _distinct(MechanicalSparePart.specification_model)
        locs = [r[0] for r in db.query(MechanicalSparePart.location_code).filter(
            MechanicalSparePart.location_code.isnot(None), MechanicalSparePart.location_code != ""
        ).distinct().all() if r[0]]
        prefixes = sorted(set((s[0].upper() if s else "") for s in locs if s))
    except Exception as e:
        logger.warning("get_mechanical_spare_part_filter_options: %s", e)
        return {"brands": [], "applicable_models": [], "storage_locations": [], "specification_models": [], "location_prefixes": []}
    return {"brands": brands, "applicable_models": applicable, "storage_locations": storage, "specification_models": spec_models, "location_prefixes": prefixes}


def get_mechanical_spare_parts_for_requisition(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    keyword: Optional[str] = None,
    brand: Optional[str] = None,
    applicable_model: Optional[str] = None,
    specification_model: Optional[str] = None,
    storage_location: Optional[str] = None,
    location_prefix: Optional[str] = None,
) -> Tuple[List[MechanicalSparePart], int]:
    base = _mechanical_base_query(
        db,
        keyword=keyword,
        brand=brand,
        applicable_model=applicable_model,
        storage_location=storage_location,
        location_prefix=location_prefix,
    )
    if specification_model and str(specification_model).strip():
        base = base.filter(MechanicalSparePart.specification_model.ilike(f"%{specification_model.strip()}%"))
    total = base.count()
    items = base.order_by(MechanicalSparePart.id).offset(skip).limit(limit).all()
    return items, total


def create_mechanical_spare_part_with_images(
    db: Session,
    spare_part: MechanicalSparePartCreate,
    image_upload_ids: List[str] = None,
) -> MechanicalSparePart:
    if image_upload_ids is None:
        image_upload_ids = []
    existing = get_mechanical_spare_part_by_location_and_spec(db, spare_part.location_code, spare_part.specification_model)
    if existing:
        raise ValueError(
            f"货位号 '{spare_part.location_code}' + 规格型号 '{getattr(spare_part, 'specification_model', '') or ''}' 已存在。"
        )
    data = spare_part.model_dump(exclude={"image_upload_ids"}, exclude_unset=True)
    data["mes_material_code"] = (data.get("mes_material_code") or "").strip() or ""
    data["specification_model"] = (data.get("specification_model") or "").strip() or ""
    db_item = MechanicalSparePart(**data)
    db.add(db_item)
    db.commit()
    db.refresh(db_item)

    if image_upload_ids:
        from app.crud.image import delete_image_record, get_image_by_upload_id
        for index, upload_id in enumerate(image_upload_ids):
            try:
                # 与电气备件一致：提交时确认 temp 内图片，移动到最终目录 spare-parts-machine/
                result = minio_client.confirm_temp_image(
                    upload_id,
                    spare_part_id=db_item.id,
                    image_index=index,
                    target_prefix=settings.IMAGE_UPLOAD_PREFIX_MECHANICAL,
                )
                image_url = result["url"]
                if index == 0:
                    db_item.physical_image_url = image_url
                elif index == 1:
                    db_item.physical_image_url2 = image_url
                mec_image = MechanicalSparePartImage(
                    material_code=db_item.mes_material_code or result.get("material_code", ""),
                    object_name=result["object_name"],
                    filename=result["filename"],
                    original_filename=result.get("original_filename"),
                    content_type=result.get("content_type"),
                    size=result.get("size"),
                    is_temp=False,
                    upload_id=upload_id,
                    uploaded_at=utc_now().replace(tzinfo=None),
                    mechanical_spare_part_id=db_item.id,
                )
                db.add(mec_image)
                # 若存在共享的 Image 记录则删除，避免孤儿
                image_record = get_image_by_upload_id(db, upload_id)
                if image_record:
                    delete_image_record(db, image_record.id)
            except Exception as e:
                logger.error("确认机械备件图片失败 %s: %s", upload_id, e)
    db.commit()
    db.refresh(db_item)
    return db_item


def update_mechanical_spare_part_with_images(
    db: Session,
    db_item: MechanicalSparePart,
    update_data: MechanicalSparePartUpdate,
    image_upload_ids: List[str] = None,
    image_ids_to_delete: List[int] = None,
) -> MechanicalSparePart:
    if image_upload_ids is None:
        image_upload_ids = []
    if image_ids_to_delete is None:
        image_ids_to_delete = []
    payload = update_data.model_dump(exclude_unset=True, exclude={"image_upload_ids", "image_ids_to_delete"})
    for k, v in payload.items():
        setattr(db_item, k, v)

    if image_ids_to_delete:
        for image_id in image_ids_to_delete:
            img = db.query(MechanicalSparePartImage).filter(MechanicalSparePartImage.id == image_id).first()
            if img:
                if not img.is_temp and img.object_name:
                    try:
                        minio_client.client.remove_object(minio_client.bucket_name, img.object_name)
                    except Exception as e:
                        logger.error("删除MINIO文件失败 %s: %s", img.object_name, e)
                if img.id and img.object_name:
                    if db_item.physical_image_url and img.object_name in (db_item.physical_image_url or ""):
                        db_item.physical_image_url = None
                    elif db_item.physical_image_url2 and img.object_name in (db_item.physical_image_url2 or ""):
                        db_item.physical_image_url2 = None
                db.delete(img)
        # 确保删除操作在后续查询前已写入会话
        db.flush()

    if image_upload_ids:
        from app.crud.image import get_image_by_upload_id, delete_image_record
        existing = db.query(MechanicalSparePartImage).filter(
            MechanicalSparePartImage.mechanical_spare_part_id == db_item.id,
            MechanicalSparePartImage.is_temp == False,
        ).all()
        start_index = len(existing)
        for i, upload_id in enumerate(image_upload_ids):
            try:
                # 与电气备件一致：提交时确认 temp 内图片，移动到最终目录 spare-parts-machine/
                result = minio_client.confirm_temp_image(
                    upload_id,
                    spare_part_id=db_item.id,
                    image_index=start_index + i,
                    target_prefix=settings.IMAGE_UPLOAD_PREFIX_MECHANICAL,
                )
                image_url = result["url"]
                idx = start_index + i
                if idx == 0:
                    db_item.physical_image_url = image_url
                elif idx == 1:
                    db_item.physical_image_url2 = image_url
                mec_image = MechanicalSparePartImage(
                    material_code=db_item.mes_material_code or result.get("material_code", ""),
                    object_name=result["object_name"],
                    filename=result["filename"],
                    original_filename=result.get("original_filename"),
                    content_type=result.get("content_type"),
                    size=result.get("size"),
                    is_temp=False,
                    upload_id=upload_id,
                    uploaded_at=utc_now().replace(tzinfo=None),
                    mechanical_spare_part_id=db_item.id,
                )
                db.add(mec_image)
                image_record = get_image_by_upload_id(db, upload_id)
                if image_record:
                    delete_image_record(db, image_record.id)
            except Exception as e:
                logger.error("确认机械备件图片失败 %s: %s", upload_id, e)

    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item


def delete_mechanical_spare_part_with_images(db: Session, part_id: int) -> Optional[MechanicalSparePart]:
    db_item = db.query(MechanicalSparePart).filter(MechanicalSparePart.id == part_id).first()
    if not db_item:
        return None
    images = db.query(MechanicalSparePartImage).filter(MechanicalSparePartImage.mechanical_spare_part_id == part_id).all()
    for img in images:
        try:
            if not img.is_temp and img.object_name:
                minio_client.client.remove_object(minio_client.bucket_name, img.object_name)
            db.delete(img)
        except Exception as e:
            logger.error("删除机械备件图片失败 %s: %s", img.id, e)
    db.delete(db_item)
    db.commit()
    return db_item


def get_mechanical_spare_part_with_images(db: Session, part_id: int) -> Optional[Dict[str, Any]]:
    item = get_mechanical_spare_part(db, part_id)
    if not item:
        return None
    images = db.query(MechanicalSparePartImage).filter(MechanicalSparePartImage.mechanical_spare_part_id == part_id).all()
    image_list = []
    for img in images:
        if not img.is_temp:
            url = minio_client.get_presigned_url(img.object_name)
        else:
            temp_data = minio_client.redis_client.get_temp_image(img.upload_id) if getattr(minio_client, "redis_client", None) else None
            url = (temp_data or {}).get("temp_url", "")
        image_list.append({
            "id": img.id,
            "filename": img.filename,
            "url": url,
            "is_temp": img.is_temp,
            "size": img.size,
            "uploaded_at": img.uploaded_at,
        })
    return {
        "id": item.id,
        "location_code": item.location_code,
        "mes_material_code": item.mes_material_code,
        "mes_material_desc": item.mes_material_desc,
        "physical_material_desc": item.physical_material_desc,
        "specification_model": item.specification_model,
        "applicable_model": item.applicable_model,
        "brand": item.brand,
        "mes_stock": item.mes_stock,
        "physical_stock": item.physical_stock,
        "unit": item.unit,
        "storage_location": item.storage_location,
        "physical_image_url": item.physical_image_url,
        "physical_image_url2": item.physical_image_url2,
        "remarks": item.remarks,
        "drawing_no": item.drawing_no,
        "custodian": item.custodian,
        "source_description": item.source_description,
        "technical_appraisal": item.technical_appraisal,
        "disposal_method": item.disposal_method,
        "created_at": item.created_at,
        "updated_at": item.updated_at,
        "is_active": item.is_active,
        "images": image_list,
    }


def sync_mechanical_spare_part_images(db: Session, part_id: int) -> Optional[Dict[str, Any]]:
    item = db.query(MechanicalSparePart).filter(MechanicalSparePart.id == part_id).first()
    if not item:
        return None
    images = db.query(MechanicalSparePartImage).filter(
        MechanicalSparePartImage.mechanical_spare_part_id == part_id,
        MechanicalSparePartImage.is_temp == False,
    ).order_by(MechanicalSparePartImage.uploaded_at.asc()).all()
    updated = False
    for idx, img in enumerate(images[:2]):
        try:
            url = minio_client.get_presigned_url(img.object_name)
            if idx == 0 and item.physical_image_url != url:
                item.physical_image_url = url
                updated = True
            elif idx == 1 and item.physical_image_url2 != url:
                item.physical_image_url2 = url
                updated = True
        except Exception as e:
            logger.error("同步机械备件图片URL失败: %s", e)
    if updated:
        db.commit()
        db.refresh(item)
    return {"id": item.id, "updated": updated, "images_count": len(images)}


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
        existing = get_mechanical_spare_part_by_mes(db, mes_code)
        if not existing:
            skipped_count += 1
            errors.append({"row": idx, "message": f"MES编码 {mes_code} 未找到对应备件，已跳过"})
            continue
        existing.mes_stock = mes_stock_int
        updated_count += 1
    return updated_count, skipped_count, errors
