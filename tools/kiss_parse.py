#!/usr/bin/env python3
"""kiss_parse.py — 把 gr-satellites 输出的 .kiss 文件拆成帧并解析。

用途（M0 及以后）：
  gr_satellites 用 --kiss_out 存下的文件是 KISS 封装的原始帧。本脚本做三件事：
    1. KISS 解帧（处理 FEND 分隔与字节转义）
    2. 若帧是 AX.25（多数业余卫星如此），解出收/发呼号、SSID、控制/PID
    3. 打印 payload 的 hexdump + 可打印 ASCII

字段级遥测（电压/温度等）是**每颗卫星各异**的，需要该星的遥测格式表，
本脚本只做到通用的“帧 → AX.25 头 + payload”这一层；再往里的解析在
拿到具体卫星格式后另写（或直接用 gr-satellites 自带的 telemetry parser）。

用法：
  python3 tools/kiss_parse.py phase-b-rf/decodes/obs_12345.kiss
  python3 tools/kiss_parse.py obs.kiss --no-ax25      # 不尝试 AX.25，只 hexdump
  python3 tools/kiss_parse.py obs.kiss --raw-only      # 只打印每帧的原始 hex

仅依赖 Python 3 标准库，无需 pip install。
"""

import argparse
import sys

FEND = 0xC0   # 帧分隔符
FESC = 0xDB   # 转义符
TFEND = 0xDC  # 转义后的 FEND
TFESC = 0xDD  # 转义后的 FESC


def kiss_deframe(data: bytes):
    """把 KISS 字节流拆成帧列表，处理字节转义。返回去掉命令字节后的帧。"""
    frames = []
    for chunk in data.split(bytes([FEND])):
        if not chunk:
            continue
        # 反转义
        out = bytearray()
        i = 0
        while i < len(chunk):
            b = chunk[i]
            if b == FESC and i + 1 < len(chunk):
                nxt = chunk[i + 1]
                out.append(FEND if nxt == TFEND else FESC if nxt == TFESC else nxt)
                i += 2
            else:
                out.append(b)
                i += 1
        if len(out) < 1:
            continue
        # 首字节是 KISS 命令/端口字节（数据帧通常为 0x00），丢弃
        frames.append(bytes(out[1:]))
    return [f for f in frames if f]


def decode_callsign(field: bytes):
    """AX.25 地址字段：7 字节，前 6 字节呼号（每字节左移 1 位），第 7 字节含 SSID。"""
    call = "".join(chr(b >> 1) for b in field[:6]).strip()
    ssid = (field[6] >> 1) & 0x0F
    return f"{call}-{ssid}" if ssid else call


def parse_ax25(frame: bytes):
    """尝试把帧当 AX.25 解。返回 (dest, src, control, pid, info) 或 None。"""
    if len(frame) < 16:  # 至少两个地址(14)+控制(1)+PID(1)
        return None
    try:
        dest = decode_callsign(frame[0:7])
        src = decode_callsign(frame[7:14])
        control = frame[14]
        pid = frame[15]
        info = frame[16:]
        # 简单合理性校验：呼号应为可见字符
        if not all(32 <= ord(c) < 127 for c in (dest + src).replace("-", "")):
            return None
        return dest, src, control, pid, info
    except (IndexError, ValueError):
        return None


def hexdump(data: bytes, indent: str = "  "):
    lines = []
    for off in range(0, len(data), 16):
        chunk = data[off:off + 16]
        hexpart = " ".join(f"{b:02x}" for b in chunk)
        asciipart = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        lines.append(f"{indent}{off:04x}  {hexpart:<47}  {asciipart}")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description="解析 gr-satellites 的 .kiss 帧文件")
    ap.add_argument("kissfile", help="gr_satellites --kiss_out 生成的 .kiss 文件")
    ap.add_argument("--no-ax25", action="store_true", help="不尝试 AX.25 头解析")
    ap.add_argument("--raw-only", action="store_true", help="每帧只打印原始 hex，不做 hexdump/AX.25")
    args = ap.parse_args()

    try:
        with open(args.kissfile, "rb") as f:
            data = f.read()
    except OSError as e:
        sys.exit(f"读取失败: {e}")

    frames = kiss_deframe(data)
    if not frames:
        sys.exit("未解出任何帧（文件可能为空或不是 KISS 格式）")

    print(f"# {args.kissfile}")
    print(f"# 共 {len(frames)} 帧\n")

    for idx, frame in enumerate(frames, 1):
        print(f"=== 帧 {idx} / {len(frames)}  ({len(frame)} 字节) ===")
        if args.raw_only:
            print(frame.hex())
            print()
            continue

        payload = frame
        if not args.no_ax25:
            ax = parse_ax25(frame)
            if ax:
                dest, src, control, pid, info = ax
                print(f"  AX.25: {src} > {dest}  control=0x{control:02x} pid=0x{pid:02x}")
                payload = info
            else:
                print("  (非 AX.25 或无法解析，按原始 payload 处理)")

        print(hexdump(payload))
        print()


if __name__ == "__main__":
    main()
