#!/usr/bin/env python3
"""
core/message_bus.py — v1.1.0 真并发 Agent 消息通信总线

华尔街驻铁岭办事处 · 多 Agent 异步消息系统

特性:
  - Pub/Sub 模式：Agent 订阅主题，发布消息
  - 点对点消息：Agent 直连通信
  - 消息队列：支持优先级、延迟投递
  - 事件溯源：完整消息历史可回溯
  - 类型安全：结构化消息信封
"""

from __future__ import annotations

import json
import time
import uuid
import threading
from collections import defaultdict, deque
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Union
from pathlib import Path


# ─── 消息类型 ─────────────────────────────────────────────────

class MessageType(Enum):
    """消息类别"""
    TASK = "task"               # 任务分配
    RESULT = "result"           # 结果回传
    QUERY = "query"             # 信息查询
    NOTIFY = "notify"           # 通知/告警
    SYNC = "sync"               # 状态同步
    ERROR = "error"             # 错误报告
    HEARTBEAT = "heartbeat"     # 心跳
    HANDOFF = "handoff"         # 任务移交


class Priority(Enum):
    """消息优先级"""
    URGENT = 0      # 紧急: 立即处理
    HIGH = 1        # 高: 优先队列
    NORMAL = 2      # 普通: 标准队列
    LOW = 3         # 低: 空闲时处理
    BACKGROUND = 4  # 后台: 批量处理


