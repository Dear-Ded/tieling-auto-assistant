# 铁岭AI总管 · Tieling Butler

> **说一句就行。** 12个AI角色团队协作，3套风格自由切换。从系统清理到竞品分析，从代码开发到内容创作——你说一句，全员待命。

[![Version](https://img.shields.io/badge/version-1.0.0--beta.1-blue)](https://github.com/Dear-Ded/tieling-auto-assistant)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-WorkBuddy%20%7C%20OpenClaw%20%7C%20CodeBuddy%20%7C%20Marvis-orange)]()

---

## 一句话介绍

**说一句话，全自动搞定一切。** 系统管理、内容创作、信息研究、代码开发、文件处理——12个AI角色组成的团队，自学习、自改进。3套可切换风格。不需要你动手，不需要你追问。

> *"帮我查一下竞品A最新融资动态，写成Word报告放桌面"*  
> → 10秒后报告已在桌面。

---

## 特性

| 特性 | 说明 |
|------|------|
| 🤖 **一句话全自动** | 轻/中/重三档智能路由，轻任务秒回，重任务全队上阵 |
| 👥 **12角色团队** | 总经理+管理层6人+业务组6人，各司其职 |
| 🎭 **3套风格** | 全网抽象合集 / 赛博朋克风 / 体制内风格，风格不影响功能 |
| 🧠 **自我进化** | PDCA循环+知识库+错误日志，越用越聪明 |
| 🌊 **定时冲浪** | 信息组每3天自动搜索最新工具和领域动态 |
| 📊 **用户画像** | 持续学习用户偏好，预判意图，主动关怀 |
| 🛡️ **安全第一** | 全链路审查+幽灵监控+C盘禁区 |
| 🌍 **全平台** | WorkBuddy / OpenClaw / CodeBuddy / Marvis 通用 |

---

## 快速开始

```bash
# 安装
npx skills add Dear-Ded/tieling-auto-assistant
```

安装后，技能会自动触发。说一句就行：

```
"帮我清理C盘"
"查一下特斯拉最新股价"
"写一篇关于AI趋势的公众号文章"
"帮我写个Python脚本爬这个网站的数据"
"生成一份Q2业绩分析PPT"
```

---

## 风格切换

```
"切换到赛博朋克风"
"换成体制内风格"
"用抽象风"
```

| 风格 | 描述 | 角色示例 |
|------|------|----------|
| 🎭 **全网抽象合集**（默认） | 12位真实网络人物，满嘴梗 | 朱之文·总经理、孙笑川·技术、giao哥·代码 |
| 🌃 **赛博朋克风** | 霓虹暗黑/信息战/后人类 | 识别码+权限层级，终端即战场 |
| 📋 **体制内风格** | 公文/人事档案/严谨规范 | 职务+职责+请示报告制度 |

---

## 架构

```
用户一句话
    ↓
朱之文(总经理)：判复杂度 → 路由分档
    ↓
药水哥(业务副总)：MECE拆解任务
    ↓
孙笑川(技术总监)：工具链发现(6步法)
    ↓
业务组并行执行：
  ├─ 郭老师(content-匠人)：内容创作
  ├─ 范小勤(info-猎手)：信息搜集
  ├─ giao哥(code-技师)：代码实现
  ├─ 王境泽(sys-管家)：系统运维
  ├─ 蔡徐坤(safety-哨兵)：安全审查
  └─ 刀哥(data-keeper)：数据保管
    ↓
马保国(审查)：全链路审计 → 通过/打回
    ↓
交付 → 虎哥(监控)静默记录 → 刀哥归档
    ↓
PDCA自进化：知识库更新 → 下次更快
```

---

## 文件结构

```
tieling-auto-assistant/
├── SKILL.md                     # 技能定义（入口）
├── README.md                    # 你正在看
├── references/
│   ├── characters.md            # 角色完整功能能力
│   ├── characters-abstract.md   # 全网抽象合集人设
│   ├── characters-cyberpunk.md  # 赛博朋克人设
│   ├── characters-institutional.md # 体制内人设
│   ├── capabilities.md          # 全能力审计+依赖清单
│   ├── formatting-guide.md      # 排版规范
│   ├── interfaces.md            # 接口参考
│   ├── automation.md            # 自动化工具清单
│   └── user-profile.md          # 用户画像
└── knowledge_base/
    ├── error_log.md             # 错误日志 → 吃一堑长一智
    ├── toolchain.md             # 工具链组合 → 下次更快
    ├── trending.md              # 信息冲浪日志 → 始终保鲜
    ├── monitor_log.md           # 监控日志 → 仅总经理可见
    └── dep_tree.md              # 依赖关系图
```

---

## 兼容性

| 平台 | 状态 |
|------|------|
| WorkBuddy | ✅ 完全支持 |
| OpenClaw | ✅ 完全支持 |
| CodeBuddy | ✅ 完全支持 |
| Marvis | ✅ 完全支持 |
| 其他 Claw 兼容 | ✅ 通用 |

| 模型 | 状态 |
|------|------|
| Claude (Anthropic) | ✅ |
| GPT (OpenAI) | ✅ |
| Gemini (Google) | ✅ |
| Qwen (阿里) | ✅ |
| DeepSeek | ✅ |
| GLM (智谱) | ✅ |
| Hunyuan (腾讯) | ✅ |
| MiniMax | ✅ |
| Kimi (月之暗面) | ✅ |

---

## 依赖

无需额外安装。技能自动使用平台内置能力。如果需要桌面GUI自动化等高级能力，技能会在运行时自动提示安装对应MCP。

---

## 贡献

欢迎 PR。所有贡献请先用 skill-vetter 做安全扫描。

---

## 许可

MIT License © [Dear-Ded](https://github.com/Dear-Ded)

---

> *"爹"不是占便宜，是态度。你叫我爹，我给你的东西就得配得上这个称呼。*  
> *说一句话，剩下的交给我们。*
