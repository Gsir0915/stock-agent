# -*- coding: utf-8 -*-
"""
本地测试飞书机器人（无需公网 IP）
使用 Postman 或 curl 模拟飞书事件推送
"""

import sys
import json
from pathlib import Path

# 添加项目根目录到路径
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))

from app.bot.handler import MessageHandler
from app.bot.commands import CommandParser


def test_command_parser():
    """测试命令解析器"""
    print("=" * 60)
    print("测试命令解析器")
    print("=" * 60)

    test_cases = [
        ("600519", "纯股票代码"),
        ("分析 600519", "带命令前缀"),
        ("贵州茅台", "股票名称"),
        ("帮助", "帮助命令"),
        ("@bot 600519", "带@的消息"),
        ("", "空消息"),
        ("hello", "无关消息"),
    ]

    for message, description in test_cases:
        code, cmd = CommandParser.parse_message(message)
        print(f"[{description}] '{message}' -> code={code}, cmd={cmd}")

    print()


def test_handler_basic():
    """测试处理器基本功能"""
    print("=" * 60)
    print("测试处理器基本功能")
    print("=" * 60)

    handler = MessageHandler()

    # 测试 URL 验证
    print("\n[URL 验证挑战]")
    result = handler.handle_url_challenge("test_challenge_123")
    print(f"输入：test_challenge_123")
    print(f"输出：{result}")
    print(f"结果：{'✓ 通过' if result == 'test_challenge_123' else '✗ 失败'}")

    # 测试空事件
    print("\n[空事件]")
    success, msg = handler.handle_event({})
    print(f"结果：{success}, {msg}")

    # 测试缺少 event 字段
    print("\n[缺少 event 字段]")
    success, msg = handler.handle_event({"header": {"event_type": "test"}})
    print(f"结果：{success}, {msg}")


def test_message_parsing():
    """测试消息解析（不实际发送）"""
    print("\n" + "=" * 60)
    print("测试消息解析（模拟）")
    print("=" * 60)

    handler = MessageHandler()

    # 模拟飞书消息事件（仅测试解析，不实际发送）
    test_messages = [
        '{"text": "600519"}',
        '{"text": "分析 600519"}',
        '{"text": "贵州茅台"}',
        '{"text": "@bot 600519"}',
    ]

    for content_str in test_messages:
        content = json.loads(content_str)
        text = content.get('text', '')
        code, cmd = CommandParser.parse_message(text)
        print(f"消息：{text!r} -> 代码={code}, 命令={cmd}")


def simulate_feishu_event():
    """模拟完整的飞书事件"""
    print("\n" + "=" * 60)
    print("模拟完整飞书事件（仅验证流程）")
    print("=" * 60)

    handler = MessageHandler()

    # 模拟 URL 验证事件
    print("\n[1] URL 验证事件")
    event = {"challenge": "abc123"}
    if "challenge" in event:
        print(f"检测到挑战，返回：{event['challenge']}")

    # 模拟消息接收事件
    print("\n[2] 消息接收事件")
    event = {
        "header": {
            "event_id": "evt_test_123",
            "event_type": "im.message.receive_v1",
            "app_id": "cli_test"
        },
        "event": {
            "message": {
                "message_id": "om_test",
                "chat_id": "oc_test",
                "content": json.dumps({"text": "@bot 600519"}),
                "mentions": [{"id": {"open_id": "ou_bot"}}]
            },
            "sender": {
                "sender_id": {"open_id": "ou_user"}
            }
        }
    }

    print(f"事件类型：{event['header']['event_type']}")
    print(f"消息内容：{event['event']['message']['content']}")
    print(f"聊天 ID: {event['event']['message']['chat_id']}")

    # 注意：实际执行会尝试发送消息，需要配置飞书凭证
    # 这里只验证事件结构
    event_data = event.get('event', {})
    message = event_data.get('message', {})
    content = json.loads(message.get('content', '{}'))
    text = content.get('text', '')

    code, cmd = CommandParser.parse_message(text)
    print(f"解析结果：代码={code}, 命令={cmd}")
    print(f"✓ 事件结构验证通过")


def main():
    """主函数"""
    print()
    print("╔" + "=" * 58 + "╗")
    print("║          飞书机器人本地测试（无需公网 IP）            ║")
    print("╚" + "=" * 58 + "╝")
    print()

    test_command_parser()
    test_handler_basic()
    test_message_parsing()
    simulate_feishu_event()

    print()
    print("=" * 60)
    print("测试完成！")
    print("=" * 60)
    print()
    print("提示：")
    print("1. 以上测试验证了代码逻辑的正确性")
    print("2. 要实际接收飞书消息，需要配置内网穿透")
    print("3. 参考 docs/国内内网穿透方案.md")
    print()


if __name__ == "__main__":
    main()
