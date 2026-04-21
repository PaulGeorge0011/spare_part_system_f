# app/api/v1/spare_parts.py
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session
from typing import List, Optional
import logging

from app.core.database import get_db
from app.api.v1.ws import broadcast_spare_part_changed
from app.api.v1.auth import get_current_user, require_material_scope
from app.models.user import User
from app.utils.cache import get_cached, set_cached, invalidate_filter_options_cache, FILTER_OPTIONS_TTL

require_electrical = require_material_scope("electrical")
from app.crud.spare_part import (
    get_spare_part,
    get_spare_parts,
    get_spare_parts_with_total,
    get_spare_parts_for_requisition,
    get_spare_part_filter_options,
    create_spare_part_with_images,
    update_spare_part_with_images,
    delete_spare_part_with_images,
    get_spare_part_by_mes_and_location,
    get_spare_part_by_location_and_spec,
    get_spare_part_with_images as get_spare_part_with_images_crud,
    sync_spare_part_images,
    batch_update_mes_stock_by_mes_code,
)
from app.schemas.spare_part import SparePart, SparePartCreate, SparePartUpdate
from app.schemas.requisition import RequisitionRequest, RequisitionResponse, ReturnRequest, ReturnResponse
from app.crud.requisition import requisition_spare_part, get_recent_requisition_logs, return_spare_part, get_unreturned_quantity
from app.crud.operation_log import log_operation
from app.crud.inbound_log import create_inbound_log
from app.crud.outbound_log import create_outbound_log

logger = logging.getLogger(__name__)

router = APIRouter()

# 其他路由保持不变...

@router.get("/requisition-search", tags=["备件领用"])
async def requisition_search(
    skip: int = Query(0, ge=0, description="跳过记录数"),
    limit: int = Query(100, ge=1, le=1000, description="每页记录数"),
    keyword: Optional[str] = Query(None, description="关键词：搜规格型号、MES编码、物料描述、适用机型、品牌"),
    brand: Optional[str] = Query(None, description="品牌筛选"),
    applicable_model: Optional[str] = Query(None, description="适用机型筛选"),
    specification_model: Optional[str] = Query(None, description="规格型号筛选"),
    storage_location: Optional[str] = Query(None, description="存放地筛选"),
    location_prefix: Optional[str] = Query(None, description="货位号首字符，如 A、B、C、D"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_electrical),
):
    """
    备件领用查询：关键词搜规格型号、MES编码、物料描述、适用机型、品牌；
    过滤器：规格型号、适用机型、品牌、存放地、货位号前缀。
    - 管理员(admin)：无任何条件时返回全部。
    空查询（无关键词、无筛选）时返回全部备件，与领用员/管理员一致。
    返回 { "items": [...], "total": number }。
    """
    try:
        kw = keyword and str(keyword).strip() or None
        items, total = get_spare_parts_for_requisition(
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
    except Exception as e:
        logger.error(f"领用查询失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="领用查询失败",
        )


@router.get("/requisition-recent", tags=["备件领用"])
async def requisition_recent(
    limit: int = Query(10, ge=1, le=20, description="条数"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_electrical),
):
    """当前用户的最近领用记录（电气），用于领用页「最近领用」展示。"""
    operator_name = getattr(current_user, "real_name", None) or current_user.username
    items = get_recent_requisition_logs(db, operator_name=operator_name or "", limit=limit)
    return {"items": items}


@router.get("/spare-parts", tags=["备件管理"])
async def read_spare_parts(
    skip: int = Query(0, ge=0, description="跳过记录数"),
    limit: int = Query(100, ge=1, le=1000, description="每页记录数"),
    keyword: Optional[str] = Query(None, description="搜索关键词（货位号、MES编码、物料描述）"),
    brand: Optional[str] = Query(None, description="品牌筛选"),
    applicable_model: Optional[str] = Query(None, description="适用机型筛选"),
    storage_location: Optional[str] = Query(None, description="存放地筛选"),
    location_prefix: Optional[str] = Query(None, description="货位号首字符，如 A、B、C"),
    updated_since: Optional[str] = Query(None, description="更新时间段：1d/7d/30d/6m/1y"),
    stock_alert: Optional[str] = Query(None, description="库存提醒筛选：zero=仅零库存，low=仅低库存(总库存=1)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_electrical),
):
    """
    获取备件列表（分页），支持关键词及品牌/适用机型/存放地/货位号前缀/更新时间段筛选；stock_alert 可筛零库存/低库存。
    返回 `{ "items": [...], "total": number, "zero_count"?: number, "low_count"?: number }`。
    """
    try:
        stock = (stock_alert and str(stock_alert).strip().lower()) or None
        if stock and stock not in ("zero", "low"):
            stock = None
        items, total, zero_count, low_count = get_spare_parts_with_total(
            db, skip=skip, limit=limit, keyword=keyword,
            brand=brand, applicable_model=applicable_model,
            storage_location=storage_location, location_prefix=location_prefix,
            updated_since=updated_since, stock_alert=stock,
        )
        logger.info(f"成功获取 {len(items)} 条备件记录，共 {total} 条")
        out = {"items": items, "total": total}
        if zero_count is not None:
            out["zero_count"] = zero_count
        if low_count is not None:
            out["low_count"] = low_count
        return out
    except Exception as e:
        logger.error(f"获取备件列表失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取备件列表失败: {str(e)}"
        )


@router.get("/spare-parts-filter-options", tags=["备件管理"])
async def read_spare_part_filter_options(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_electrical),
):
    """
    获取备件筛选下拉选项：品牌、适用机型、存放地、货位号首字符（去重排序）。
    用于前端过滤器下拉框。
    结果会被缓存 10 分钟以提高响应速度。
    """
    try:
        # 尝试从缓存获取
        cache_key = "electrical_filter:options"
        cached = get_cached(cache_key)
        if cached is not None:
            return cached
        
        # 缓存未命中，查询数据库
        result = get_spare_part_filter_options(db)
        
        # 缓存结果
        set_cached(cache_key, result, FILTER_OPTIONS_TTL)
        
        return result
    except Exception as e:
        logger.error(f"获取筛选选项失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取筛选选项失败",
        )

@router.get("/spare-parts/{part_id}", response_model=SparePart, tags=["备件管理"])
async def read_spare_part(
    part_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_electrical),
):
    """
    根据ID获取单个备件详情
    """
    spare_part = get_spare_part(db, spare_part_id=part_id)
    if spare_part is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"备件ID {part_id} 不存在"
        )
    return spare_part

