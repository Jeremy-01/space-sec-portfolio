# Hack-A-Sat 往届题目清点

> 📍 [作品集首页](../README.md) › [阶段 A](README.md) › **题目清点**

> 实地清点于 2026-07-26，基于本地 clone 的仓库：`~/E/code/ctf/hackasat/`
> 数据来源：各仓库根 README 的官方映射表 + 每题 `README.md` 的 Category/Difficulty 字段。
> 用途：M1 选题决策依据（见 [M1-playbook.md](M1-playbook.md) §2），免得重复清点。

## ⚠️ 一个被证伪的假设（重要）

最初的 M1 计划假设"Hack-A-Sat 有独立的 CCSDS 协议题类"。**实地清点证明这个假设是错的**：

- `grep -ril "ccsds\|apid\|space packet"` 在 2023 仓库只命中 2 个文件，**全是误报**——H.G. Wells 小说文本里的 "ra**pid**ly"
- 2022 仓库命中 `fda_approved_beef`，但那是 NASA **F-Prime** 框架的利用题，不是 CCSDS 解析题
- **两届都没有以 CCSDS 命名的题类**

真正含 CCSDS 元素的题**只有一道**：2023 的 **FAUXY Lady**（详见下方）。M1 因此把主攻方向调整为**「信号→帧→遥测」链路**。

> 这条记录本身是 [ai-workflow.md](../docs/ai-workflow.md) 要求的"AI 出错记录"——AI 基于领域常识做的合理推断，被实地数据推翻。写进 writeup 时可直接引用。

---

## 🎯 M1 目标题目（信号→帧→遥测链路）

| 内部路径 | 记分板名 | 类别 | 难度 | 为什么选 |
|---|---|---|---|---|
| `2023/challenges/2_Cant_Stop_The_Signal_Mal/2_Fauxy_Lady` | **FAUXY Lady** | DSP | 3/5 | ⭐**核心题**，见下方详解 |
| `2023/challenges/2_Cant_Stop_The_Signal_Mal/0_QAM` | QAM | DSP | 1/5 | 热身：QAM 符号解调 |
| `2023/challenges/2_Cant_Stop_The_Signal_Mal/1_Dashing` | Dashing | DSP | 1/5 | 热身：摩尔斯解码 |
| `2022/doppler` | Doppler | RF | 4/5 | 进阶：带多普勒与路径效应的下行解码 |
| `2023/challenges/2_Cant_Stop_The_Signal_Mal/3_Dark_Side_of_the_Dishy` | Dark Side of the Dishy | DSP | 5/5 | 拉伸目标 |

### FAUXY Lady 详解（为什么它是核心题）

**题面**：某大学的立方星遥测需要接收。给一段 `.wav` 录音 + 官方发布的遥测定义，要求重建遥测包。信号特征：BPSK 调制、差分编码、44.1k 采样率。

**帧结构**（读 `generator/packets.py` 确认）：

```
[1a cf fc 1d] [len][len] [ 7e | 14字节收发呼号 | 03 | F0 | 80字节载荷 | CRC16 | 7e ]
 ^^^^^^^^^^^            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
 CCSDS TM Transfer      内层是 AX.25 风格帧——与 M0 解 CUBEBEL-2 时同源
 Frame 同步字(ASM)
```

**与 M0 的衔接**：
- `1a cf fc 1d` 是 CCSDS TM 传输帧的标准同步字（Attached Sync Marker）
- 内层 `0x7e` flag + 呼号 + `0x03`/`0xF0`（control/PID）+ CRC 的结构，正是你在 M0 用 [`tools/kiss_parse.py`](../tools/kiss_parse.py) 解过的 AX.25 帧格式
- BPSK 解调可复用 M0 装好的 GNU Radio（官方 solver 就是个 `.grc` 流图）

**素材**：`static/tlm_def.pdf`（官方遥测定义）、`static/tlm_def.zip`、`solver/solver.grc`（GNU Radio 参考解流图）

---

## 2023 全量清单（Hack-A-Sat 4，28 题）

路径前缀：`~/E/code/ctf/hackasat/hackasat-qualifier-2023/challenges/`

