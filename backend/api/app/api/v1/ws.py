# app/api/v1/ws.py
"""WebSocket 端点：备件数据变更广播，支持跨浏览器、跨终端实时推送。"""
import asyncio
import json
import logging
import time
from typing import Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

router = APIRouter()

# 当前所有已连接的 WebSocket 客户端（单 worker 内存集合；多 worker 时可改用 Redis Pub/Sub）
_connections: Set[WebSocket] = set()
_event_type = "spare-part-changed"


def _payload(at: int) -> str:
    return json.dumps({"type": _event_type, "at": at})


async def broadcast_spare_part_changed() -> None:
    """向所有已连接的 WebSocket 客户端广播「备件数据已变更」。跨浏览器、跨终端均能收到。"""
    if not _connections:
        return
    at = int(time.time_ns() / 1_000_000)
    payload = _payload(at)
    dead: Set[WebSocket] = set()
    for ws in list(_connections):
        try:
            await ws.send_text(payload)
        except Exception as e:
            logger.warning("广播时发送失败，移除连接: %s", e)
            dead.add(ws)
    for ws in dead:
        _connections.discard(ws)
        try:
            await ws.close()
        except Exception:
            pass


@router.websocket("/ws/spare-part-events")
async def spare_part_events_ws(websocket: WebSocket) -> None:
    """客户端连接此 WebSocket 后，可收到备件增删改、领用等变更的实时推送。"""
    await websocket.accept()
    _connections.add(websocket)
    logger.info("WebSocket 客户端接入 spare-part-events，当前连接数: %d", len(_connections))
    try:
        while True:
            # 保持连接；可接收 ping 或忽略客户端消息
            data = await asyncio.wait_for(websocket.receive_text(), timeout=60.0)
            # 可选：处理 ping/pong 等，这里仅保活
            if data.strip().lower() == "ping":
                await websocket.send_text(json.dumps({"type": "pong", "at": int(time.time_ns() / 1_000_000)}))
    except (WebSocketDisconnect, asyncio.TimeoutError) as e:
        logger.info("WebSocket 断开: %s", e)
    except Exception as e:
        logger.warning("WebSocket 异常: %s", e)
    finally:
        _connections.discard(websocket)
        try:
            await websocket.close()
        except Exception:
            pass
        logger.info("spare-part-events 连接已移除，当前连接数: %d", len(_connections))


# 机械备件 WebSocket
_mechanical_connections: Set[WebSocket] = set()
_mechanical_event_type = "mechanical-spare-part-changed"


def _mechanical_payload(at: int) -> str:
    return json.dumps({"type": _mechanical_event_type, "at": at})


async def broadcast_mechanical_spare_part_changed() -> None:
    """向所有已连接的 WebSocket 客户端广播「机械备件数据已变更」。跨浏览器、跨终端均能收到。"""
    if not _mechanical_connections:
        return
    at = int(time.time_ns() / 1_000_000)
    payload = _mechanical_payload(at)
    dead: Set[WebSocket] = set()
    for ws in list(_mechanical_connections):
        try:
            await ws.send_text(payload)
        except Exception as e:
            logger.warning("机械备件广播时发送失败，移除连接: %s", e)
            dead.add(ws)
    for ws in dead:
        _mechanical_connections.discard(ws)
        try:
            await ws.close()
        except Exception:
            pass


@router.websocket("/ws/mechanical-spare-part-events")
async def mechanical_spare_part_events_ws(websocket: WebSocket) -> None:
    """客户端连接此 WebSocket 后，可收到机械备件增删改、领用等变更的实时推送。"""
    await websocket.accept()
    _mechanical_connections.add(websocket)
    logger.info("WebSocket 客户端接入 mechanical-spare-part-events，当前连接数: %d", len(_mechanical_connections))
    try:
        while True:
            data = await asyncio.wait_for(websocket.receive_text(), timeout=60.0)
            if data.strip().lower() == "ping":
                await websocket.send_text(json.dumps({"type": "pong", "at": int(time.time_ns() / 1_000_000)}))
    except (WebSocketDisconnect, asyncio.TimeoutError) as e:
        logger.info("WebSocket 机械备件断开: %s", e)
    except Exception as e:
        logger.warning("WebSocket 机械备件异常: %s", e)
    finally:
        _mechanical_connections.discard(websocket)
        try:
            await websocket.close()
        except Exception:
            pass
        logger.info("mechanical-spare-part-events 连接已移除，当前连接数: %d", len(_mechanical_connections))
