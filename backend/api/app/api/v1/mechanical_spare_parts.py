# app/api/v1/mechanical_spare_parts.py
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session
from typing import Optional
import logging

from app.core.database import get_db
from app.api.v1.auth import get_current_user, require_material_scope
from app.api.v1.ws import broadcast_mechanical_spare_part_changed
from app.models.user import User
from app.utils.cache import get_cached, set_cached, invalidate_filter_options_cache, FILTER_OPTIONS_TTL

require_mechanical = require_material_scope("mechanical")
from app.crud.mechanical_spare_part import (
    get_mechanical_spare_part,
    get_mechanical_spare_parts_with_total,
    get_mechanical_spare_parts_for_requisition,
    get_mechanical_spare_part_filter_options,
    get_mechanical_spare_part_by_location_and_spec,
    create_mechanical_spare_part_with_images,
    update_mechanical_spare_part_with_images,
    delete_mechanical_spare_part_with_images,
    get_mechanical_spare_part_with_images as get_mechanical_with_images_crud,
    sync_mechanical_spare_part_images,
    batch_update_mes_stock_by_mes_code,
)
from app.schemas.mechanical_spare_part import (
    MechanicalSparePart,
    MechanicalSparePartCreate,
    MechanicalSparePartUpdate,
)
from app.schemas.requisition import RequisitionRequest, RequisitionResponse, ReturnRequest, ReturnResponse
from app.crud.mechanical_requisition import (
    requisition_mechanical_spare_part, get_recent_mechanical_requisition_logs,
    return_mechanical_spare_part, get_unreturned_quantity_mechanical,
)
from app.crud.mechanical_inbound_log import create_mechanical_inbound_log
from app.crud.mechanical_outbound_log import create_mechanical_outbound_log
from app.crud.operation_log import log_operation

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/mechanical-requisition-search", tags=["机械备件领用"])
async def mechanical_requisition_search(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    keyword: Optional[str] = Query(None),
    brand: Optional[str] = Query(None),
    applicable_model: Optional[str] = Query(None),
    specification_model: Optional[str] = Query(None),
    storage_location: Optional[str] = Query(None, description="存放地筛选"),
    location_prefix: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_mechanical),
):
    kw = keyword and str(keyword).strip() or None
    items, total = get_mechanical_spare_parts_for_requisition(
        db,
        skip=skip,
        limit=limit,
        keyword=kw,
        brand=brand,
        applicable_model=applicable_model,
        specification_model=specification_model,
        storage_location=storage_location,
        location_prefix=location_prefix,
    )
    return {"items": items, "total": total}


@router.get("/mechanical-requisition-recent", tags=["机械备件领用"])
async def mechanical_requisition_recent(
    limit: int = Query(10, ge=1, le=20),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_mechanical),
):
    """当前用户的最近领用记录（机械），用于领用页「最近领用」展示。"""
    operator_name = getattr(current_user, "real_name", None) or current_user.username
    items = get_recent_mechanical_requisition_logs(db, operator_name=operator_name or "", limit=limit)
    return {"items": items}


@router.get("/mechanical-spare-parts", tags=["机械备件管理"])
async def read_mechanical_spare_parts(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    keyword: Optional[str] = Query(None),
    brand: Optional[str] = Query(None),
    applicable_model: Optional[str] = Query(None),
    storage_location: Optional[str] = Query(None),
    location_prefix: Optional[str] = Query(None),
    updated_since: Optional[str] = Query(None),
    stock_alert: Optional[str] = Query(None, description="库存提醒筛选：zero=仅零库存，low=仅低库存(总库存=1)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_mechanical),
):
    stock = (stock_alert and str(stock_alert).strip().lower()) or None
    if stock and stock not in ("zero", "low"):
        stock = None
    items, total, zero_count, low_count = get_mechanical_spare_parts_with_total(
        db,
        skip=skip,
        limit=limit,
        keyword=keyword,
        brand=brand,
        applicable_model=applicable_model,
        storage_location=storage_location,
        location_prefix=location_prefix,
        updated_since=updated_since,
        stock_alert=stock,
    )
    out = {"items": items, "total": total}
    if zero_count is not None:
        out["zero_count"] = zero_count
    if low_count is not None:
        out["low_count"] = low_count
    return out


@router.get("/mechanical-spare-parts-filter-options", tags=["机械备件管理"])
async def read_mechanical_filter_options(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_mechanical),
):
    """
    获取机械备件筛选下拉选项。
    结果会被缓存 10 分钟以提高响应速度。
    """
    # 尝试从缓存获取
    cache_key = "mechanical_filter:options"
    cached = get_cached(cache_key)
    if cached is not None:
        return cached
    
    # 缓存未命中，查询数据库
    result = get_mechanical_spare_part_filter_options(db)
    
    # 缓存结果
    set_cached(cache_key, result, FILTER_OPTIONS_TTL)
    
    return result