@router.get("/spare-parts/{part_id}/with-images", tags=["备件管理"])
async def read_spare_part_with_images(
    part_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_electrical),
):
    """
    获取备件及其所有图片
    """
    result = get_spare_part_with_images_crud(db, part_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"备件ID {part_id} 不存在"
        )
    return result

@router.post("/spare-parts", response_model=SparePart, status_code=status.HTTP_201_CREATED, tags=["备件管理"])
async def create_new_spare_part(
    spare_part: SparePartCreate,
    allow_overwrite: bool = Query(False, description="模式一批量导入时设为 true：货位号+规格型号已存在则覆盖更新，不报 400"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_electrical),
):
    """
    创建新的备件记录。
    唯一性：货位号 + 规格型号 联合区分，两者都相同时视为重复；MES 编码可空。
    """
    logger.info(f"接收到创建备件请求: {spare_part.model_dump()}")
    
    try:
        # 检查 (货位号, 规格型号) 是否已存在
        db_spare_part = get_spare_part_by_location_and_spec(
            db, spare_part.location_code, spare_part.specification_model
        )
        if db_spare_part:
            if allow_overwrite:
                update_data = SparePartUpdate(
                    location_code=spare_part.location_code,
                    mes_material_code=spare_part.mes_material_code,
                    mes_material_desc=spare_part.mes_material_desc,
                    physical_material_desc=spare_part.physical_material_desc,
                    specification_model=spare_part.specification_model,
                    applicable_model=spare_part.applicable_model,
                    brand=spare_part.brand,
                    mes_stock=spare_part.mes_stock if spare_part.mes_stock is not None else 0.0,
                    physical_stock=spare_part.physical_stock if spare_part.physical_stock is not None else 0.0,
                    unit=spare_part.unit or "个",
                    remarks=spare_part.remarks,
                    storage_location=spare_part.storage_location,
                    physical_image_url=spare_part.physical_image_url,
                    physical_image_url2=spare_part.physical_image_url2,
                    image_upload_ids=spare_part.image_upload_ids,
                    image_ids_to_delete=[],
                )
                result = update_spare_part_with_images(
                    db=db,
                    db_item=db_spare_part,
                    spare_part_update=update_data,
                    image_upload_ids=spare_part.image_upload_ids or [],
                    image_ids_to_delete=[],
                )
                logger.info(f"批量模式一覆盖更新备件成功，ID: {result.id}")
                try:
                    summary = f"批量模式一覆盖更新备件 {result.id}（货位号 {result.location_code}，规格型号 {getattr(result, 'specification_model', '') or ''}）"
                    log_operation(
                        db=db,
                        user=current_user,
                        module="spare_part",
                        action="update",
                        entity_type="spare_part",
                        entity_id=result.id,
                        summary=summary,
                    )
                    db.commit()
                except Exception as e:
                    logger.warning("记录覆盖更新备件操作日志失败: %s", e)
                invalidate_filter_options_cache()
                await broadcast_spare_part_changed()
                return result
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"货位号 '{spare_part.location_code}' + 规格型号 '{getattr(spare_part, 'specification_model', '') or ''}' 已存在"
            )
        
        # 货位号必填
        if not spare_part.location_code or len(spare_part.location_code.strip()) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="货位号不能为空"
            )
        
        # 处理可选字段默认值
        if spare_part.mes_stock is None:
            spare_part.mes_stock = 0.0
        
        if spare_part.physical_stock is None:
            spare_part.physical_stock = 0.0
        
        if not spare_part.unit or len(spare_part.unit.strip()) == 0:
            spare_part.unit = "个"
        
        # 创建备件（如携带 image_upload_ids，则同时尝试关联图片）
        result = create_spare_part_with_images(
            db=db,
            spare_part=spare_part,
            image_upload_ids=spare_part.image_upload_ids
        )
        logger.info(f"创建备件成功，ID: {result.id}")
        # 记录操作日志
        try:
            summary = f"创建备件 {result.id}（货位号 {result.location_code}，MES编码 {getattr(result, 'mes_material_code', '') or ''}，规格型号 {getattr(result, 'specification_model', '') or ''}）"
            log_operation(
                db=db,
                user=current_user,
                module="spare_part",
                action="create",
                entity_type="spare_part",
                entity_id=result.id,
                summary=summary,
            )
            db.commit()
        except Exception as e:
            logger.warning("记录创建备件操作日志失败: %s", e)
        # 清除筛选选项缓存
        invalidate_filter_options_cache()
        try:
            await broadcast_spare_part_changed()
        except Exception as e:
            logger.warning("广播备件变更失败: %s", e)
        return result
        
    except ValueError as e:
        logger.error(f"创建备件参数错误: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"创建备件失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建备件失败: {str(e)}"
        )

