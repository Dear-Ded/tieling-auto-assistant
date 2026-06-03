# 全自主能力架构

> 由朱之文/钱守正维护，周通/孙笑川负责能力猎取。目标：用户一句话，全链路自动执行。

---

## 一、能力矩阵

### ✅ 已有能力（可直接用）

| 层级 | 能力域 | 具体能力 | 工具 |
|------|--------|----------|------|
| **文件** | 读写 | 文件读写/搜索/编辑 | Read/Write/Edit/Glob/Grep |
| **文件** | 文档 | Word/PPT/Excel/PDF | docx/pptx/xlsx/pdf |
| **系统** | 命令 | Bash/PowerShell | 内置 |
| **系统** | 包管理 | npm/pip 安装到D盘 | 运行时隔离 |
| **网络** | 搜索 | WebSearch | 内置 |
| **网络** | 抓取 | WebFetch | 内置 |
| **网络** | 浏览器 | 无头浏览器自动化 | agent-browser |
| **内容** | 写作 | 多风格文案/报告 | humanizer/content-匠人 |
| **内容** | 小红书 | 搜索/发布/分析 | xiaohongshu |
| **内容** | 去AI味 | 人味儿写作 | humanizer |
| **数据** | 表格 | Excel处理 | xlsx |
| **数据** | 分析 | Python/Pandas | 运行时 |
| **开发** | 代码 | 多语言代码生成 | code-技师 |
| **开发** | GitHub | Issue/PR/CI | github |
| **开发** | 前端 | 网页/UI | frontend-design |
| **开发** | Skill | 创建/安装技能 | skill-creator/find-skills |
| **多媒体** | 图片 | AI图片生成 | openai-image-gen |
| **多媒体** | 语音 | 语音转文字 | openai-whisper |
| **多媒体** | GIF | GIF搜索 | gifgrep |
| **实用** | 天气 | 天气预报 | weather |
| **实用** | 总结 | URL/文件总结 | summarize |
| **实用** | 笔记 | Obsidian/Markdown | obsidian/qmd |
| **实用** | PDF | PDF编辑 | nano-pdf |
| **实用** | 审查 | 安全扫描 | skill-vetter |
| **管理** | 任务 | 任务跟踪 | Task系统 |
| **管理** | 自动化 | 定时任务 | automation系统 |
| **管理** | 记忆 | 三层记忆 | 内置 |
| **管理** | 知识库 | 自我学习 | knowledge_base/ |
| **管理** | 画像 | 用户画像构建 | user-profile.md |
| **云服务** | 腾讯文档 | 在线文档 | tencent-docs MCP |

### 🔴 关键缺失（必须补齐）

| 能力域 | 缺什么 | 为什么重要 | 获取途径 |
|--------|--------|-----------|----------|
| **桌面控制** | 屏幕点击/键盘输入/窗口操作 | 用户不动手的核心——操作任何桌面软件 | 安装 MCPControl 或 win32-mcp-server |
| **邮件** | 收发邮件 | 发送报告/提醒/通知 | 安装邮件MCP或SMTP脚本 |
| **剪贴板** | 读写剪贴板 | 与用户桌面交互最直接的方式 | PowerShell `Get-Clipboard`/`Set-Clipboard` |
| **文件监听** | 目录变化监控 | 用户放了文件自动处理 | PowerShell FileSystemWatcher 或 fs-watch |

### 🟡 可增强（锦上添花）

| 能力域 | 可增强项 | 获取途径 |
|--------|----------|----------|
| **搜索** | 多引擎并发搜索 | multi-search-engine skill |
| **通知** | 系统通知推送 | PowerShell Toast通知 |
| **日程** | 日历管理 | 需日历MCP或Connector |
| **存储** | 云盘操作 | 百度网盘/微云 Connector |
| **即时通讯** | 微信/企微/飞书 | 需对应Connector或MCP |

### ❌ 不可实现（告知用户）