@router.get("/mechanical-spare-parts/{part_id}", response_model=MechanicalSparePart, tags=["机械备件管理"])
async def read_mechanical_spare_part(
    part_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_mechanical),
):
    item = get_mechanical_spare_part(db, part_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"机械备件ID {part_id} 不存在")
    return item


@router.get("/mechanical-spare-parts/{part_id}/with-images", tags=["机械备件管理"])
async def read_mechanical_spare_part_with_images(
    part_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_mechanical),
):
    result = get_mechanical_with_images_crud(db, part_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"机械备件ID {part_id} 不存在")
    return result


@router.post("/mechanical-spare-parts", response_model=MechanicalSparePart, status_code=status.HTTP_201_CREATED, tags=["机械备件管理"])
async def create_mechanical_spare_part(
    body: MechanicalSparePartCreate,
    allow_overwrite: bool = Query(False, description="模式一批量导入时设为 true：货位号+规格型号已存在则覆盖更新，不报 400"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_mechanical),
):
    existing = get_mechanical_spare_part_by_location_and_spec(db, body.location_code, body.specification_model)
    if existing:
        if allow_overwrite:
            update_data = MechanicalSparePartUpdate(
                location_code=body.location_code,
                mes_material_code=body.mes_material_code,
                mes_material_desc=body.mes_material_desc,
                physical_material_desc=body.physical_material_desc,
                specification_model=body.specification_model,
                applicable_model=body.applicable_model,
                brand=body.brand,
                mes_stock=body.mes_stock if body.mes_stock is not None else 0.0,
                physical_stock=body.physical_stock if body.physical_stock is not None else 0.0,
                unit=body.unit or "个",
                remarks=body.remarks,
                storage_location=body.storage_location,
                physical_image_url=body.physical_image_url,
                physical_image_url2=body.physical_image_url2,
                drawing_no=body.drawing_no,
                custodian=body.custodian,
                source_description=body.source_description,
                technical_appraisal=body.technical_appraisal,
                disposal_method=body.disposal_method,
                image_upload_ids=body.image_upload_ids,
                image_ids_to_delete=[],
            )
            result = update_mechanical_spare_part_with_images(
                db=db,
                db_item=existing,
                update_data=update_data,
                image_upload_ids=body.image_upload_ids or [],
                image_ids_to_delete=[],
            )
            try:
                summary = f"批量模式一覆盖更新机械备件 {existing.id}（货位号 {result.location_code}，规格型号 {getattr(result, 'specification_model', '') or ''}）"
                log_operation(
                    db=db,
                    user=current_user,
                    module="mechanical_spare_part",
                    action="update",
                    entity_type="mechanical_spare_part",
                    entity_id=existing.id,
                    summary=summary,
                )
                db.commit()
            except Exception as e:
                logger.warning("记录覆盖更新机械备件操作日志失败: %s", e)
            invalidate_filter_options_cache()
            await broadcast_mechanical_spare_part_changed()
            return result
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"货位号 '{body.location_code}' + 规格型号 '{getattr(body, 'specification_model', '') or ''}' 已存在",
        )
    if not body.location_code or not body.location_code.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="货位号不能为空")
    if body.mes_stock is None:
        body.mes_stock = 0.0
    if body.physical_stock is None:
        body.physical_stock = 0.0
    if not body.unit or not body.unit.strip():
        body.unit = "个"
    result = create_mechanical_spare_part_with_images(
        db=db,
        spare_part=body,
        image_upload_ids=body.image_upload_ids,
    )
    try:
        summary = f"创建机械备件 {result.id}（货位号 {result.location_code}，规格型号 {getattr(result, 'specification_model', '') or ''}）"
        log_operation(
            db=db,
            user=current_user,
            module="mechanical_spare_part",
            action="create",
            entity_type="mechanical_spare_part",
            entity_id=result.id,
            summary=summary,
        )
        db.commit()
    except Exception as e:
        logger.warning("记录创建机械备件操作日志失败: %s", e)
    # 清除筛选选项缓存
    invalidate_filter_options_cache()
    # 广播数据变更，跨终端同步
    await broadcast_mechanical_spare_part_changed()
    return result