@router.put("/spare-parts/{part_id}", response_model=SparePart, tags=["备件管理"])
async def update_existing_spare_part(
    part_id: int,
    spare_part_update: SparePartUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_electrical),
):
    """
    更新备件信息
    
    **注意**: (MES物料编码, 货位号) 联合唯一。更新后不得与其他记录的 (MES, 货位) 重复。
    """
    # 1. 检查备件是否存在
    db_spare_part = get_spare_part(db, spare_part_id=part_id)
    if db_spare_part is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"备件ID {part_id} 不存在"
        )
    
    # 2. 若更新了货位号或规格型号，检查 (货位号, 规格型号) 是否与其他记录冲突
    new_loc = spare_part_update.location_code if spare_part_update.location_code is not None else db_spare_part.location_code
    new_spec = spare_part_update.specification_model if spare_part_update.specification_model is not None else db_spare_part.specification_model
    existing = get_spare_part_by_location_and_spec(db, new_loc, new_spec)
    if existing and existing.id != part_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"货位号 '{new_loc}' + 规格型号 '{new_spec or ''}' 已被其他备件使用"
        )
    
    # 3. 保存变更前数据（用于操作日志摘要）
    before_loc = db_spare_part.location_code
    before_mes = getattr(db_spare_part, "mes_material_code", "") or ""
    before_spec = getattr(db_spare_part, "specification_model", "") or ""
    before_unit = getattr(db_spare_part, "unit", "") or "个"
    before_mes_stock = getattr(db_spare_part, "mes_stock", 0)
    before_physical_stock = getattr(db_spare_part, "physical_stock", 0)
    # 4. 执行更新
    try:
        result = update_spare_part_with_images(
            db=db,
            db_item=db_spare_part,
            spare_part_update=spare_part_update,
            image_upload_ids=spare_part_update.image_upload_ids,
            image_ids_to_delete=spare_part_update.image_ids_to_delete
        )
        # 实物库存变动记为入库/管理出库，供库存管理展示
        after_physical_stock = int(getattr(result, "physical_stock", 0) or 0)
        before_val = int(before_physical_stock or 0)
        if after_physical_stock > before_val:
            try:
                create_inbound_log(
                    db=db,
                    spare_part_id=part_id,
                    quantity=after_physical_stock - before_val,
                    physical_stock_before=before_val,
                    physical_stock_after=after_physical_stock,
                    operator_name=getattr(current_user, "username", None),
                )
            except Exception as e:
                logger.warning("记录入库日志失败: %s", e)
        elif after_physical_stock < before_val:
            try:
                create_outbound_log(
                    db=db,
                    spare_part_id=part_id,
                    quantity=before_val - after_physical_stock,
                    physical_stock_before=before_val,
                    physical_stock_after=after_physical_stock,
                    operator_name=getattr(current_user, "username", None),
                )
            except Exception as e:
                logger.warning("记录管理出库日志失败: %s", e)
        # 记录操作日志（含变更前、变更后）
        try:
            summary = (
                f"更新备件 {part_id}（变更前：货位号 {before_loc}，MES编码 {before_mes}，规格型号 {before_spec}，"
                f"单位 {before_unit}，MES库存 {before_mes_stock}，实物库存 {before_physical_stock}；"
                f"变更后：货位号 {result.location_code}，MES编码 {getattr(result, 'mes_material_code', '') or ''}，"
                f"规格型号 {getattr(result, 'specification_model', '') or ''}，单位 {getattr(result, 'unit', '') or '个'}，"
                f"MES库存 {getattr(result, 'mes_stock', 0)}，实物库存 {getattr(result, 'physical_stock', 0)}）"
            )
            log_operation(
                db=db,
                user=current_user,
                module="spare_part",
                action="update",
                entity_type="spare_part",
                entity_id=part_id,
                summary=summary,
            )
            db.commit()
        except Exception as e:
            logger.warning("记录更新备件操作日志失败: %s", e)
        # 清除筛选选项缓存
        invalidate_filter_options_cache()
        try:
            await broadcast_spare_part_changed()
        except Exception as e:
            logger.warning("广播备件变更失败: %s", e)
        return result
    except Exception as e:
        logger.error(f"更新备件失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新备件失败: {str(e)}"
        )

