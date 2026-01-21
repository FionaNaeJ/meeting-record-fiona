# LLM 意图识别设计

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 用豆包 LLM 替换正则匹配，实现自然语言意图识别

**Architecture:** 用户消息 → LLM 意图识别 → 4种意图 → 执行操作

**Tech Stack:** 豆包 1.6 lite (ARK API)，OpenAI 兼容格式

---

## 意图类型

| 意图 | 示例 | 动作 |
|------|------|------|
| `todo` | "本周todo：1、2、3" | 保存 todo，更新周报文档，回复「已接收」 |
| `send_report` | "发一下本周周报" | 发送周报链接 |
| `skip` | "这周跳过" | 标记跳过，回复确认 |
| `cancel_skip` | "还是发吧" | 取消跳过，回复确认 |
| `unknown` | 其他 | 不回复 |

---

## 工作流程

### 收到 todo 时
1. LLM 识别意图 → todo
2. 检查本周周报是否已创建
   - 未创建 → 复制上周周报 → 读取 todo 区块 → 删除已勾选的 → 追加新 todo
   - 已创建 → 直接追加新 todo
3. 回复「已接收」

### 周二 11 点
1. 检查本周周报是否已创建
   - 未创建 → 复制上周周报 → 清理已完成 todo
   - 已创建 → 跳过
2. 发送周报链接到群（除非已跳过）

---

## LLM Prompt

```
你是一个周报机器人的意图识别器。根据用户消息，返回 JSON：

意图类型：
- todo: 用户发送待办事项
- send_report: 用户要求发送某周周报
- skip: 用户要求跳过某周周报
- cancel_skip: 用户取消跳过
- unknown: 无法识别

返回格式（只返回 JSON，不要其他内容）：
{"intent": "xxx", "content": "提取的内容或null"}

示例：
用户：本周todo：开会、写文档
返回：{"intent": "todo", "content": "开会、写文档"}

用户：发一下上周周报
返回：{"intent": "send_report", "content": "上周"}

用户：这周周会跳过
返回：{"intent": "skip", "content": null}

用户：还是发吧
返回：{"intent": "cancel_skip", "content": null}

用户：今天天气真好
返回：{"intent": "unknown", "content": null}
```

---

## 配置

```
ARK_API_KEY=da657c2f-0dc6-4411-a780-e92a70c3f58a
ARK_MODEL_ENDPOINT=ep-20260121163501-qq8rl
ARK_BASE_URL=https://ark.cn-beijing.volces.com/api/v3
```

---

## 实现任务

### Task 1: 添加 ARK 配置
- 更新 `.env` 添加 ARK 配置
- 更新 `src/config.py` 读取配置

### Task 2: 创建 LLM 意图识别服务
- 创建 `src/services/intent_service.py`
- 调用豆包 API，返回意图和内容
- 处理 API 错误

### Task 3: 更新 CommandHandler
- 用 IntentService 替换正则匹配
- 移除 status 和 help 命令
- 添加 send_report 意图处理

### Task 4: 更新文档服务 - 读取并清理已完成 todo
- 读取文档 block
- 识别 checkbox block
- 过滤已勾选的 todo
- 保留未完成的

### Task 5: 更新 todo 流程 - 实时更新周报
- 收到 todo 时检查本周周报是否存在
- 不存在则创建
- 追加 todo 到文档

### Task 6: 更新定时任务
- 周二 11 点检查周报是否存在
- 不存在则创建
- 发送链接（除非跳过）