| 能力域 | 原因 |
|--------|------|
| 支付/转账 | 安全红线，不可自动化 |
| 修改系统核心配置 | 安全风险 |
| 绕过用户认证 | 安全红线 |

---

## 二、全自主工作流模板

### 一句话示例

```
用户："帮我查竞品A的最新融资动态，做成Word报告放桌面，顺便把关键信息截图发我"
```

### 自动执行链

```
Step 0 周通环境探测（静默）
  → 检查：agent-browser ✅ / docx ✅ / 桌面路径 ✅
  
Step 1 朱之文判复杂度 → 中度，激活：药水哥拆解 + 孙笑川工具 + 郭老师输出
  
Step 2 药水哥MECE拆解 → ①查融资信息 ②截图关键页 ③生成Word ④保存桌面
  
Step 3 孙笑川工具链 → agent-browser → WebFetch → docx → 桌面路径
  
Step 4 info-猎手执行
  → 范小勤：WebSearch "竞品A 融资 2026" 
  → 抓到5条信息，可信度标记：[高]2条 [中]2条 [低]1条
  
Step 5 content-匠人执行
  → 郭老师："耶斯莫拉～收到信息了集美！"
  → 整合成Word报告（宋体12pt/黑体标题）
  
Step 6 马保国审查
  → "我大意了啊……这条信息来源不够硬"
  → 退回标记[低]的信息，重写
  
Step 7 郭老师修改 → 只用[高][中]信息，重出Word
  
Step 8 马保国:"耗子尾汁。过。"
  
Step 9 蔡徐坤安全扫描 → "内容安全，可以发。你真棒。"
  
Step 10 王境泽："桌面路径OK，我帮你存好了……真香。"
  
Step 11 虎哥静默监控 → 记录全程 → "嗷……正常。"（只有朱之文能听到）
  
Step 12 朱之文交付："搞完了。报告在桌面，叫《竞品A融资动态报告-20260603.docx》。核心发现：他们上周刚融了B轮，3个亿。"
```

---

## 三、自我进化机制

### PDCA循环（每次任务后自动执行）

```
Plan   → 朱之文/药水哥：分析任务，选最优工具链
Do     → 业务组：执行
Check  → 马保国/虎哥：审查+监控
Act    → 孙笑川：沉淀知识库 → 下次更快
```

### 知识库成长路径

```
首次任务 → 空知识库，全量执行
第10次   → toolchain.md有5条记录，匹配历史方案
第50次   → 90%任务命中已有工具链，秒级响应
第100次  → 用户画像完善，预判意图，一句话都不用说完
```

### info-猎手定时冲浪（核心）

范小勤每3天自动执行：

```
1. WebSearch 用户所在领域最新动态（从user-profile.md读取）
2. WebSearch 新出工具/skill/mcp（从SkillHub搜索）
3. 更新 knowledge_base/trending.md
4. 向朱之文汇报："最近有XX新工具、YY新动态"
5. 如果有高价值新工具 → 转孙笑川安装
```

---

## 四、依赖环境清单

### 运行时依赖

| 依赖 | 版本 | 用途 | 安装方式 |
|------|------|------|----------|
| Node.js | ≥22.0 | JS运行时 | 已安装(managed) |
| Python | ≥3.12 | 数据处理/脚本 | 已安装(managed) |
| Git Bash | - | Shell命令 | 已安装(系统) |

### 推荐安装的Skill/MCP（按需）

| 名称 | 来源 | 用途 | 优先级 |
|------|------|------|--------|
| multi-search-engine | SkillHub | 多引擎并发搜索 | 🟡中 |
| proactive-agent | SkillHub | 主动预判增强 | 🟡中 |
| self-improving | SkillHub | 自我改进增强 | 🟢低 |
| MCPControl | MCP市场 | 桌面自动化 | 🔴高 |
| win32-mcp-server | GitHub | Windows GUI控制 | 🔴高 |

### 禁止安装项

- 任何写入C盘的工具
- 任何需要root/管理员权限的（除非用户明确授权）
- 任何来源不明的二进制文件（必须通过skill-vetter审查）
