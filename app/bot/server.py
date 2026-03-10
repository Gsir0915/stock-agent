# -*- coding: utf-8 -*-
"""
HTTP 服务器模块
使用 FastAPI 创建轻量 HTTP 服务器，接收飞书事件推送
"""

import uvicorn
import asyncio
import json
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, PlainTextResponse
from typing import Dict, Any, Optional, Tuple
import hashlib
import base64
import time
import hmac

from .handler import MessageHandler
from ..config import get_config
from ..utils.logger import get_logger

logger = get_logger("bot.server")

# 用于去重的 event_id 集合（避免飞书重试导致重复处理）
processed_events: Dict[str, float] = {}
EVENT_DEDUPE_WINDOW = 300  # 5 分钟去重窗口

# 用于去重已处理的消息（基于 message_id，避免飞书重试导致重复处理）
# Key: message_id, Value: 处理完成的时间戳
processed_messages: Dict[str, float] = {}
MESSAGE_DEDUPE_WINDOW = 600  # 10 分钟去重窗口（飞书重试最长可达 5 分钟）

# 后台清理任务
_cleanup_task: Optional[asyncio.Task] = None


async def cleanup_expired_entries():
    """后台清理过期的去重记录"""
    while True:
        try:
            await asyncio.sleep(60)  # 每分钟清理一次
            current_time = time.time()

            # 清理过期的 event_id
            expired_events = [eid for eid, t in processed_events.items()
                             if current_time - t > EVENT_DEDUPE_WINDOW]
            for eid in expired_events:
                del processed_events[eid]

            # 清理过期的 message_id
            expired_msgs = [mid for mid, t in processed_messages.items()
                           if current_time - t > MESSAGE_DEDUPE_WINDOW]
            for mid in expired_msgs:
                del processed_messages[mid]

            logger.debug(f"清理完成，当前 event_id 数量：{len(processed_events)}, message_id 数量：{len(processed_messages)}")
        except Exception as e:
            logger.exception(f"清理任务异常：{e}")


def start_cleanup_task():
    """启动后台清理任务"""
    global _cleanup_task
    if _cleanup_task is None or _cleanup_task.done():
        _cleanup_task = asyncio.create_task(cleanup_expired_entries())
        logger.info("后台清理任务已启动")


def create_app() -> FastAPI:
    """创建 FastAPI 应用"""
    app = FastAPI(
        title="Feishu Stock Bot",
        description="飞书股票分析机器人事件订阅服务",
        version="1.0.0"
    )

    # 初始化消息处理器
    handler = MessageHandler()

    @app.on_event("startup")
    async def startup_event():
        """应用启动时启动后台清理任务"""
        start_cleanup_task()
        logger.info("应用启动完成")

    @app.get("/health")
    async def health_check():
        """健康检查端点"""
        return {"status": "ok", "timestamp": int(time.time())}

    @app.post("/feishu/event")
    async def handle_feishu_event(request: Request):
        """
        处理飞书事件推送

        飞书开放平台会将事件推送到此端点

        注意：为了应对飞书 3 秒超时重试机制，此端点会立即返回响应，
        实际的消息处理在后台异步执行。
        """
        logger.info("收到飞书事件推送")

        try:
            # 获取请求头
            headers = dict(request.headers)
            logger.debug(f"请求头：{list(headers.keys())}")

            # 获取请求体
            body = await request.json()
            logger.info(f"收到飞书事件推送：{body}")

            # 检查是否是 URL 验证请求（优先处理）
            if body.get("type") == "url_verification" or "challenge" in body:
                logger.info("处理 URL 验证请求")
                challenge = body.get("challenge")
                # 飞书要求返回 JSON 格式，包含 challenge 字段
                return JSONResponse(content={"challenge": challenge})

            # 验证请求来源（可选，增强安全性）
            if not verify_feishu_request(headers, body):
                logger.warning("请求验证失败")
                raise HTTPException(status_code=401, detail="Invalid request signature")

            # 处理事件
            event_type = body.get("header", {}).get("event_type", "")
            logger.info(f"处理事件类型：{event_type}")

            # 根据事件类型处理
            if event_type == "im.message.receive_v1":
                # 消息接收事件
                # 获取 event_id 用于去重（防止飞书重试导致重复处理）
                event_id = body.get("header", {}).get("event_id", "")

                # 提取消息信息用于去重（使用 message_id，因为同一消息的 message_id 始终相同）
                event = body.get("event", {})
                message = event.get("message", {})
                message_id = message.get("message_id", "")
                sender = event.get("sender", {})

                # 检查是否已经处理过此事件（event_id 去重 - 第一道防线）
                if event_id in processed_events:
                    logger.info(f"事件已处理过，忽略重复请求：{event_id}")
                    return JSONResponse(
                        status_code=200,
                        content={"code": 0, "msg": "success"}
                    )

                # 检查是否已经处理过此消息（message_id 去重 - 第二道防线）
                # 即使 event_id 不同，只要 message_id 相同就表示是同一个消息的重试
                if message_id and message_id in processed_messages:
                    logger.info(f"消息已处理过，忽略重复请求：{message_id} (event_id: {event_id})")
                    return JSONResponse(
                        status_code=200,
                        content={"code": 0, "msg": "success"}
                    )

                # 先标记 event_id 防止同 event_id 的重试
                processed_events[event_id] = time.time()

                # 异步处理消息（后台执行）
                # 飞书允许在收到事件后先返回成功响应，然后在后台处理
                asyncio.create_task(process_message_async(body, message_id or event_id, message_id))

                # 立即返回成功响应
                # 飞书事件订阅标准响应格式：code=0 表示成功
                return JSONResponse(
                    status_code=200,
                    content={"code": 0, "msg": "success"}
                )

            elif event_type == "url_verification":
                # URL 验证事件（备用处理）
                challenge = body.get("challenge")
                return JSONResponse(content={"challenge": challenge})

            else:
                # 其他事件类型，返回成功但不处理
                logger.info(f"未处理的事件类型：{event_type}")
                return JSONResponse(
                    status_code=200,
                    content={"code": 0, "msg": "success"}
                )

        except HTTPException:
            raise
        except Exception as e:
            logger.exception(f"处理飞书事件异常：{e}")
            return JSONResponse(
                status_code=500,
                content={"error": "Internal server error", "message": str(e)}
            )

    return app


