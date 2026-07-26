# M0 解码记录 — SatNOGS 观测 #14593136（CUBEBEL-2）

> 📍 [作品集首页](../../README.md) › [阶段 B](../README.md) › **M0 解码记录**

> M0 交付物之一。操作依据：[M0-playbook.md](../M0-playbook.md)；踩坑详录：[M0-pitfalls.md](../M0-pitfalls.md)。

- **日期**：2026-07-24 ～ 2026-07-25
- **卫星名 / NORAD ID**：CUBEBEL-2 / 57175
- **SatNOGS 观测编号**：https://network.satnogs.org/observations/14593136/
- **频率 / 调制 / 采样率**：UHF 下行（准确值见观测页）/ **9k6 FSK** / 音频 48000 Hz（观测 JSON 中 `samp-rate-rx: 1.024e6` 为射频端 IQ 采样率，与音频解码无关，见坑 6）
- **输入文件类型**：音频 `.ogg` → 转 `.wav`
- **解码命令（完整）**：

```bash
# 仓库根目录执行
ffmpeg -i phase-b-rf/captures/obs_14593136.ogg -ar 48000 phase-b-rf/captures/obs_14593136.wav

gr_satellites 57175 \
  --wavfile phase-b-rf/captures/obs_14593136.wav \
  --samp_rate 48000 \
  --hexdump 2>&1 | tee phase-b-rf/decodes/obs_14593136_decode.txt

gr_satellites 57175 \
  --wavfile phase-b-rf/captures/obs_14593136.wav \
  --samp_rate 48000 \
  --kiss_out phase-b-rf/decodes/obs_14593136.kiss

python3 tools/kiss_parse.py phase-b-rf/decodes/obs_14593136.kiss \
  | tee phase-b-rf/decodes/obs_14593136_parsed.txt
```

- **解出帧数**：KISS 文件共 6 帧，其中 **3 条 216 字节 AX.25 遥测帧**（另 3 条为 8 字节短帧）
- **帧样例（首帧前 2 行 hex）**：

```
0000: 8a aa 62 b0 b0 40 60 8a aa 62 62 a6 40 61 03 f0
0010: 14 ba 88 00 00 c6 12 ab 00 00 00 00 00 47 49 05
```

  AX.25 解析：`EU11S > EU1XX`（源 → 目的呼号），control=0x03 pid=0xf0，payload 尾部含明文 **`CubeBel-2 Beacon TRX-Sec`**

- **交叉校验结论**：与 SatNOGS 观测页其他地面站解出的 Demoded Data **一致** ✅
- **遇到的坑与解决**（详见 [M0-pitfalls.md](../M0-pitfalls.md)，共 8 个）：
  1. `pip install gr-satellites` 装不上 → 它是 GNU Radio OOT 模块，改用 conda
  2. SatNOGS 网站改版，筛选项术语变了 → `Results → Good`
  3. 下载链接藏在 `Audio`/`Data` 选项卡里，要点击展开
  4. `$CAP` 相对路径变量在子目录执行时叠加失效 → 回根目录执行
  5. METEOR-M2-4 报 `Satellite not found`（新星未收录）→ 换 CUBEBEL-2
  6. 误用 IQ 采样率 1.024M 解音频 → 音频一律 48000
  7. `less` 分页器不会退 → 按 `q`
  8. CUBEBEL-2 无公开遥测格式表 → 字段级解析留给 FUNcube-1/JY1SAT
- **AI 用在哪**：全程副驾，四类角色——①**概念解释**（调制难度排序、AX.25/KISS 协议、RF vs 音频采样率）；②**故障诊断**（8 个坑的根因定位）；③**流程导航**（SatNOGS 页面操作指引、命令构建）；④**工程决策**（选 FSK 最简的 CUBEBEL-2、评估无格式表后果断跳过字段解析）。详见 [ai-workflow.md](../../docs/ai-workflow.md)。
  - **基础设施层——本地翻译**：阅读英文资料（SatNOGS 页面、gr-satellites 文档）时用完全本地的翻译链路：沉浸式翻译 / Cherry Studio → Ollama → **Hy-MT2-1.8B**（腾讯混元开源翻译模型，量化后 440MB~1.1GB，Metal GPU 加速，离线运行、数据不出本机）。配置见 [ai-workflow.md](../../docs/ai-workflow.md) 工具层小节。

## 环境

见 [env.md](env.md)：GNU Radio 3.10.12.0 / gr-satellites 5.9.0（conda 环境）/ Python 3.13.13 / macOS 26.5.2

## 产物清单

| 文件 | 说明 |
|---|---|
| [`obs_14593136_decode.txt`](obs_14593136_decode.txt) | gr_satellites hexdump 输出（3 条 PDU） |
| [`obs_14593136.kiss`](obs_14593136.kiss) | KISS 帧原始数据 |
| [`obs_14593136_parsed.txt`](obs_14593136_parsed.txt) | kiss_parse.py 结构化解析（AX.25 头 + payload） |
| [`obs_14593136_screenshot.png`](obs_14593136_screenshot.png) | 出帧截图 |
| `../captures/obs_14593136.{ogg,wav}` | 原始音频（本地保留，不入库） |
