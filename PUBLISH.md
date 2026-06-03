# 发布指南 · PUBLISH.md

## 发布清单

### 1. GitHub 仓库

```bash
# 创建仓库
gh repo create Dear-Ded/tieling-auto-assistant --public --description "铁岭AI总管 - 一句话全自动个人助理"

# 推送文件
cd path/to/skill
git init
git add .
git commit -m "v1.0.0-beta.1: 铁岭AI总管 全自动个人助理首发"
git remote add origin https://github.com/Dear-Ded/tieling-auto-assistant.git
git push -u origin main
```

### 2. SkillHub (lightmake.site)

访问 https://lightmake.site，注册/登录后：
- 点击"上传技能"
- 上传 SKILL.md 作为主文件
- 勾选"包含 references 目录"
- 勾选"包含 knowledge_base 目录"

### 3. WorkBuddy 技能市场

已内置在 WorkBuddy 中，无需额外操作。SkillHub 注册后 WorkBuddy 可自动发现。

### 4. OpenClaw / CodeBuddy / Marvis

基于 Claw 兼容标准，SkillHub 注册后这些平台自动可见。各自平台可能需要：
- OpenClaw: `npx skills add Dear-Ded/tieling-auto-assistant`
- CodeBuddy: 在技能市场中搜索"铁岭AI总管"

### 5. 豆包 (Doubao)

豆包目前不支持自定义 skill 上传。替代方案：
- 将 SKILL.md 内容作为"角色扮演"prompt 粘贴到豆包对话中
- 或等待豆包开放 skill 市场

---

## 发布后验证

- [ ] GitHub repo 可访问: https://github.com/Dear-Ded/tieling-auto-assistant
- [ ] SkillHub 可搜索: 搜索"铁岭AI总管"或"tieling-auto-assistant"
- [ ] `npx skills add Dear-Ded/tieling-auto-assistant` 可安装
- [ ] README.md 渲染正常
- [ ] 中英文标签都生效
