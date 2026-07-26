#!/usr/bin/env python3
"""asm_deframe.py — 按 CCSDS 同步字（ASM）切分比特流并解析内层帧。

用途（M1 及以后）：
  解调出的原始比特流通常是「同步字 + 长度 + 内层帧」反复拼接，帧间填充空闲字节。
  本脚本做四件事：
    1. 按同步字（默认 CCSDS ASM `1acffc1d`）切分传输帧
    2. 读双份长度字段并交叉校验
    3. 解析内层帧：起止 flag、收发呼号、control/PID、载荷、CRC
    4. 校验 CRC-16/XMODEM 并打印 hexdump + ASCII

默认帧格式（Hack-A-Sat 2023 "FAUXY Lady" 实测，见 phase-a-software/M1-playbook.md）：

    [1a cf fc 1d][len:2][len:2][ 7e | 14B 呼号 | 03 | F0 | 载荷 | CRC:2 | 7e ]
     ^^^^^^^^^^^  ^^^^^^^^^^^^  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
     CCSDS ASM    长度写两遍     内层帧（AX.25 风格，但呼号是明文 ASCII）
                  (= 内层帧长)   CRC 覆盖范围：呼号+control+PID+载荷（不含 flag）

  ⚠️ 注意与真 AX.25 的区别：本格式的呼号是**明文 ASCII**（如 `1AB-CDE2FGHI-1`），
     不是 AX.25 那种「每字节左移 1 位」的编码。所以 tools/kiss_parse.py 的
     decode_callsign() 用在这里会得到乱码——两者不能混用。

能力边界（与 tools/kiss_parse.py、tools/ccsds_parse.py 同构的定位）：
  本脚本只做到「切帧 + 内层帧头 + CRC 校验」这一层。载荷内部的遥测字段
  （电压、温度、时间等）布局**每个任务各异**，需要该任务的遥测定义表
  （FAUXY Lady 的在 static/tlm_def.pdf）。那一层请另行解析。

  另外三个工具的分工：
    - asm_deframe.py（本脚本）：同步字切帧 + 明文呼号内层帧
    - kiss_parse.py：KISS 封装 + 真 AX.25（呼号左移 1 位）
    - ccsds_parse.py：CCSDS Space Packet 主包头（APID/序列/长度）

用法：
  python3 tools/asm_deframe.py signal.bin
  python3 tools/asm_deframe.py stream.hex --hex           # 输入是 hex 文本
  python3 tools/asm_deframe.py signal.bin --raw-only      # 每帧只打印原始 hex
  python3 tools/asm_deframe.py signal.bin --no-inner      # 不解析内层，只切帧
  python3 tools/asm_deframe.py signal.bin --sync 1acffc1d # 自定义同步字
  python3 tools/asm_deframe.py signal.bin --ascii-only    # 只输出各帧载荷的可打印文本

仅依赖 Python 3 标准库，无需 pip install。
"""

import argparse
import sys

DEFAULT_SYNC = "1acffc1d"   # CCSDS Attached Sync Marker
FLAG = 0x7E                 # 内层帧起止标志
CALLSIGN_LEN = 14           # 收发呼号各 7 字节，明文 ASCII
CRC_LEN = 2


def crc16_xmodem(data: bytes) -> int:
    """CRC-16/XMODEM：poly=0x1021, init=0x0000, 不反转, xorout=0。"""
    crc = 0x0000
    for b in data:
        crc ^= b << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
    return crc


def split_by_sync(stream: bytes, sync: bytes):
    """按同步字切分。返回 (帧体列表, 首个同步字之前被丢弃的字节数)。"""
    frames = []
    first = stream.find(sync)
    if first == -1:
        return frames, len(stream)
    i = first
    while i != -1:
        j = stream.find(sync, i + len(sync))
        frames.append(stream[i + len(sync): j if j != -1 else len(stream)])
        i = j
    return frames, first


def parse_frame(body: bytes) -> dict:
    """解析同步字之后的帧体：双份长度 + 内层帧。"""
    out = {"errors": []}
    if len(body) < 4:
        out["errors"].append(f"帧体仅 {len(body)} 字节，不足两个长度字段")
        return out

    len_a = int.from_bytes(body[0:2], "big")
    len_b = int.from_bytes(body[2:4], "big")
    out["len_a"], out["len_b"] = len_a, len_b
    if len_a != len_b:
        out["errors"].append(f"两份长度字段不一致：{len_a} vs {len_b}")

    rest = body[4:]
    declared = len_a
    if declared > len(rest):
        out["errors"].append(f"声明长度 {declared} > 实际剩余 {len(rest)}（帧被截断）")
        inner = rest
    else:
        inner = rest[:declared]
        trailing = rest[declared:]
        # 帧后通常是空闲填充（0xFF）；非填充内容值得提示
        stripped = trailing.strip(b"\xff")
        if stripped:
            out["trailing_note"] = f"帧后有 {len(stripped)} 字节非 0xFF 数据"
    out["inner_raw"] = inner
    return out


