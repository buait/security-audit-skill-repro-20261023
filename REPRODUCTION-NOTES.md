# REPRODUCTION-NOTES

本仓库是对上游开源项目的独立复刻与增强，遵循 MIT 许可证（见 [LICENSE](LICENSE)）。

## 原仓库信息

- 原仓库：https://github.com/cloudflare/security-audit-skill
- 复现日期：2026-10-23
- 原仓库简介：面向编码代理的安全审计技能。通过侦察、覆盖驱动的狩猎、候选验证、结构化输出、独立记录验证、目标中立报告六个阶段，把代码库安全审计做成可追溯、机器可读的流程。

## 复现方式说明

1. 使用浅克隆（`git clone --depth 1`）获取上游最新代码。
2. 断血缘：复制仓库内容到新目录，跳过原 `.git` 历史，重新 `git init`，使本仓库成为独立项目。
3. 完整保留原仓库 `LICENSE`（MIT）与全部原始文件，不删除、不改写上游内容。
4. 在此基础上新增增强工具与说明，详见下方"优化内容"。

## 优化内容

本次复刻在保留上游全部功能的基础上，新增了两个零依赖 Python 工具，作为 Node 版校验器的跨语言补充：

| 文件 | 作用 | 创新点 |
| --- | --- | --- |
| `skills/security-audit/validate_findings.py` | 用 Python 校验 `findings.json` 是否符合 `report-schema.json` | 实现 JSON-Schema 关键字子集（type / required / properties / enum / pattern / oneOf / const / visibleContent 等），退出码 0/1/2 可直接接入 CI，适用于无 Node 环境 |
| `skills/security-audit/summarize_findings.py` | 将 `findings.json` 渲染为可读 Markdown 摘要 | 按严重度排序 confirmed 表格、列出 needs_validation 阻塞项与 rejected 原因，便于人工快速审阅审计结果，支持 `-o` 输出文件 |

配套改动：

- `README.md`：新增 "Python companions" 小节，补充两个工具的用法与设计说明。
- 校验器在开发中修复了一处 oneOf 分支全部失败时错误被吞掉的问题，确保无效记录一定报错。

## 维护记录表

| 日期 | 版本 | 操作 | 说明 |
| --- | --- | --- | --- |
| 2026-10-23 | v1.0 | 初始复刻 | 浅克隆 cloudflare/security-audit-skill，断血缘后重新初始化；新增 Python 校验器与 Markdown 摘要工具；README 增补说明 |
