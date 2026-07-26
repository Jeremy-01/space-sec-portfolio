# 路线图与里程碑

保守估时，单兵可完成，每个里程碑都有独立可交付物，配 kill-switch。

**全程贯穿 AI**：每个里程碑既用 AI 做副驾加速，也逐步把 AI/ML 沉淀为产出本身。详见 [ai-workflow.md](ai-workflow.md)。

## M0（第 1–2 周）能力校准 ✅ 2026-07-25 完成
- 装好 GNU Radio + gr-satellites
- 用 [SatNOGS](https://satnogs.org/) 存档数据成功解出**一条**真实遥测
- **交付**：一份解码截图 + 步骤记录 → [解码记录](../phase-b-rf/decodes/obs_14593136_record.md)（CUBEBEL-2）· [踩坑沉淀](../phase-b-rf/M0-pitfalls.md)
- 📋 **带命令的操作手册**：[phase-b-rf/M0-playbook.md](../phase-b-rf/M0-playbook.md)
- **Kill-switch**：若两周内工具链装不通，先专注纯软件阶段 A，RF 推后 →（未触发：conda 路线一次装通）

## M1（第 1 个月）软件打底
- 刷通 Hack-A-Sat 往届至少**一个完整题类**（如 CCSDS 协议解析）
- **交付**：第一篇 writeup（`phase-a-software/writeups/`）
- 📋 **带命令的操作手册**：[phase-a-software/M1-playbook.md](../phase-a-software/M1-playbook.md)（主攻「信号→帧→遥测」链路，核心题 2023 FAUXY Lady）

## M2（第 2 个月）软件成体系
- 覆盖 2–3 个题类，writeup 成系列
- 报名一场 CTF（[Ctrl+Space](https://security4space.esa.int/2025/ctrl-space-ctf/) / Aerospace Village）
- **→ 产出 A 完成**

## M3（第 3 个月）RF 上手
- 买 RTL-SDR + DIY 天线，物理接收并解码第一颗真实卫星（NOAA APT 云图最易）
- **交付**：接收记录 + 解出的云图（`phase-b-rf/`）
- **Kill-switch**：若接收环境/天线始终失败，退回纯 SatNOGS 存档数据完成 B

## M4（第 4 个月）RF 差异化
- 解码一颗业余立方星遥测，整理接收链路文档（候选：FUNcube-1 / JY1SAT——遥测格式公开，可做字段级解析；M0 经验：避开无格式表的学生卫星，见[踩坑沉淀](../phase-b-rf/M0-pitfalls.md)坑 8）
- 训练一个 ML 信号/调制分类或遥测异常检测原型（AI×RF 差异化）
- **→ 产出 B 完成**

## M5（第 5 个月）安全分析
- 选定一类链路做安全属性分析（加密/认证/重放/GNSS 欺骗可行性边界，仅分析与仿真）
- 构建 AI 辅助威胁建模 / 遥测异常检测流程，收口成"AI×空间安全"主线
- **交付**：安全分析报告初稿（`phase-c-analysis/`）

## M6（第 6 个月）缝合与打磨
- 完成产出 C，整理 GitHub 作品集主页 + 简历条目
- 评估是否启动可选开源上坡道
- **→ 求职作品集成型**

## 可选上坡道（拉伸目标，非必需）
若阶段 B/C 工具链有明显缺口，开源一个小工具贡献给 gr-satellites / SatNOGS 生态。**仅在前三段稳了之后再碰。**