async def process_message_async(body: Dict[str, Any], message_id: str, dedupe_key: str = None) -> Tuple[bool, str]:
    """
    处理消息（同步或异步）

    Args:
        body: 请求体数据
        message_id: 消息 ID，用于日志记录
        dedupe_key: 用于去重的 key（默认为 message_id）

    Returns:
        (success, message) 元组
    """
    try:
        handler = MessageHandler()
        success, message = handler.handle_event(body)
        if success:
            logger.info(f"消息处理成功：{message}")
            # 只有成功后才标记为已处理，防止失败的消息被错误拦截
            if dedupe_key:
                processed_messages[dedupe_key] = time.time()
            return True, message
        else:
            logger.warning(f"消息处理失败：{message}")
            # 失败时不标记，允许飞书重试
            return False, message
    except Exception as e:
        logger.exception(f"异步处理消息异常：{e}")
        # 异常时不标记，允许飞书重试
        return False, str(e)


def verify_feishu_request(headers: Dict[str, str], body: Dict[str, Any]) -> bool:
    """
    验证飞书请求签名（可选的安全措施）

    飞书会在请求头中发送签名，可以使用此函数验证请求来源

    Args:
        headers: 请求头
        body: 请求体

    Returns:
        True 如果验证通过
    """
    # 获取配置
    config = get_config()
    verification_token = config.feishu_verification_token

    if not verification_token:
        # 如果没有配置 verification token，跳过验证
        logger.debug("未配置 verification token，跳过签名验证")
        return True

    # 飞书签名验证逻辑
    # 注意：飞书的签名验证方式可能变化，请参考最新文档
    # 这里实现基本的验证逻辑

    # 从请求头获取签名
    signature = headers.get("X-Lark-Signature", "")
    timestamp = headers.get("X-Lark-Timestamp", "")
    nonce = headers.get("X-Lark-Nonce", "")

    if not all([signature, timestamp, nonce]):
        logger.debug("请求头中缺少签名信息")
        # 某些事件可能不包含签名，不强制验证
        return True

    # 构建待签名字符串
    body_str = ""
    if body:
        import json
        body_str = json.dumps(body, separators=(',', ':'))

    sign_str = f"{timestamp}{nonce}{verification_token}{body_str}"

    # 计算签名
    signature_calculated = hmac.new(
        verification_token.encode('utf-8'),
        sign_str.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

    # 比较签名
    if signature != f"v1={signature_calculated}":
        logger.warning("签名验证失败")
        return False

    logger.debug("签名验证通过")
    return True


def _extract_stock_code_from_text(text: str) -> Optional[str]:
    """
    从消息文本中提取股票代码（用于去重 key）

    Args:
        text: 消息文本

    Returns:
        股票代码，如果无法提取则返回 None
    """
    import re

    if not text:
        return None

    # 尝试匹配 6 位数字股票代码
    match = re.search(r'\b(\d{6})\b', text)
    if match:
        return match.group(1)

    # 如果没有找到股票代码，返回原始文本（去除空白）
    text_clean = text.strip()
    if text_clean:
        return text_clean

    return None


def run_server(host: str = "0.0.0.0", port: int = None, log_level: str = "info"):
    """
    运行 HTTP 服务器

    Args:
        host: 监听地址
        port: 监听端口（默认从配置读取）
        log_level: 日志级别
    """
    config = get_config()
    port = port or config.feishu_bot_port

    app = create_app()

    logger.info(f"启动飞书机器人服务器：http://{host}:{port}")
    logger.info(f"事件订阅端点：POST /feishu/event")
    logger.info(f"健康检查端点：GET /health")

    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level=log_level
    )


# 便捷函数
def get_server_app() -> FastAPI:
    """获取 FastAPI 应用实例（用于其他模块导入）"""
    return create_app()