def parse_inner(inner: bytes, out: dict):
    """解析内层帧：flag / 呼号 / control / PID / 载荷 / CRC。"""
    if len(inner) < 1 + CALLSIGN_LEN + 2 + CRC_LEN + 1:
        out["errors"].append(f"内层帧仅 {len(inner)} 字节，太短")
        return

    if inner[0] != FLAG:
        out["errors"].append(f"起始 flag 应为 0x7e，实为 0x{inner[0]:02x}")
    if inner[-1] != FLAG:
        out["errors"].append(f"结束 flag 应为 0x7e，实为 0x{inner[-1]:02x}")

    core = inner[1:-1]                       # 去掉首尾 flag
    calls = core[0:CALLSIGN_LEN]
    out["src"] = calls[0:7].decode("ascii", "replace").rstrip("\x00 ")
    out["dst"] = calls[7:14].decode("ascii", "replace").rstrip("\x00 ")
    out["control"] = core[CALLSIGN_LEN]
    out["pid"] = core[CALLSIGN_LEN + 1]
    out["payload"] = core[CALLSIGN_LEN + 2: -CRC_LEN]

    crc_rx = int.from_bytes(core[-CRC_LEN:], "big")
    crc_calc = crc16_xmodem(core[:-CRC_LEN])   # 覆盖呼号+control+PID+载荷
    out["crc_rx"], out["crc_calc"] = crc_rx, crc_calc
    out["crc_ok"] = crc_rx == crc_calc


def hexdump(data: bytes, indent: str = "  "):
    lines = []
    for off in range(0, len(data), 16):
        chunk = data[off:off + 16]
        hexpart = " ".join(f"{b:02x}" for b in chunk)
        asciipart = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        lines.append(f"{indent}{off:04x}  {hexpart:<47}  {asciipart}")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description="按 CCSDS 同步字切帧并解析内层帧")
    ap.add_argument("infile", help="比特流文件（或 hex 文本，配合 --hex）")
    ap.add_argument("--hex", action="store_true", help="输入是 hex 文本（忽略空白）")
    ap.add_argument("--sync", default=DEFAULT_SYNC, help=f"同步字 hex（默认 {DEFAULT_SYNC}）")
    ap.add_argument("--no-inner", action="store_true", help="不解析内层帧，只切帧")
    ap.add_argument("--raw-only", action="store_true", help="每帧只打印原始 hex")
    ap.add_argument("--ascii-only", action="store_true", help="只打印各帧载荷的可打印文本")
    args = ap.parse_args()

    try:
        sync = bytes.fromhex(args.sync)
    except ValueError:
        sys.exit(f"同步字不是合法 hex: {args.sync}")

    try:
        if args.hex:
            with open(args.infile, "r") as f:
                data = bytes.fromhex("".join(f.read().split()))
        else:
            with open(args.infile, "rb") as f:
                data = f.read()
    except OSError as e:
        sys.exit(f"读取失败: {e}")
    except ValueError as e:
        sys.exit(f"hex 解析失败: {e}")

    if not data:
        sys.exit("文件为空")

    frames, skipped = split_by_sync(data, sync)
    if not frames:
        sys.exit(f"未找到同步字 {args.sync}（检查解调是否正确、比特是否反相）")

    # --ascii-only：拼接所有载荷，方便直接看 flag
    if args.ascii_only:
        for body in frames:
            info = parse_frame(body)
            if "inner_raw" not in info:
                continue
            parse_inner(info["inner_raw"], info)
            pl = info.get("payload", b"")
            text = "".join(chr(b) for b in pl if 32 <= b < 127).rstrip()
            if text:
                print(text)
        return

    print(f"# {args.infile}")
    print(f"# 同步字 {args.sync}，共 {len(frames)} 帧")
    if skipped:
        print(f"# 首个同步字前跳过 {skipped} 字节（通常是空闲填充）")
    print()

    for idx, body in enumerate(frames, 1):
        info = parse_frame(body)
        print(f"=== 帧 {idx} / {len(frames)} ===")
        if "len_a" in info:
            same = "一致" if info["len_a"] == info["len_b"] else "⚠️ 不一致"
            print(f"  长度字段: {info['len_a']} / {info['len_b']} ({same})")

        inner = info.get("inner_raw", b"")
        if args.raw_only:
            print(f"  {inner.hex()}")
        elif args.no_inner:
            print(hexdump(inner))
        else:
            parse_inner(inner, info)
            if "src" in info:
                print(f"  呼号: {info['src']} > {info['dst']}   "
                      f"control=0x{info['control']:02x} pid=0x{info['pid']:02x}")
                mark = "✅" if info.get("crc_ok") else "❌"
                print(f"  CRC-16/XMODEM: 收到 0x{info['crc_rx']:04x} / "
                      f"计算 0x{info['crc_calc']:04x} {mark}")
                print(hexdump(info.get("payload", b"")))

        if info.get("trailing_note"):
            print(f"  ℹ️ {info['trailing_note']}")
        for e in info["errors"]:
            print(f"  ⚠️ {e}")
        print()


if __name__ == "__main__":
    main()