| 类别 | 记分板名 | 内部路径 | 难度 |
|---|---|---|---|
| The Kitchen | The Freezer | `0_The_Kitchen/0_The_Freezer` | — |
| The Kitchen | The Microwave | `0_The_Kitchen/1_The_Microwave` | — |
| The Kitchen | The Stove | `0_The_Kitchen/2_The_Stove` | 0/5 |
| The Kitchen | A Sink | `0_The_Kitchen/` | — |
| Aerocapture the Flag | GGs | `1_Aerocapture_The_Flag/0_GGs` | 3/5 |
| Aerocapture the Flag | Find Your Center | `1_Aerocapture_The_Flag/1_Find_Your_Center` | — |
| Aerocapture the Flag | Terraforming Mars | `1_Aerocapture_The_Flag/2_Teraforming_Mars` | 4/5 |
| Aerocapture the Flag | TLE | `1_Aerocapture_The_Flag/3_TLE` | 5/5 |
| **Can't Stop the Signal, Mal** | **QAM** | `2_Cant_Stop_The_Signal_Mal/0_QAM` | 1/5 |
| **Can't Stop the Signal, Mal** | **Dashing** | `2_Cant_Stop_The_Signal_Mal/1_Dashing` | 1/5 |
| **Can't Stop the Signal, Mal** | **FAUXY Lady** ⭐ | `2_Cant_Stop_The_Signal_Mal/2_Fauxy_Lady` | 3/5 |
| **Can't Stop the Signal, Mal** | **Dark Side of the Dishy** | `2_Cant_Stop_The_Signal_Mal/3_Dark_Side_of_the_Dishy` | 5/5 |
| Pure Pwnage | RISC-V Smash Baby | `3_Pure_Pwnage/0_RISC-V-Smash-Baby` | 1/5 |
| Pure Pwnage | Warning | `3_Pure_Pwnage/1_Warning` | 1/5 |
| Pure Pwnage | dROP Baby | `3_Pure_Pwnage/2_dROP_Baby` | 2/5 |
| Pure Pwnage | Magic Space Bussin | `3_Pure_Pwnage/3_Magic_Space_Bussin` | 3/5 |
| Pure Pwnage | Spectrel Imaging | `3_Pure_Pwnage/4_Spectrel_Imaging` | 5/5 |
| Pure Pwnage | Kalman At Me Bro | `3_Pure_Pwnage/5_Kalman_At_Me_Bro` | — |
| Anomaly Review Bored | Contact | `4_Anomoly_Review_Bored/0_Contact` | 2/5 |
| Anomaly Review Bored | You've Been Promoted! | `4_Anomoly_Review_Bored/1_Youve_Been_Promoted` | 2/5 |
| Van Halen Radiation Belt | Based Emoji | `5_Van_Halen_Radiation_Belt/0_Based_Emoji` | 1/5 |
| Van Halen Radiation Belt | Meet Me at Midway | `5_Van_Halen_Radiation_Belt/1_Meet_Me_At_Midway` | 2/5 |
| Van Halen Radiation Belt | Signals from Trisolaris | `5_Van_Halen_Radiation_Belt/2_Signals_From_Trisolaris` | 4/5 |
| Van Halen Radiation Belt | Quantum | `5_Van_Halen_Radiation_Belt/3_Quantum` | 4/5 |
| The Magician | As Below | `6_The_Magician/0_As_Below` | 2/5 |
| The Magician | Leavenworth Street | `6_The_Magician/1_Leavenworth_Street` | 3/5 |
| The Magician | Hyde Street | `6_The_Magician/2_Hyde_Street` | 4/5 |
| The Magician | So Above | `6_The_Magician/3_So_Above` | 5/5 |

**额外资源**：`team_writeups/`（20 支队伍的官方 writeup，含 Solar Wine、PPP、mhackeroni、DiceGang 等）、`tickets.csv`（ticket→seed 解码环）

---

## 2022 全量清单（Hack-A-Sat 3，27 题）

路径前缀：`~/E/code/ctf/hackasat/hackasat-qualifier-2022/`

| 类别 | 记分板名 | 内部名 | 难度 |
|---|---|---|---|
| The Danger Room | Juggernaut | `basic_file` | 入门 |
| The Danger Room | Magneto | `basic_service` | 入门 |
| The Danger Room | Prof. X | `basic_handoff` | 3/3 |
| Crypto | Black Hole | `black_hole` | 2/5 |
| Crypto | Leggo My Steggo! | `leggo_my_stego` | — |
| Crypto | Screaming Fist | `screaming_fist` | — |
| Crypto | Welcome to the Spiderverse | `spiderverse` | 4/5 |
| I Can Haz Satellite | F'DA Approved Beef | `fda_approved_beef` | — |
| I Can Haz Satellite | Fun in the Sun | `sunfun` | 2/5 |
| I Can Haz Satellite | Red Alert | `red_alert` | 3/5 |
| Revenge of the Space Math | (Don't) Fly Me to the Moon | `fly_me_to_the_moon` | 4/5 |
| Revenge of the Space Math | Crosslinks | `crosslinks` (crosslinks1) | — |
| Revenge of the Space Math | Matters of State | `matters_of_state` | 1/5 |
| Revenge of the Space Math | Navigation Rebooting | `crosslinks` (crosslinks2) | — |
| Rocinante Strikes Back | Once Unop a Djikstar | `dijkstar` | — |
| Rocinante Strikes Back | Stars Above | `starsabove` | — |
| Rocinante Strikes Back | The Authenticator Equivalence Principle | `authentication_equivalence_principle` | 4/5 |
| Rocinante Strikes Back | The Wrath of Khan | `khan` | 4/5 |
| The Only Good Bug is a Dead Bug | Bit Flipper | `bitflipper` | 3/5 |
| The Only Good Bug is a Dead Bug | Blazin' Etudes | `blazing_etudes` | 4/5 |
| The Only Good Bug is a Dead Bug | It's A Wrap | `its_a_wrap` | 0/5 |
| The Only Good Bug is a Dead Bug | Ominous Etude | `ominous_etude` | 1/5 |
| The Only Good Bug is a Dead Bug | Small Hashes Anyways | `small_hashes_anyways` | — |
| **We Get Signal** | **Doppler** | `doppler` | 4/5 |
| We Get Signal | Power Level | `power_level` | 1/5 |
| We Get Signal | Power Point | `power_point` | 4/5 |
| （未在映射表） | Space Jam | `space_jam` | 5/5 |

> 注：`generator-base`、`microblaze-user-toolchain` 是构建基础设施，非题目。

---

## 后续题类候选（M2 用）

M2 要"覆盖 2–3 个题类"。按与空间安全主线的相关度排序：

1. **Pure Pwnage**（2023，6 题，1/5→5/5 梯度完整）—— 星上软件二进制利用，对应 phase-a README 的"cFS/星务逻辑"
2. **Satellite Ops / I Can Haz Satellite** —— 卫星运控逻辑（姿态、功率、动量管理），偏业务逻辑攻击
3. **Space Math / Aerocapture** —— 轨道力学，对应 phase-a README 第 4 类
