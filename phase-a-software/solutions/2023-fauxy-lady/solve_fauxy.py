#!/usr/bin/env python3
"""
FAUXY Lady (Hack-A-Sat 4 2023) solver — 信号→帧→遥测 全链路复现
=============================================================
输入: 官方 generator 产出的 signal.wav (44.1k, 双声道 float32, I/Q)
输出: 重建的 CCSDS TM 帧 + 内层 AX.25-like 帧 + 遥测载荷 (flag)

链路 (对应 M1-playbook §4):
  1. 读 wav → 复数基带 (ch0=I, ch1=Q); GNU Radio 写的是 IEEE float wav,
     Python 自带 wave 模块只认 PCM, 必须用 scipy.io.wavfile
  2. 频偏盲检 + 校正 (generator 里 rotator_cc 加了 +1kHz)
  3. RRC 匹配滤波 (excess_bw=0.35, 对应 generic_mod 的 pulse shaping)
  4. 重采样到 4800 Hz (1200 baud × 4 sps)
  5. 符号定时: 多相位/细偏移中选差分能量最大者
  6. 差分译码 (differential=True 的逆): b[n] = d[n] XOR d[n-1]
  7. 比特流搜索 CCSDS ASM 1a cf fc 1d → 切传输帧
  8. 内层帧解析: 0x7e | 呼号14B | 03 F0 | 载荷80B | CRC16/XMODEM | 0x7e
"""
import sys, math
import numpy as np
from scipy import signal as sps_sig
from scipy.io import wavfile

WAV = sys.argv[1] if len(sys.argv) > 1 else "signal.wav"
BAUD = 1200.0

# ---------- 1. 读 wav ----------
sr, raw = wavfile.read(WAV)
raw = np.asarray(raw, dtype=np.float32)
iq = raw[:, 0] + 1j * raw[:, 1]
print(f"[1] wav: {raw.shape[1]}ch float32 {sr}Hz, {len(iq)} 帧 ({len(iq)/sr:.2f}s)")

# ---------- 2. 频偏盲检 + 校正 ----------
f, P = sps_sig.welch(iq, sr, nperseg=4096, return_onesided=False)
fc = f[np.argmax(P)]
print(f"[2] 频谱峰值 {fc:+.1f} Hz → 校正 -1 kHz (generator rotator_cc +1kHz)")
iq = iq * np.exp(-2j * math.pi * 1000.0 * np.arange(len(iq)) / sr)

# ---------- 3. RRC 匹配滤波 ----------
sps_f = sr / BAUD                      # 36.75 samples/symbol
k = 8
t = (np.arange(int(k * sps_f) + 1) - k * sps_f / 2) / sps_f
alpha = 0.35
rrc = np.sinc(t) * np.cos(math.pi * alpha * t) / (1 - (2 * alpha * t) ** 2)
rrc = rrc / np.sqrt(np.sum(rrc ** 2))
mf = sps_sig.lfilter(rrc, 1.0, iq)

# ---------- 4. 重采样到 4 sps ----------
target = BAUD * 4                       # 4800 Hz
g = math.gcd(int(sr), int(target))
y = sps_sig.resample_poly(mf, int(target // g), int(sr // g))
print(f"[3] 重采样 {sr} → {target} Hz (4 sps), {len(y)} 样点")

# ---------- 5. 符号定时: 4 相位 × 7 细偏移, 取差分能量最大 ----------
# ---------- 6+7. 对每个定时候选做相位差分译码并搜 ASM ----------
ASM = "00011010110011111111110000011101"  # 1a cf fc 1d
frames, hit = None, None
for phase in range(4):
    for fine in np.linspace(0, 1, 8)[:-1]:
        idx = (np.arange(phase, len(y), 4) + fine * 4).astype(int)
        idx = idx[idx < len(y)]
        sy = y[idx]
        u = sy[1:] * np.conj(sy[:-1])           # 相邻符号相位差
        # 差分译码按 0/π 判: 实部符号对任意固定相移免疫
        # (angle(u)>0 会把 ±180° 拆成两类, 星座带残余旋转时是错的)
        bits = (u.real < 0).astype(np.uint8)
        bitstr = "".join(map(str, bits))
        for inv in (0, 1):
            s2 = bitstr if not inv else "".join("01"[int(c)] for c in bitstr)
            pos, fr = 0, []
            while True:
                pp = s2.find(ASM, pos)
                if pp < 0: break
                # 帧布局: ASM(4B) + len(2B) + len(2B, 写两遍) + 内层帧(ln 字节)
                ln = int(s2[pp + 32:pp + 48], 2)
                if int(s2[pp + 48:pp + 64], 2) != ln:   # 第二遍长度校验
                    pos = pp + 1; continue
                payload = s2[pp + 64 : pp + 64 + ln * 8]
                if len(payload) == ln * 8:
                    fr.append(bytes(int(payload[i:i+8], 2) for i in range(0, ln * 8, 8)))
                pos = pp + 1
            if fr:
                frames, hit = fr, (phase, round(float(fine), 3), inv, len(idx), float(np.abs(sy).mean()))
                break
        if frames: break
    if frames: break
if frames is None:
    sys.exit("!! 全部定时候选均未找到 ASM")
ph, fine, inv, nsym, eye = hit
print(f"[4] 定时: phase={ph} fine={fine}, 眼高 {eye:.4f}, {nsym} 符号")
print(f"[5] ASM 命中 (位反转={inv}), 切出 {len(frames)} 帧")

# ---------- 8. 内层帧解析 ----------
def crc16_xmodem(data: bytes) -> int:
    crc = 0
    for b in data:
        crc ^= b << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
    return crc

print("[6] 内层帧:")
for i, fr in enumerate(frames):
    if fr[0] != 0x7E or fr[-1] != 0x7E:
        print(f"  帧{i}: 首尾非 0x7E, 跳过"); continue
    body = fr[1:-1]
    payload, crcrx = body[:-2], int.from_bytes(body[-2:], "big")
    ok = crc16_xmodem(payload) == crcrx
    call, ctl = payload[:14], payload[14:16]
    tele = payload[16:]
    flag = tele.rstrip(b"\x00").rstrip().decode("utf-8", "replace")
    print(f"  帧{i}: CRC {'PASS' if ok else 'FAIL'} | 呼号 {call.decode('utf-8','replace')!r} | 控制 0x{ctl.hex().upper()}")
    print(f"        遥测载荷: {flag}")