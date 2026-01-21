# 周报自动发送机器人

自动复制上周周报、更新日期和待办事项、发送到飞书群。

## 功能

- 每周二上午 11 点自动发送周报到指定群聊（标题日期为周三会议日）
- 通过 @ 机器人添加待办事项
- 支持跳过某周周报（节假日）
- 卡片消息展示周报链接和待办
- 周报记录自动汇总到多维表格

## 使用方法

### 群聊命令

| 命令 | 说明 |
|------|------|
| `@机器人 todo <内容>` | 添加待办事项 |
| `@机器人 跳过本周` | 跳过本周周报 |
| `@机器人 取消跳过` | 恢复本周周报 |
| `@机器人 状态` | 查看当前状态 |
| `@机器人 帮助` | 显示帮助信息 |

## 部署

### 1. 配置飞书应用

1. 在 [飞书开放平台](https://open.feishu.cn) 创建企业自建应用
2. 添加机器人能力
3. 配置权限：
   - `im:message:send_as_bot` - 发送消息
   - `im:message:receive_as_bot` - 接收消息
   - `wiki:wiki:readonly` - 读取知识库
   - `wiki:wiki` - 编辑知识库
   - `docx:document:readonly` - 读取文档
   - `drive:drive:permission` - 管理文档权限
   - `bitable:app:write` - 写入多维表格
4. 配置事件订阅：
   - 请求地址: `https://your-domain.com/webhook/event`
   - 事件: `im.message.receive_v1`

### 2. 环境变量

复制 `.env.example` 为 `.env` 并填写配置：

```bash
cp .env.example .env
```

### 3. 启动服务

```bash
# 使用 Docker
docker-compose up -d

# 或直接运行
pip install -r requirements.txt
python -m src.main
```

## 开发

```bash
# 安装依赖
pip install -r requirements.txt

# 运行测试
pytest

# 手动触发周报（测试）
curl -X POST http://localhost:8080/api/trigger

# 查看状态
curl http://localhost:8080/api/status
```

## API 接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/webhook/event` | POST | 飞书事件回调 |
| `/api/trigger` | POST | 手动触发周报发送 |
| `/api/status` | GET | 获取当前状态 |
| `/health` | GET | 健康检查 |
