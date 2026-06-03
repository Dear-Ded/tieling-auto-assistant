# 自动化工具清单

> 此文件由 sys-管家维护，记录所有可用的自动化机制。

## 定时任务（Automation）

WorkBuddy 内置自动化系统，支持：
- 一次性任务（scheduleType=once）
- 周期性任务（scheduleType=recurring，支持 RRULE）

### 常用 RRULE

| 场景 | RRULE |
|------|-------|
| 每天 | `FREQ=DAILY` |
| 每周一 | `FREQ=WEEKLY;BYDAY=MO` |
| 每月1号 | `FREQ=MONTHLY;BYMONTHDAY=1` |
| 每小时 | `FREQ=HOURLY` |
| 工作日 | `FREQ=DAILY;BYDAY=MO,TU,WE,TH,FR` |

### 自动化配置

- 存储位置：`$HOME/.workbuddy/workbuddy.db`（SQLite）
- 管理方式：`automation_update` 工具
- 状态：`ACTIVE` / `PAUSED`

## 自启动能力

| 能力 | 状态 | 说明 |
|------|------|------|
| 文件监听 | ❌ | 需安装 fs-watch MCP |
| 定时执行 | ✅ | 内置 automation |
| 事件触发 | ❌ | 待开发 |

## 全自主操作清单

| 操作 | 工具 | 自主程度 |
|------|------|----------|
| 文件读写 | Bash/Read/Write | ✅ 完全自主 |
| 网页搜索 | WebSearch | ✅ 完全自主 |
| 网页抓取 | WebFetch | ✅ 完全自主 |
| 命令执行 | Bash/PowerShell | ✅ 完全自主 |
| 包安装 | npm/pip | ✅ 完全自主（不装C盘） |
| Word/PPT/Excel | docx/pptx/xlsx | ✅ 完全自主 |
| 浏览器控制 | agent-browser | ✅ 已安装 |
| 桌面控制 | MCPControl | ❌ 未安装 |
| 屏幕点击 | win32-mcp-server | ❌ 未安装 |
| 邮件发送 | - | ❌ 未配置 |

## 待安装自动化工具

| 工具 | 优先级 | 用途 |
|------|--------|------|
| MCPControl | 🔴高 | 桌面自动化 |
| win32-mcp-server | 🔴高 | Windows屏幕控制 |
| 邮件MCP | 🟡中 | 自动发邮件 |
| 定时任务增强 | 🟢低 | 复杂定时逻辑 |

> 每次安装/配置新自动化工具，sys-管家立即更新本文件。