@dataclass
class MessageEnvelope:
    """消息信封 — 包含完整路由和追踪信息"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    type: MessageType = MessageType.TASK
    priority: Priority = Priority.NORMAL

    sender: str = ""          # 发送方 Agent ID
    recipient: str = ""       # 接收方 Agent ID (空=广播)
    topic: str = ""           # 订阅主题

    subject: str = ""         # 消息主题 (人类可读)
    body: Any = None          # 消息体 (任意 JSON 可序列化)
    metadata: Dict[str, Any] = field(default_factory=dict)

    # 追踪
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    correlation_id: Optional[str] = None    # 用于关联请求-响应
    reply_to: Optional[str] = None          # 回复地址

    # 生命周期
    ttl: int = 300                          # 存活时间 (秒)
    retries: int = 0
    max_retries: int = 3
    status: str = "pending"                 # pending | delivered | acknowledged | failed | expired

    def to_dict(self) -> dict:
        d = asdict(self)
        d["type"] = self.type.value
        d["priority"] = self.priority.value
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "MessageEnvelope":
        d = dict(d)
        d["type"] = MessageType(d["type"])
        d["priority"] = Priority(d["priority"])
        return cls(**d)


# ─── 消息总线 ─────────────────────────────────────────────────

class MessageBus:
    """异步 Agent 消息总线 — Pub/Sub + P2P + 事件溯源

    使用方式:
        bus = MessageBus()
        bus.subscribe("dd", "enterprise_data", callback)
        bus.publish(MessageEnvelope(sender="lead", topic="enterprise_data", body={...}))
    """

    def __init__(self, history_path: Optional[str] = None):
        self._lock = threading.RLock()

        # 订阅表: agent_id -> topic -> [callbacks]
        self._subscriptions: Dict[str, Dict[str, List[Callable]]] = defaultdict(lambda: defaultdict(list))

        # 消息队列: 按优先级分桶
        self._queues: Dict[Priority, deque] = {
            Priority.URGENT: deque(),
            Priority.HIGH: deque(),
            Priority.NORMAL: deque(),
            Priority.LOW: deque(),
            Priority.BACKGROUND: deque(),
        }

        # 投递历史 (完整事件溯源)
        self._history: List[MessageEnvelope] = []
        self._history_path = Path(history_path) if history_path else None

        # Agent 在线状态
        self._online: Set[str] = set()

        # 处理线程
        self._running = False
        self._worker: Optional[threading.Thread] = None

        # 延迟投递
        self._delayed: List[tuple] = []  # (deliver_at, envelope)

        # 统计
        self._stats = {
            "published": 0,
            "delivered": 0,
            "failed": 0,
            "expired": 0,
        }

    # ── 订阅管理 ──────────────────────────────────────────

    def subscribe(self, agent_id: str, topic: str, callback: Callable[[MessageEnvelope], Any]):
        """订阅主题 - agent_id 向 topic 注册回调"""
        with self._lock:
            self._subscriptions[agent_id][topic].append(callback)
            self._online.add(agent_id)

    def unsubscribe(self, agent_id: str, topic: Optional[str] = None):
        """取消订阅"""
        with self._lock:
            if topic:
                self._subscriptions[agent_id].pop(topic, None)
            else:
                self._subscriptions.pop(agent_id, None)

    # ── 发布 / 投递 ─────────────────────────────────────

    def publish(self, envelope: MessageEnvelope) -> str:
        """发布消息 - 异步投递到对应队列"""
        envelope.timestamp = datetime.now().isoformat()
        envelope.status = "pending"

        with self._lock:
            self._stats["published"] += 1
            queue = self._queues[envelope.priority]
            queue.append(envelope)

        return envelope.id

    def send_direct(self, sender: str, recipient: str, subject: str, body: Any,
                    msg_type: MessageType = MessageType.QUERY,
                    priority: Priority = Priority.NORMAL) -> str:
        """点对点直连消息"""
        envelope = MessageEnvelope(
            sender=sender,
            recipient=recipient,
            subject=subject,
            body=body,
            type=msg_type,
            priority=priority,
        )
        return self.publish(envelope)

    def broadcast(self, sender: str, topic: str, subject: str, body: Any,
                  exclude: Optional[List[str]] = None) -> str:
        """广播消息到所有订阅了 topic 的 Agent"""
        envelope = MessageEnvelope(
            sender=sender,
            topic=topic,
            subject=subject,
            body=body,
            type=MessageType.NOTIFY,
            priority=Priority.NORMAL,
        )
        envelope.metadata["exclude"] = exclude or []
        return self.publish(envelope)

    def send_delayed(self, envelope: MessageEnvelope, delay_seconds: int) -> str:
        """延迟投递"""
        deliver_at = time.time() + delay_seconds
        with self._lock:
            self._delayed.append((deliver_at, envelope))
        return envelope.id

    # ── 消费 / 投递循环 ─────────────────────────────────

    def start(self):
        """启动消息处理循环（后台线程）"""
        if self._running:
            return
        self._running = True
        self._worker = threading.Thread(target=self._process_loop, daemon=True)
        self._worker.start()

    def stop(self):
        """停止消息处理"""
        self._running = False
        if self._worker:
            self._worker.join(timeout=5)

    def _process_loop(self):
        """后台消息处理循环"""
        while self._running:
            self._tick()
            time.sleep(0.05)  # 20Hz

    def _tick(self):
        """单次处理周期"""
        # 1. 处理延迟消息
        now = time.time()
        with self._lock:
            ready = [d for d in self._delayed if d[0] <= now]
            for _, envelope in ready:
                self._queues[envelope.priority].append(envelope)
            self._delayed = [d for d in self._delayed if d[0] > now]

        # 2. 从高优先级开始投递
        for priority in [Priority.URGENT, Priority.HIGH, Priority.NORMAL, Priority.LOW, Priority.BACKGROUND]:
            with self._lock:
                if not self._queues[priority]:
                    continue
                envelope = self._queues[priority].popleft()

            # 检查 TTL
            try:
                ts = datetime.fromisoformat(envelope.timestamp)
                if (datetime.now() - ts).total_seconds() > envelope.ttl:
                    with self._lock:
                        envelope.status = "expired"
                        self._stats["expired"] += 1
                        self._history.append(envelope)
                    continue
            except (ValueError, TypeError):
                pass

            # 投递
            delivered = self._deliver(envelope)
            if not delivered and envelope.retries < envelope.max_retries:
                envelope.retries += 1
                with self._lock:
                    self._queues[priority].append(envelope)
            elif not delivered:
                with self._lock:
                    envelope.status = "failed"
                    self._stats["failed"] += 1
                    self._history.append(envelope)
            else:
                with self._lock:
                    envelope.status = "delivered"
                    self._stats["delivered"] += 1
                    self._history.append(envelope)

    def _deliver(self, envelope: MessageEnvelope) -> bool:
        """投递消息到目标"""
        delivered = False

        if envelope.recipient:
            # 点对点: 发送到指定 Agent 的所有订阅
            sub = self._subscriptions.get(envelope.recipient, {})
            topic = envelope.topic or "__default__"
            callbacks = sub.get(topic, [])
            if not callbacks:
                callbacks = sub.get("__all__", [])  # 兜底: 全局监听

            for cb in callbacks:
                try:
                    cb(envelope)
                    delivered = True
                except Exception:
                    continue

        elif envelope.topic:
            # 广播: 发送到所有订阅了该 topic 的 Agent
            exclude = set(envelope.metadata.get("exclude", []))
            for agent_id, topics in self._subscriptions.items():
                if agent_id in exclude:
                    continue
                for cb in topics.get(envelope.topic, []):
                    try:
                        cb(envelope)
                        delivered = True
                    except Exception:
                        continue

        return delivered

    # ── 查询和历史 ───────────────────────────────────────

    def get_history(self, agent_id: Optional[str] = None, limit: int = 100) -> List[MessageEnvelope]:
        """获取消息历史"""
        with self._lock:
            if agent_id:
                return [
                    h for h in self._history[-limit:]
                    if h.sender == agent_id or h.recipient == agent_id
                ]
            return list(self._history[-limit:])

    def query(self, correlation_id: str) -> Optional[MessageEnvelope]:
        """按 correlation_id 查找"""
        with self._lock:
            for h in reversed(self._history):
                if h.correlation_id == correlation_id:
                    return h
        return None

    def get_stats(self) -> dict:
        """获取统计信息"""
        with self._lock:
            stats = dict(self._stats)
            stats["queue_depth"] = sum(len(q) for q in self._queues.values())
            stats["online_agents"] = len(self._online)
            stats["active_subscriptions"] = sum(
                len(topics) for topics in self._subscriptions.values()
            )
        return stats

    def is_online(self, agent_id: str) -> bool:
        """检查 Agent 是否在线"""
        return agent_id in self._online

    def save_history(self):
        """持久化消息历史"""
        if not self._history_path:
            return
        with self._lock:
            data = [h.to_dict() for h in self._history[-1000:]]
        self._history_path.parent.mkdir(parents=True, exist_ok=True)
        self._history_path.write_text(json.dumps(data, ensure_ascii=False, indent=2))


# ─── 便捷工厂 ─────────────────────────────────────────────────

def create_bus(history_path: str = ".wallstreet/message_history.json") -> MessageBus:
    """创建默认配置的消息总线"""
    bus = MessageBus(history_path=history_path)
    bus.start()
    return bus
