# 阶段 A：软件/协议层

> 📍 [作品集首页](../README.md) › **阶段 A：软件/协议层**

**目标**：通过 Hack-A-Sat 往届开源题，建立空间软件/协议安全能力，产出 CTF writeup 系列。

## 覆盖题类（按优先级）
1. **信号→帧→遥测链路** — 解调、帧同步（CCSDS 传输帧 / AX.25）、遥测字段解析 ← **M1 主攻**，📋 [M1-playbook.md](M1-playbook.md)
2. **cFS / 星务逻辑** — NASA core Flight System，星上应用漏洞
3. **比特翻转 / 遥测遥控** — TC/TM 帧构造与校验
4. **轨道力学题** — 用 skyfield/GMAT 解算轨道相关谜题

> 📋 往届题目完整清点（2022+2023，含内部名↔记分板名映射、类别、难度）见 [challenge-inventory.md](challenge-inventory.md)。
> ⚠️ 注意：Hack-A-Sat **没有**独立的"CCSDS 题类"——这是实地清点推翻的一个初始假设，详见 inventory 开头。

## AI 运用（见 [ai-workflow.md](../docs/ai-workflow.md)）
- **副驾**：AI 辅助逆向二进制、快速读懂 CCSDS/cFS 规范、解释陌生协议字段、起草 writeup。
- **AI-as-subject**：用 LLM/小模型做**协议帧自动解析与异常标注**，作为 writeup 的方法亮点。
- 每篇 writeup 记录 AI 用法，并标注 AI 结论是否经人工验证。

## 产出
- 每题一篇 writeup，放入 [`writeups/`](writeups/)，用 [模板](writeups/_TEMPLATE.md)
- 解题脚本放 `solutions/<题目名>/`，writeup 里链过去
- writeup 标准：让不看题的人也能读懂攻击原理；题目可本地复现

## 工具
- [`tools/ccsds_parse.py`](../tools/ccsds_parse.py) — CCSDS Space Packet 主包头切包 + hexdump（纯标准库）
- 字段级解析用 [ccsdspy](https://docs.ccsdspy.org/)，见 [M1 手册 §5](M1-playbook.md)

## 进度
- [x] 搭好本地练习环境（[M1 手册](M1-playbook.md) §0–1，比 [setup.md](../docs/setup.md) 更细）
- [x] 第一题类通关 + writeup（M1：信号→帧→遥测，主攻 2023 FAUXY Lady）✅ 2026-10-29
  - ✅ [writeup 已填实](writeups/2023-fauxy-lady.md)：generator 等价路线生成信号 → 自研 numpy solver（频偏校正/RRC/定时/差分译码）→ ASM 切帧 → CRC PASS，重建遥测载荷成功（「AI 运用」含 4 条 AI 出错记录）
  - ✅ 解题脚本：[solutions/2023-fauxy-lady/solve_fauxy.py](solutions/2023-fauxy-lady/solve_fauxy.py)
  - 🕳️ [M1 踩坑沉淀](M1-pitfalls.md)：累计 6 条真实坑（docker 等价路线、float WAV、0/π 判决、双长度解析、谱线≠载波等）
- [ ] 2–3 题类成系列
- [ ] 报名一场 CTF
