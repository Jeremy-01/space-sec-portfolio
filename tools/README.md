# tools/

> 📍 [作品集首页](../README.md) › **自研工具**

自研脚本与小工具存放处。

随着阶段推进，这里会放：
- SatNOGS 数据下载/批处理脚本
- 遥测帧解析辅助脚本
- 安全分析用的取证/对比脚本

## 现有脚本
| 脚本 | 用途 | 用法 |
|---|---|---|
| [`kiss_parse.py`](kiss_parse.py) | 把 gr-satellites `--kiss_out` 的 .kiss 文件拆帧 + 解 AX.25 头 + hexdump payload（纯标准库） | `python3 tools/kiss_parse.py phase-b-rf/decodes/obs_<号>.kiss` |
| [`ccsds_parse.py`](ccsds_parse.py) | 按 CCSDS Space Packet 主包头切分二进制流，解 APID/类型/序列/长度 + hexdump（纯标准库） | `python3 tools/ccsds_parse.py dump.bin [--hex] [--apid N]` |
| [`asm_deframe.py`](asm_deframe.py) | 按 CCSDS 同步字（ASM `1acffc1d`）切帧 + 解明文呼号内层帧 + CRC-16/XMODEM 校验（纯标准库） | `python3 tools/asm_deframe.py signal.bin [--ascii-only]` |

## 三个帧解析工具怎么选

它们解的是**不同层**，用错了只会得到乱码：

| 数据特征 | 用哪个 | 典型场景 |
|---|---|---|
| KISS 封装，呼号是 AX.25 编码（每字节左移 1 位） | `kiss_parse.py` | gr-satellites `--kiss_out`（M0 真实卫星） |
| 有 6 字节主包头（APID / 序列计数 / 长度） | `ccsds_parse.py` | cFS、真实任务遥测转储 |
| 有同步字 `1a cf fc 1d`，呼号是明文 ASCII | `asm_deframe.py` | Hack-A-Sat FAUXY Lady（M1） |

**可选上坡道**：若某个脚本成熟到能填补 gr-satellites / SatNOGS 生态的缺口，考虑抽出来开源贡献（拉伸目标，见 [roadmap.md](../docs/roadmap.md)）。