@router.delete("/spare-parts/{part_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["备件管理"])
async def delete_existing_spare_part(
    part_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_electrical),
):
    """
    删除备件记录（同时删除关联的图片）
    """
    spare_part = delete_spare_part_with_images(db, spare_part_id=part_id)
    if spare_part is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"备件ID {part_id} 不存在"
        )
    # 记录操作日志
    try:
        summary = f"删除备件 {part_id}（货位号 {spare_part.location_code}，MES编码 {getattr(spare_part, 'mes_material_code', '') or ''}，规格型号 {getattr(spare_part, 'specification_model', '') or ''}）"
        log_operation(
            db=db,
            user=current_user,
            module="spare_part",
            action="delete",
            entity_type="spare_part",
            entity_id=part_id,
            summary=summary,
        )
        db.commit()
    except Exception as e:
        logger.warning("记录删除备件操作日志失败: %s", e)
    # 清除筛选选项缓存
    invalidate_filter_options_cache()
    try:
        await broadcast_spare_part_changed()
    except Exception as e:
        logger.warning("广播备件变更失败: %s", e)
    # 204 No Content 不返回任何内容

@router.post("/spare-parts/{part_id}/requisition", response_model=RequisitionResponse, tags=["备件领用"])
async def requisition_spare_part_endpoint(
    request: Request,
    part_id: int,
    body: RequisitionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_electrical),
):
    """
    备件领用：扣减修复件库存并记录领用日志。
    仅支持领用，不能新增、删除备件。
    """
    request_id = (request.headers.get("X-Request-Id") or "").strip()
    try:
        spare = get_spare_part(db, spare_part_id=part_id)
        if not spare:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"备件ID {part_id} 不存在")
        stock = spare.physical_stock or 0
        if body.quantity <= 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="领用数量必须大于 0")
        if stock < body.quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"修复件库存不足：当前 {stock} {spare.unit or '个'}，无法领用 {body.quantity}",
            )
        # 领用人 = 当前用户的真实姓名，无则回退到用户名（防御：避免 None 导致后端异常）
        requisitioner_name = (getattr(current_user, "real_name", None) or getattr(current_user, "username", None)) or "—"
        operator_name = getattr(current_user, "username", None)
        result = requisition_spare_part(
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
        try:
            await broadcast_spare_part_changed()
        except Exception as e:
            logger.warning("广播备件变更失败: %s", e)
        return RequisitionResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("领用接口异常 request_id=%s part_id=%s: %s", request_id or "-", part_id, e)
        detail = getattr(e, "message", str(e)) if str(e) else "领用处理异常，请稍后重试或联系管理员"
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail,
        )