@router.put("/mechanical-spare-parts/{part_id}", response_model=MechanicalSparePart, tags=["机械备件管理"])
async def update_mechanical_spare_part(
    part_id: int,
    body: MechanicalSparePartUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_mechanical),
):
    db_item = get_mechanical_spare_part(db, part_id)
    if db_item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"机械备件ID {part_id} 不存在")
    new_loc = body.location_code if body.location_code is not None else db_item.location_code
    new_spec = body.specification_model if body.specification_model is not None else db_item.specification_model
    existing = get_mechanical_spare_part_by_location_and_spec(db, new_loc, new_spec)
    if existing and existing.id != part_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"货位号 '{new_loc}' + 规格型号 '{new_spec or ''}' 已被其他机械备件使用",
        )
    before_physical = int(getattr(db_item, "physical_stock", 0) or 0)
    result = update_mechanical_spare_part_with_images(
        db=db,
        db_item=db_item,
        update_data=body,
        image_upload_ids=body.image_upload_ids,
        image_ids_to_delete=body.image_ids_to_delete or [],
    )
    after_physical = int(getattr(result, "physical_stock", 0) or 0)
    if after_physical > before_physical:
        try:
            create_mechanical_inbound_log(
                db=db,
                mechanical_spare_part_id=part_id,
                quantity=after_physical - before_physical,
                physical_stock_before=before_physical,
                physical_stock_after=after_physical,
                operator_name=getattr(current_user, "username", None),
            )
        except Exception as e:
            logger.warning("记录机械备件入库日志失败: %s", e)
    elif after_physical < before_physical:
        try:
            create_mechanical_outbound_log(
                db=db,
                mechanical_spare_part_id=part_id,
                quantity=before_physical - after_physical,
                physical_stock_before=before_physical,
                physical_stock_after=after_physical,
                operator_name=getattr(current_user, "username", None),
            )
        except Exception as e:
            logger.warning("记录机械备件出库日志失败: %s", e)
    try:
        summary = f"更新机械备件 {part_id}"
        log_operation(
            db=db,
            user=current_user,
            module="mechanical_spare_part",
            action="update",
            entity_type="mechanical_spare_part",
            entity_id=part_id,
            summary=summary,
        )
        db.commit()
    except Exception as e:
        logger.warning("记录更新机械备件操作日志失败: %s", e)
    # 清除筛选选项缓存
    invalidate_filter_options_cache()
    # 广播数据变更，跨终端同步
    await broadcast_mechanical_spare_part_changed()
    return result


@router.delete("/mechanical-spare-parts/{part_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["机械备件管理"])
async def delete_mechanical_spare_part(
    part_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_mechanical),
):
    item = delete_mechanical_spare_part_with_images(db, part_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"机械备件ID {part_id} 不存在")
    try:
        summary = f"删除机械备件 {part_id}（货位号 {item.location_code}）"
        log_operation(
            db=db,
            user=current_user,
            module="mechanical_spare_part",
            action="delete",
            entity_type="mechanical_spare_part",
            entity_id=part_id,
            summary=summary,
        )
        db.commit()
    except Exception as e:
        logger.warning("记录删除机械备件操作日志失败: %s", e)
    # 清除筛选选项缓存
    invalidate_filter_options_cache()
    # 广播数据变更，跨终端同步
    await broadcast_mechanical_spare_part_changed()


