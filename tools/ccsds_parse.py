#!/usr/bin/env python3
"""ccsds_parse.py — 按 CCSDS Space Packet 主包头切分二进制流并解析。

用途（M1 及以后）：
  Hack-A-Sat 的协议题、以及真实任务的遥测转储，多为 CCSDS Space Packet 序列。
  本脚本做三件事：
    1. 按主包头（Primary Header，6 字节）逐包切分字节流
    2. 解出版本号、包类型（TM/TC）、次级头标志、APID、序列标志/计数、包长
    3. 打印每包用户数据区的 hexdump + 可打印 ASCII

主包头位域布局（CCSDS 133.0-B，6 字节 = 48 bit）：
    字节 0-1: [版本 3b][类型 1b][次级头标志 1b][APID 11b]
    字节 2-3: [序列标志 2b][序列计数 14b]
    字节 4-5: [包数据长度 16b]   ← 值 = 用户数据区字节数 - 1
  故整包长度 = 6 + (包数据长度 + 1)

能力边界（与 tools/kiss_parse.py 同构的定位）：
  本脚本只做**通用主包头**这一层。次级头与用户数据区的字段级布局
  （时间戳、遥测点、指令参数等）**每个任务/每个 APID 各异**，需要该任务的
  遥测字典。那一层请用 ccsdspy 定义 FixedLength/PacketArray 另行解析：

      import ccsdspy
      from ccsdspy import PacketField
      pkt = ccsdspy.FixedLength([
          PacketField(name='TIME',    data_type='uint', bit_length=32),
          PacketField(name='VOLTAGE', data_type='int',  bit_length=16),
      ])
      result = pkt.load('tlm.bin', include_primary_header=True)

用法：
  python3 tools/ccsds_parse.py dump.bin
  python3 tools/ccsds_parse.py dump.hex --hex          # 输入是 hex 文本
  python3 tools/ccsds_parse.py dump.bin --apid 100     # 只看某个 APID
  python3 tools/ccsds_parse.py dump.bin --raw-only     # 每包只打印原始 hex

仅依赖 Python 3 标准库，无需 pip install。
"""

import argparse
import sys

PRIMARY_HEADER_LEN = 6

SEQ_FLAGS = {
    0b00: "继续段",
    0b01: "首段",
    0b10: "末段",
    0b11: "独立包",
}


def parse_primary_header(hdr: bytes) -> dict:
    """解 6 字节主包头为字段字典。"""
    w0 = int.from_bytes(hdr[0:2], "big")
    w1 = int.from_bytes(hdr[2:4], "big")
    length_field = int.from_bytes(hdr[4:6], "big")
    return {
        "version": (w0 >> 13) & 0x07,
        "type": (w0 >> 12) & 0x01,       # 0=遥测(TM) 1=遥控(TC)
        "sec_hdr": (w0 >> 11) & 0x01,
        "apid": w0 & 0x07FF,
        "seq_flags": (w1 >> 14) & 0x03,
        "seq_count": w1 & 0x3FFF,
        "length_field": length_field,     # = 用户数据区长度 - 1
        "data_len": length_field + 1,
    }


def split_packets(data: bytes):
    """按主包头逐包切分。返回 (header_dict, payload) 列表。

    遇到长度越界（截断的尾包）时停止，并把剩余字节数报给调用方。
    """
    packets = []
    off = 0
    while off + PRIMARY_HEADER_LEN <= len(data):
        hdr = parse_primary_header(data[off:off + PRIMARY_HEADER_LEN])
        start = off + PRIMARY_HEADER_LEN
        end = start + hdr["data_len"]
        if end > len(data):
            # 尾部被截断：把能拿到的部分作为最后一包返回，并标记
            hdr["truncated"] = True
            packets.append((hdr, data[start:]))
            return packets, 0
        hdr["truncated"] = False
        packets.append((hdr, data[start:end]))
        off = end
    return packets, len(data) - off


def hexdump(data: bytes, indent: str = "  "):
    lines = []
    for off in range(0, len(data), 16):
        chunk = data[off:off + 16]
        hexpart = " ".join(f"{b:02x}" for b in chunk)
        asciipart = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        lines.append(f"{indent}{off:04x}  {hexpart:<47}  {asciipart}")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description="按 CCSDS Space Packet 主包头解析二进制流")
    ap.add_argument("infile", help="二进制转储文件（或 hex 文本，配合 --hex）")
    ap.add_argument("--hex", action="store_true", help="输入是 hex 文本（忽略空白与换行）")
    ap.add_argument("--apid", type=int, help="只显示该 APID 的包")
    ap.add_argument("--raw-only", action="store_true", help="每包只打印原始 hex，不做 hexdump")
    args = ap.parse_args()

    try:
        if args.hex:
            with open(args.infile, "r") as f:
                text = "".join(f.read().split())
            data = bytes.fromhex(text)
        else:
            with open(args.infile, "rb") as f:
                data = f.read()
    except OSError as e:
        sys.exit(f"读取失败: {e}")
    except ValueError as e:
        sys.exit(f"hex 解析失败: {e}")

    if not data:
        sys.exit("文件为空")

    packets, leftover = split_packets(data)
    if not packets:
        sys.exit(f"未解出任何包（数据不足 {PRIMARY_HEADER_LEN} 字节主包头）")

    shown = [p for p in packets if args.apid is None or p[0]["apid"] == args.apid]

    print(f"# {args.infile}")
    print(f"# 共 {len(packets)} 包" + (f"，APID={args.apid} 命中 {len(shown)} 包" if args.apid is not None else ""))
    if leftover:
        print(f"# ⚠️ 尾部剩余 {leftover} 字节不足一个主包头，已忽略")
    print()

    for idx, (hdr, payload) in enumerate(shown, 1):
        kind = "TC(遥控)" if hdr["type"] else "TM(遥测)"
        seq = SEQ_FLAGS.get(hdr["seq_flags"], "?")
        print(f"=== 包 {idx} / {len(shown)} ===")
        print(f"  APID={hdr['apid']} (0x{hdr['apid']:03x})  {kind}  "
              f"次级头={'有' if hdr['sec_hdr'] else '无'}  版本={hdr['version']}")
        print(f"  序列: {seq} #{hdr['seq_count']}   数据区 {hdr['data_len']} 字节"
              f"（长度字段={hdr['length_field']}）")
        if hdr["truncated"]:
            print(f"  ⚠️ 该包被截断：声明 {hdr['data_len']} 字节，实际只有 {len(payload)} 字节")

        if args.raw_only:
            print(f"  {payload.hex()}")
        else:
            print(hexdump(payload))
        print()


if __name__ == "__main__":
    main()
