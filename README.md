# 空间网络安全作品集 (Space Cybersecurity Portfolio)

一个独立研究者的 **AI × 空间安全** 实战作品集，目标是产出可展示的求职敲门砖，覆盖 **软件/协议层** 与 **RF/SDR 信号层** 两侧。

**核心主线**：全流程用 AI 工具做安全研究，并把 AI/ML 做成产出本身（信号分类、遥测异常检测、AI 辅助威胁建模）。这是本作品集对外展示的差异化卖点——见 [AI 工作流](docs/ai-workflow.md)。

## 目标

- **底线目标**：构建可展示的个人作品集，作为空间/卫星网络安全相关岗位的敲门砖，凸显"AI×安全"复合能力。
- **拉伸目标**：若工具链有明显缺口，开源一个小工具贡献给社区（gr-satellites / SatNOGS 生态）。

## 三段式结构

| 阶段 | 侧重 | AI 运用 | 产出 | 目录 |
|---|---|---|---|---|
| A | 软件/协议（CTF、协议解析、固件） | AI 辅助逆向/读规范 + LLM 协议帧解析 | CTF writeup 系列 | [`phase-a-software/`](phase-a-software/) |
| B | RF/SDR（真实信号接收与解码） | ML 信号/调制分类 + 遥测异常检测 | 真实卫星信号接收记录 | [`phase-b-rf/`](phase-b-rf/) |
| C | 安全分析（缝合 A+B） | AI 辅助威胁建模 + 模式挖掘 | 结构化安全分析报告 | [`phase-c-analysis/`](phase-c-analysis/) |

## 文档

- [AI 工作流（差异化主线）](docs/ai-workflow.md) 🤖
- [路线图与里程碑](docs/roadmap.md)
- [环境搭建](docs/setup.md)
- [伦理与法律边界](docs/ethics-and-legal.md)
- [资源清单](resources/README.md)
- [开源仓库索引](resources/repos.md) 📦
- [自研工具](tools/README.md) 🔧

> 全部项目文档索引见 [docs/README.md](docs/README.md)。

## 伦理红线（先读）

全程**只被动接收、只分析、只在授权环境（CTF / 自有设备 / 仿真）里做攻击**。绝不向卫星发射、绝不干扰真实链路、绝不攻击未授权系统。详见 [ethics-and-legal.md](docs/ethics-and-legal.md)。

## 当前进度

- [x] M0 能力校准：装好工具链，用 SatNOGS 存档数据解出一条真实遥测 ✅ 2026-07-25（CUBEBEL-2，[解码记录](phase-b-rf/decodes/obs_14593136_record.md)）
- [ ] M1–M2 阶段 A：Hack-A-Sat writeup 系列
- [ ] M3–M4 阶段 B：物理接收真实卫星信号
- [ ] M5–M6 阶段 C：安全分析报告 + 作品集打磨