@router.post("/mechanical-spare-parts/{part_id}/requisition", response_model=RequisitionResponse, tags=["机械备件领用"])
async def requisition_mechanical_spare_part_endpoint(
    request: Request,
    part_id: int,
    body: RequisitionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_mechanical),
):
    request_id = (request.headers.get("X-Request-Id") or "").strip()
    try:
        item = get_mechanical_spare_part(db, part_id)
        if not item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"机械备件ID {part_id} 不存在")
        stock = item.physical_stock or 0
        if body.quantity <= 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="领用数量必须大于 0")
        if stock < body.quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"实物库存不足：当前 {stock} {item.unit or '个'}，无法领用 {body.quantity}",
            )
        requisitioner_name = (getattr(current_user, "real_name", None) or getattr(current_user, "username", None)) or "—"
        operator_name = getattr(current_user, "username", None)
        result = requisition_mechanical_spare_part(
            db,
            part_id,
            body.quantity,
            requisitioner_name=requisitioner_name,
            remark=body.remark,
            operator_name=operator_name,
            requisition_reason=body.requisition_reason,
            usage_location=body.usage_location,
        )
        if not result:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="领用处理失败")
        await broadcast_mechanical_spare_part_changed()
        return RequisitionResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("机械领用接口异常 request_id=%s part_id=%s: %s", request_id or "-", part_id, e)
        detail = getattr(e, "message", str(e)) if str(e) else "领用处理异常，请稍后重试或联系管理员"
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail,
        )


@router.post("/mechanical-spare-parts/{part_id}/return", response_model=ReturnResponse, tags=["备件领用"])
async def return_mechanical_spare_part_endpoint(
    part_id: int,
    body: ReturnRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_mechanical),
):
    """
    归还机械备件：增加库存并记录归还日志。
    归还数量不能超过当前用户对该备件的未归还余量（已领用 - 已归还）。
    """
    part = get_mechanical_spare_part(db, part_id)
    if not part:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"备件ID {part_id} 不存在")
    if body.quantity <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="归还数量必须大于 0")
    requisitioner_name = getattr(current_user, "real_name", None) or current_user.username
    unreturned = get_unreturned_quantity_mechanical(db, part_id, current_user.username)
    if body.quantity > unreturned:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"归还数量超出可归还余量：当前可归还 {unreturned} {part.unit or '个'}",
        )
    result = return_mechanical_spare_part(
        db,
        part_id,
        body.quantity,
        requisitioner_name=requisitioner_name,
        remark=body.remark,
        operator_name=current_user.username,
    )
    if not result:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="归还处理失败")
    await broadcast_mechanical_spare_part_changed()
    return ReturnResponse(**result)


@router.post("/mechanical-spare-parts/batch", tags=["机械备件管理"])
async def batch_create_mechanical_spare_parts(
    body: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_mechanical),
):
    from app.schemas.mechanical_spare_part import MechanicalSparePartCreate

    items = body.get("items", [])
    if not items or not isinstance(items, list):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="请提供有效的备件数据数组")
    success_count = failed_count = skipped_count = 0
    errors = []
    for idx, item_data in enumerate(items, start=1):
        try:
            data = MechanicalSparePartCreate(**item_data)
            existing = get_mechanical_spare_part_by_location_and_spec(db, data.location_code, data.specification_model)
            if existing:
                skipped_count += 1
                errors.append({"row": idx, "message": f"货位号+规格型号已存在，已跳过"})
                continue
            create_mechanical_spare_part_with_images(db=db, spare_part=data, image_upload_ids=data.image_upload_ids or [])
            success_count += 1
        except Exception as e:
            failed_count += 1
            errors.append({"row": idx, "message": str(e)})
    if success_count > 0:
        try:
            log_operation(db=db, user=current_user, module="mechanical_spare_part", action="batch_create", entity_type="mechanical_spare_part", entity_id=None, summary=f"批量新增机械备件：成功 {success_count}，失败 {failed_count}，跳过 {skipped_count}")
            db.commit()
        except Exception as e:
            logger.warning("记录批量新增机械备件操作日志失败: %s", e)
        # 广播数据变更，跨终端同步
        await broadcast_mechanical_spare_part_changed()
    return {
        "success": failed_count == 0 and skipped_count == 0,
        "message": f"批量导入完成：成功 {success_count}，失败 {failed_count}，跳过 {skipped_count}",
        "totalCount": len(items),
        "successCount": success_count,
        "failedCount": failed_count,
        "skippedCount": skipped_count,
        "errors": errors[:50],
    }