@router.post("/spare-parts/{part_id}/return", response_model=ReturnResponse, tags=["备件领用"])
async def return_spare_part_endpoint(
    part_id: int,
    body: ReturnRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_electrical),
):
    """
    归还备件：增加修复件库存并记录归还日志。
    归还数量不能超过当前用户对该备件的未归还余量（已领用 - 已归还）。
    """
    spare = get_spare_part(db, spare_part_id=part_id)
    if not spare:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"备件ID {part_id} 不存在")
    if body.quantity <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="归还数量必须大于 0")
    requisitioner_name = getattr(current_user, "real_name", None) or current_user.username
    unreturned = get_unreturned_quantity(db, part_id, current_user.username)
    if body.quantity > unreturned:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"归还数量超出可归还余量：当前可归还 {unreturned} {spare.unit or '个'}",
        )
    result = return_spare_part(
        db,
        part_id,
        body.quantity,
        requisitioner_name=requisitioner_name,
        remark=body.remark,
        operator_name=current_user.username,
    )
    if not result:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="归还处理失败")
    try:
        await broadcast_spare_part_changed()
    except Exception as e:
        logger.warning("广播备件变更失败: %s", e)
    return ReturnResponse(**result)


@router.post("/spare-parts/batch", tags=["备件管理"])
async def batch_create_spare_parts(
    body: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_electrical),
):
    """
    批量创建备件。唯一性：货位号 + 规格型号 联合区分，两者都相同则跳过；MES 编码可空。
    """
    from app.schemas.spare_part import SparePartCreate

    items = body.get("items", [])
    if not items or not isinstance(items, list):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请提供有效的备件数据数组"
        )
    
    success_count = 0
    failed_count = 0
    skipped_count = 0
    errors = []
    
    for idx, item_data in enumerate(items, start=1):
        try:
            # 验证数据
            spare_part_data = SparePartCreate(**item_data)
            
            # 检查 (货位号, 规格型号) 是否已存在
            existing = get_spare_part_by_location_and_spec(
                db, spare_part_data.location_code, spare_part_data.specification_model
            )
            if existing:
                skipped_count += 1
                errors.append({
                    "row": idx,
                    "message": f"货位号 '{spare_part_data.location_code}' + 规格型号 '{getattr(spare_part_data, 'specification_model', '') or ''}' 已存在，已跳过"
                })
                continue
            
            # 创建备件
            result = create_spare_part_with_images(
                db=db,
                spare_part=spare_part_data,
                image_upload_ids=spare_part_data.image_upload_ids or []
            )
            success_count += 1
            logger.info(f"批量创建备件成功: {result.id} ({spare_part_data.mes_material_code})")
            
        except ValueError as e:
            failed_count += 1
            errors.append({
                "row": idx,
                "message": f"数据验证失败: {str(e)}"
            })
            logger.warning(f"批量创建备件失败（行 {idx}）: {e}")
        except Exception as e:
            failed_count += 1
            errors.append({
                "row": idx,
                "message": f"创建失败: {str(e)}"
            })
            logger.error(f"批量创建备件失败（行 {idx}）: {e}", exc_info=True)
    
    # 如果有成功创建的，记录操作日志并触发广播
    if success_count > 0:
        try:
            summary = f"批量新增备件：成功 {success_count} 条，失败 {failed_count} 条，跳过 {skipped_count} 条"
            log_operation(
                db=db,
                user=current_user,
                module="spare_part",
                action="batch_create",
                entity_type="spare_part",
                entity_id=None,
                summary=summary,
            )
            db.commit()
        except Exception as e:
            logger.warning("记录批量新增备件操作日志失败: %s", e)
        try:
            await broadcast_spare_part_changed()
        except Exception as e:
            logger.warning("广播备件变更失败: %s", e)
    total_count = len(items)
    all_success = failed_count == 0 and skipped_count == 0
    
    return {
        "success": all_success,
        "message": f"批量导入完成：成功 {success_count} 条，失败 {failed_count} 条，跳过 {skipped_count} 条",
        "totalCount": total_count,
        "successCount": success_count,
        "failedCount": failed_count,
        "skippedCount": skipped_count,
        "errors": errors[:50]  # 最多返回50条错误
    }


