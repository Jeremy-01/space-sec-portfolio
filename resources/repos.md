# 开源仓库索引

本作品集引用到的全部开源仓库，集中列此。均为已核实真实可用（截至 2026-07）。

| 仓库 | 用途 | 阶段 | 出现在文档 |
|---|---|---|---|
| [daniestevez/gr-satellites](https://github.com/daniestevez/gr-satellites) | GNU Radio 业余卫星遥测解码器合集 | B | setup.md, resources/README.md |
| [Xerbo/aptdec](https://github.com/Xerbo/aptdec) | NOAA APT 云图解码 | B | setup.md, resources/README.md |
| [baskiton/sats-receiver](https://github.com/baskiton/sats-receiver) | 一体化 GNU Radio 卫星接收 | B | setup.md, resources/README.md |
| [nasa/cFS](https://github.com/nasa/cFS) | NASA core Flight System 星务飞控框架 | A | setup.md, resources/README.md |
| [CCSDSPy/ccsdspy](https://github.com/CCSDSPy/ccsdspy) | CCSDS Space Packet 字段级解析库（NASA/NOAA 在用） | A | M1-playbook.md |
| [deptofdefense/hack-a-sat-library](https://github.com/deptofdefense/hack-a-sat-library) | 官方空间文档与教程合集 | A | M1-playbook.md |
| [solar-wine/writeups](https://github.com/solar-wine/writeups) | 强队 Hack-A-Sat 解法合集 | A | M1-playbook.md |

### Hack-A-Sat 往届开源题（阶段 A 主要题源，均已核实）
| 仓库 | 说明 |
|---|---|
| [hackasat-qualifier-2023](https://github.com/cromulencellc/hackasat-qualifier-2023) | HAS4 资格赛（推荐起步） |
| [hackasat-qualifier-2022](https://github.com/cromulencellc/hackasat-qualifier-2022) | HAS3 资格赛 |
| [hackasat-qualifier-2021](https://github.com/cromulencellc/hackasat-qualifier-2021) | HAS2 资格赛 |
| [hackasat-qualifier-2020](https://github.com/cromulencellc/hackasat-qualifier-2020) | 首届资格赛，含入门题类 Space Cadets |
| [hackasat-qualifier-2022-techpapers](https://github.com/cromulencellc/hackasat-qualifier-2022-techpapers) · [2021](https://github.com/cromulencellc/hackasat-qualifier-2021-techpapers) | 前十名队伍官方 writeup（卡死时的 kill-switch） |

> 每题自带 Docker 三件套（generator / challenge / solver）；目录按**内部名**命名，映射表在各仓库根 README。
> ⚠️ `ticket-taker` / `lifecycle-manager` / `sat-solver` 未开源，本地复现绕法见 [M1-playbook.md §3.3](../phase-a-software/M1-playbook.md)。

## 非 GitHub 的关键资源（含代码/数据平台）
| 资源 | 用途 | 链接 |
|---|---|---|
| SatNOGS | 开源地面站网络（代码托管在 GitLab） | https://satnogs.org/ · https://gitlab.com/librespacefoundation/satnogs |
| SatNOGS DB | 卫星/遥测数据库 | https://db.satnogs.org/ |
| SatNOGS Network | 存档观测数据 | https://network.satnogs.org/ |
| CCSDS 蓝皮书 | 空间协议标准 | https://public.ccsds.org/ |
