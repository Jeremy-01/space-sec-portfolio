# 环境搭建

> 📦 **本文含开源仓库地址**（下方以 `[repo]` 标注）。全部仓库集中索引见 [resources/repos.md](../resources/repos.md)。

## 软件层（阶段 A，无需硬件）

### 基础工具
- Python 3.11+
- Git
- Docker（部分 Hack-A-Sat 题目提供容器化环境）

### Hack-A-Sat 练习环境
往届题目与基础设施开源，可本地跑（📋 完整照做手册：[M1-playbook.md](../phase-a-software/M1-playbook.md)）：
- 官方站点：https://hackasat.com/
- 往届题目仓库 `[repo]`：[2023](https://github.com/cromulencellc/hackasat-qualifier-2023) · [2022](https://github.com/cromulencellc/hackasat-qualifier-2022) · [2021](https://github.com/cromulencellc/hackasat-qualifier-2021) · [2020](https://github.com/cromulencellc/hackasat-qualifier-2020)（全部索引见 [repos.md](../resources/repos.md)）
- cFS（NASA core Flight System）`[repo]`：https://github.com/nasa/cFS

### Python 工具链（阶段 A）
```bash
python3 -m venv ~/.venvs/hasat && source ~/.venvs/hasat/bin/activate
pip install ccsdspy pwntools scapy
```
- `ccsdspy` `[repo]` — CCSDS Space Packet 字段级解析：https://github.com/CCSDSPy/ccsdspy
- `pwntools` — CTF 交互与打包；`scapy` — 自定义协议层
- 本仓库自带 [`tools/ccsds_parse.py`](../tools/ccsds_parse.py) 做主包头快速 triage（纯标准库）

## RF/SDR 层（阶段 B）

### 硬件（约 ¥150–200）
- RTL-SDR 接收器（RTL-SDR Blog V4 推荐）
- 天线：NOAA APT 用 137MHz V 型偶极子或 QFH 天线（可 DIY）

### 软件工具链
```bash
# GNU Radio（macOS 用 Homebrew）
brew install gnuradio

# gr-satellites（业余卫星遥测解码器）[repo]
# ⚠️ 不要用 pip 装——它是 GNU Radio 的 C++ OOT 模块，PyPI 上没有（报 No matching distribution found）
# 用 conda-forge（M0 实测可行）：
conda install -c conda-forge gnuradio-satellites
# 或从源码编译：https://github.com/daniestevez/gr-satellites

# NOAA APT 云图解码 [repo]
# https://github.com/Xerbo/aptdec

# 一体化接收（可选）[repo]
# https://github.com/baskiton/sats-receiver
```

### 无硬件起步（M0 用这个）
不必等硬件到货——先用 [SatNOGS](https://satnogs.org/) 网络的真实存档观测数据：
- SatNOGS DB：https://db.satnogs.org/
- SatNOGS Network（存档观测）：https://network.satnogs.org/
- 下载某次观测的 IQ/音频数据，喂给 gr-satellites 解码

## 验证环境是否就绪
- [x] `gnuradio-companion` 能打开
- [x] `gr_satellites --help` 有输出
- [x] 能从 SatNOGS 下载一次观测数据并解出遥测

✅ 已于 2026-07-25 全部通过（M0 完成，见 [解码记录](../phase-b-rf/decodes/obs_14593136_record.md)）。踩坑记录见 [M0-pitfalls.md](../phase-b-rf/M0-pitfalls.md)。
