# 阶段 B：RF/SDR 层

> 📍 [作品集首页](../README.md) › **阶段 B：RF/SDR 层**

**目标**：亲手接收并解码真实卫星信号，作为面试差异化。

## 里程碑
1. **M0 起步（无硬件）**：用 SatNOGS 存档 IQ/音频数据，跑通 gr-satellites 解出一条真实遥测 —— 📋 照做手册见 [M0-playbook.md](M0-playbook.md)
2. **M3 首次物理接收**：RTL-SDR + 天线，接收 NOAA APT 云图（最易上手）
3. **M4 差异化**：解码一颗业余立方星遥测

## 目录
- [`captures/`](captures/) — 原始 IQ / 音频采集（大文件走 .gitignore，仅存元数据与截图）
- [`decodes/`](decodes/) — 解出的云图 / 遥测数据 / 截图

## 每次接收要记录
- 卫星名 / NORAD ID / 频率 / 时间 / 地点
- 天线与设备配置
- 接收信噪比 / 波形截图
- 解码结果 + 与 SatNOGS 数据库的交叉校验
- 完整可复现步骤

## AI 运用（见 [ai-workflow.md](../docs/ai-workflow.md)）
- **副驾**：AI 辅助调 GNU Radio 流图、排查解码失败、解释调制原理。
- **AI-as-subject（本阶段差异化重头）**：用 ML 做**信号/调制分类**、从 IQ 数据做**遥测异常检测**——"AI×RF"最硬的卖点。
- 每次接收记录里注明 ML 模型/方法与验证情况。

## Kill-switch
若物理接收环境（城市遮挡、天线）始终失败 → 退回纯 SatNOGS 存档数据完成本阶段，仍是真实数据，AI/ML 分析不受影响。

## 进度
- [x] M0：SatNOGS 存档数据解出第一条遥测 ✅ 2026-07-25 — CUBEBEL-2（NORAD 57175）观测 #14593136，3 条 AX.25 遥测帧，与网络 Demoded Data 校验一致。[解码记录](decodes/obs_14593136_record.md) · [踩坑沉淀](M0-pitfalls.md)
- [ ] 首次物理接收 NOAA APT
- [ ] 立方星遥测解码