@router.post("/mechanical-spare-parts/batch-delete", tags=["机械备件管理"])
async def batch_delete_mechanical_spare_parts(
    body: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_mechanical),
):
    ids = body.get("ids")
    if not ids or not isinstance(ids, list):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="请提供有效的备件 ID 数组")
    ids = [int(x) for x in ids if isinstance(x, (int, float)) and int(x) > 0]
    if not ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="请提供有效的备件 ID")
    deleted = failed = 0
    errors = []
    for part_id in ids:
        try:
            obj = delete_mechanical_spare_part_with_images(db, part_id)
            if obj is not None:
                deleted += 1
            else:
                failed += 1
                errors.append({"id": part_id, "message": "备件不存在"})
        except Exception as e:
            failed += 1
            errors.append({"id": part_id, "message": str(e)})
    if deleted > 0:
        try:
            log_operation(db=db, user=current_user, module="mechanical_spare_part", action="batch_delete", entity_type="mechanical_spare_part", entity_id=None, summary=f"批量删除机械备件：成功 {deleted}，失败 {failed}")
            db.commit()
        except Exception as e:
            logger.warning("记录批量删除机械备件操作日志失败: %s", e)
        # 广播数据变更，跨终端同步
        await broadcast_mechanical_spare_part_changed()
    return {"success": failed == 0, "message": f"批量删除完成：成功 {deleted}，失败 {failed}", "deleted": deleted, "failed": failed, "errors": errors[:50]}


@router.post("/mechanical-spare-parts/batch-update-mes", tags=["机械备件管理"])
async def batch_update_mes_stock_mechanical_spare_parts(
    body: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_mechanical),
):
    """
    按 MES 编码批量更新 MES 库存。
    请求体: { "items": [ { "mes_material_code": "编码", "mes_stock": 数量 }, ... ] }。
    返回: { "updated": int, "skipped": int, "errors": [ { "row", "message" } ] }。
    """
    items = body.get("items", [])
    if not items or not isinstance(items, list):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请提供有效的 items 数组（每项含 mes_material_code、mes_stock）",
        )
    updated_count, skipped_count, errors = batch_update_mes_stock_by_mes_code(db, items)
    if updated_count > 0:
        try:
            summary = f"批量更新MES库存（机械备件）：成功 {updated_count} 条，跳过 {skipped_count} 条"
            log_operation(
                db=db,
                user=current_user,
                module="mechanical_spare_part",
                action="batch_update_mes",
                entity_type="mechanical_spare_part",
                entity_id=None,
                summary=summary,
            )
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error("批量更新MES库存（机械）提交失败: %s", e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="保存失败",
            )
        try:
            await broadcast_mechanical_spare_part_changed()
        except Exception as e:
            logger.warning("广播机械备件变更失败: %s", e)
        invalidate_filter_options_cache()
    return {
        "updated": updated_count,
        "skipped": skipped_count,
        "errors": errors[:100],
    }


@router.post("/mechanical-spare-parts/{part_id}/sync-images", tags=["机械备件管理"])
async def sync_mechanical_images(
    part_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_mechanical),
):
    result = sync_mechanical_spare_part_images(db, part_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"机械备件ID {part_id} 不存在")
    return {"success": True, "message": f"机械备件 {part_id} 图片同步{'成功' if result.get('updated') else '无需更新'}", "data": result}