@router.post("/spare-parts/batch-delete", tags=["备件管理"])
async def batch_delete_spare_parts(
    body: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_electrical),
):
    """
    批量删除备件（同时删除关联图片）。
    请求体: { "ids": [1, 2, 3] }。
    返回: { "success": bool, "message": str, "deleted": int, "failed": int, "errors": [...] }。
    """
    ids = body.get("ids")
    if not ids or not isinstance(ids, list):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请提供有效的备件 ID 数组（ids）",
        )
    ids = [int(x) for x in ids if isinstance(x, (int, float)) and int(x) > 0]
    if not ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请提供有效的备件 ID",
        )
    deleted = 0
    failed = 0
    errors = []
    for part_id in ids:
        try:
            obj = delete_spare_part_with_images(db, spare_part_id=part_id)
            if obj is not None:
                deleted += 1
            else:
                failed += 1
                errors.append({"id": part_id, "message": "备件不存在"})
        except Exception as e:
            failed += 1
            errors.append({"id": part_id, "message": str(e)})
            logger.warning("批量删除备件失败 id=%s: %s", part_id, e)
    if deleted > 0:
        try:
            summary = f"批量删除备件：成功 {deleted} 条，失败 {failed} 条"
            log_operation(
                db=db,
                user=current_user,
                module="spare_part",
                action="batch_delete",
                entity_type="spare_part",
                entity_id=None,
                summary=summary,
            )
            db.commit()
        except Exception as e:
            logger.warning("记录批量删除备件操作日志失败: %s", e)
        try:
            await broadcast_spare_part_changed()
        except Exception as e:
            logger.warning("广播备件变更失败: %s", e)
    return {
        "success": failed == 0,
        "message": f"批量删除完成：成功 {deleted} 条，失败 {failed} 条",
        "deleted": deleted,
        "failed": failed,
        "errors": errors[:50],
    }


@router.post("/spare-parts/batch-update-mes", tags=["备件管理"])
async def batch_update_mes_stock_spare_parts(
    body: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_electrical),
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
            summary = f"批量更新MES库存（电气备件）：成功 {updated_count} 条，跳过 {skipped_count} 条"
            log_operation(
                db=db,
                user=current_user,
                module="spare_part",
                action="batch_update_mes",
                entity_type="spare_part",
                entity_id=None,
                summary=summary,
            )
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error("批量更新MES库存提交失败: %s", e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="保存失败",
            )
        try:
            await broadcast_spare_part_changed()
        except Exception as e:
            logger.warning("广播备件变更失败: %s", e)
        invalidate_filter_options_cache()
    return {
        "updated": updated_count,
        "skipped": skipped_count,
        "errors": errors[:100],
    }


@router.post("/{part_id}/sync-images", tags=["备件管理"])
async def sync_images_for_spare_part(
    part_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_electrical),
):
    """
    同步备件的图片数据到spare_parts表的字段
    用于修复数据不一致问题
    """
    try:
        result = sync_spare_part_images(db, part_id)
        if result is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"备件ID {part_id} 不存在"
            )
        if result.get("updated"):
            try:
                await broadcast_spare_part_changed()
            except Exception as e:
                logger.warning("广播备件变更失败: %s", e)
        return {
            "success": True,
            "message": f"备件 {part_id} 图片数据同步{'成功' if result['updated'] else '无需更新'}",
            "data": result
        }
    except Exception as e:
        if isinstance(e, HTTPException):
            raise
        logger.error(f"同步备件图片失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"同步图片数据失败: {str(e)}"
        )