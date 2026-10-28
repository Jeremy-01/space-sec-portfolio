# FAUXY Lady — 从 BPSK 录音重建卫星遥测包

> 📍 [作品集首页](../../README.md) › [阶段 A](../README.md) › **FAUXY Lady writeup**

> ✅ **本文状态**:全链路实做完成(2026-10-29),解题各节已填实。
> 「AI 运用」节含 4 条真实 AI 出错记录——这些记录本身是一份独立成立的产出。

- **来源**:Hack-A-Sat 4 (2023) 资格赛 · 记分板名 `FAUXY Lady` · 内部名 `satsig`
- **题类**:信号→帧→遥测链路(DSP)
- **难度**:★★★☆☆ (官方标注 3/5)
- **标签**:`#dsp` `#bpsk` `#differential-encoding` `#ccsds-asm` `#ax25-like` `#crc16-xmodem`
- **本地路径**:`~/E/code/ctf/hackasat/hackasat-qualifier-2023/challenges/2_Cant_Stop_The_Signal_Mal/2_Fauxy_Lady`

## 题目描述

> 某大学需要帮助收集他们立方星的遥测。已捕获一段卫星信号的 `.wav` 录音,该校也公开了遥测定义。信号特征:**BPSK 调制、差分编码、44.1k 采样率**。能重建出遥测包吗?

*(摘自官方 `README.md`,原题分类 DSP)*

素材:`static/tlm_def.pdf`(官方遥测定义)、`make generator` 产出的 `out/signal.wav`。

## 背景知识

面向不熟悉空间链路的读者,这题涉及三层嵌套——**这三层的辨识本身就是解题的一半**。

### 1. CCSDS 同步字(ASM)

空间遥测下行是**连续比特流**,没有以太网那样的帧间隙。接收端靠一个约定的固定图样找帧头,这就是 CCSDS 的 Attached Sync Marker:

```
1a cf fc 1d
```

这 32 bit 是 CCSDS TM 传输帧标准前导。它被选中不是随意的——其自相关特性好,在噪声中误同步概率低。**看到 `1acffc1d` 基本可以断定面对的是 CCSDS 体系的遥测流。**

### 2. 帧结构(读 `generator/packets.py` 源码得出,非推测)

```
[1a cf fc 1d][len:2][len:2][ 7e │ 14B 呼号 │ 03 │ F0 │ 80B 载荷 │ CRC:2 │ 7e ]
 └─ ASM 同步字  └─ 长度写两遍   └────────────── 内层帧 ──────────────────┘
                  (= 内层帧长)     CRC 覆盖:呼号+control+PID+载荷(不含 flag)
```

- **长度字段写两遍**:冗余设计,便于接收端交叉校验。两份不一致即说明比特流有误码
- **`0x7e` 起止 flag**、**`0x03`/`0xF0`** control/PID、**CRC-16**:这套组合是 AX.25(业余无线电链路层)的标志性特征

### 3. ⚠️ 「像 AX.25 但不是 AX.25」

这是本题最容易踩的坑,也是我自己踩过的(见「AI 运用」的出错记录):

| | 真 AX.25 | 本题 |
|---|---|---|
| 呼号编码 | 每字节**左移 1 位**,SSID 在第 7 字节 | **明文 ASCII**(`1AB-CDE` + `2FGHI-1`) |
| 帧界定 | `0x7e` flag + 比特填充(bit stuffing) | `0x7e` flag,无比特填充 |
| CRC | CRC-16/X.25(反转) | **CRC-16/XMODEM**(poly 0x1021, init 0x0000) |

结论:**M0 解 CUBEBEL-2 用的 `kiss_parse.py` 在这题上会输出乱码**——它的 `decode_callsign()` 会对明文 ASCII 再做一次右移。这题需要专门的解析器,即本仓库的 [`tools/asm_deframe.py`](../../tools/asm_deframe.py)。

### 与 M0 的对照(阶段 A ↔ 阶段 B 互相强化)

| 环节 | [M0:CUBEBEL-2](../../phase-b-rf/decodes/obs_14593136_record.md) | 本题 |
|---|---|---|
| 信号来源 | SatNOGS 真实存档观测 | 题目生成的合成录音 |
| 调制 | 9k6 FSK(gr-satellites 内建) | BPSK + 差分编码(需自己搭流图) |
| 帧同步 | KISS `0xC0` 分隔符 | CCSDS ASM `1acffc1d` |
| 内层帧 | 真 AX.25(呼号左移 1 位) | AX.25 风格(呼号明文) |
| 字段解析 | ❌ 无公开遥测格式表([M0 坑 8](../../phase-b-rf/M0-pitfalls.md)) | ✅ 官方给 `tlm_def.pdf` |

> M0 卡在"拿到帧却没有格式表,解不出字段级含义"。本题官方直接给格式表——正好补上 M0 没做成的那一步。

## 侦察与分析

**第一手观察**(2026-10-29 实做记录):

- **WAV 头**:44100 Hz、双声道、float32。GNU Radio 的 `wavfile_sink` 写 IEEE float WAV(format tag 3),Python 自带 `wave` 模块只认 PCM(`wave.Error: unknown format: 3`,见 pitfalls 坑 3),必须用 `scipy.io.wavfile`。
- **时长反推**:2.79 s ≈ 420 B × 8 bit ÷ 1200 baud,精确吻合——全程 1 bit/符号、无冗余编码,码元速率不用估,读流图源码即得。
- **频谱峰值 +398 Hz,不是 +1 kHz**:空闲段 `0xFF` 经差分编码变成 ±1 交替符号,等效 600 Hz 方波;载波 1 kHz 两侧各一条谱线,上边 1600 Hz 又被 generator 的 1.5 kHz 低通压掉,只剩 1000−600=400 Hz 这条。**谱峰 ≠ 载波**(pitfalls 坑 6)。
- **星座**:解调后空闲段为 1∠−5° / 1∠176° 完美交替——干净 BPSK;残余 −5° 相转来自信道 `taps=[1+1j]`(45°)与滤波群延迟,差分译码天然免疫。

**解调参数怎么定**:全部从 `generator/satsig.py` 流图源码读出,不猜——BPSK、差分、RRC α=0.35、1200 baud、44.1 kHz 下每符号 36.75 采样;重采样到 4800 Hz(4 sps)后扫相位/细偏移。

**同步字怎么发现**:不是猜的——`generator/packets.py` 源码明写 `a = b'\x1a\xcf\xfc\x1d'`。它同时是 CCSDS TM 标准前导,`tools/asm_deframe.py` 早已按它实现。

## 攻击思路

**差分编码为何必须先解差分再判决**:BPSK 相干解调有 π 相位歧义(载波环锁在 0 还是 π 无法区分),静态判决会把整串比特取反。差分编码把信息藏进**相邻符号的相位变化**(0→不变、1→翻转),接收端对相位差判决,歧义自动消失。实现上等价于 `b[n] = d[n] ⊕ d[n-1]`;对任意固定相转 θ,直接看相邻符号共轭乘积 `s[n]·conj(s[n-1])` 的**实部符号**(0/π 门限)即可——这是本次复现的关键(门限写错成角度正负会全错,见 pitfalls 坑 4)。

**双重冗余各自挡什么**:

- **长度字段写两遍**(`bc + bc`):挡解析器错位/单遍误读——两遍不一致即弃帧(本 solver 就靠它发现过切片错误);挡不住两遍一起错。
- **CRC-16/XMODEM**:挡随机误码(汉明距内必检出),**挡不住蓄意构造**——CRC 是检错码不是认证,知道生成多项式 `0x1021` 就能伪造合法帧。

**安全视角**:这套格式无认证、无加密,呼号明文、控制字 `0x03F0`、80 字节载荷任意填充。知道格式(公开遥测定义 + 一次下行采样即可获得)就能构造帧级合法的伪造遥测——对应真实系统「链路只做完整性、没做消息认证」的常见缺口,M5 安全分析沿此展开。

## 解题步骤

> 实做于 2026-10-29。全部命令可复现;本机无 docker,走「官方源码 + 本地 GNU Radio」等价路线(见 pitfalls 坑 2)。

### 0. 生成信号(等价 make generator)

`make generator` 依赖 docker,且 generator 的 `CMD` 引用 base 镜像里的 `/upload/upload.sh`(`COPY --from=has4/quals/generator-base/...`)。信号生成本身只依赖两条 python 命令——与容器无关:

```bash
cd ~/E/code/ctf/hackasat/hackasat-qualifier-2023/challenges/2_Cant_Stop_The_Signal_Mal/2_Fauxy_Lady/generator
export PATH=~/miniconda3/envs/grsat/bin:$PATH     # M0 装好的 GNU Radio 3.10 环境
FLAG='flag{FAKE_FLAG}' python3 packets.py         # → tx_stream (420 B)
python3 satsig.py                                 # → signal.wav (985 KB, 2.79 s)
cp signal.wav ../out/
```

### 1. 解调 → 切帧 → 解析(自研 solver,一条命令)

```bash
cd ../out
python3 ~/E/code/space-sec-portfolio/phase-a-software/solutions/2023-fauxy-lady/solve_fauxy.py signal.wav
```

六步流水线(numpy/scipy 实现,无 GNU Radio 依赖):

| 步骤 | 实现 | 要点 |
|---|---|---|
| ① 读 wav | `scipy.io.wavfile` | float32 双声道 I/Q;`wave` 模块读不了(坑 3) |
| ② 频偏校正 | `exp(-j2π·1k·t)` | generator 的 `rotator_cc` 加了 +1 kHz;Welch 谱峰 398 Hz 是空闲谱线不是载波(坑 6) |
| ③ RRC 匹配滤波 | α=0.35,8 符号窗 | 参数读自 `satsig.py` |
| ④ 重采样 | 44.1k→4.8k(resample_poly 16/147) | 1200 baud × 4 sps |
| ⑤ 符号定时 | 4 相位 × 7 细偏移扫描 | 差分能量/眼高选优;高信噪比下 phase0 即最优 |
| ⑥ 差分译码 | `Re{s[n]·conj(s[n-1])} < 0` | 0/π 门限,对残余相转免疫(坑 4) |

随后比特流搜 ASM → 双长度一致性校验(第二遍当校验用,坑 5) → 切内层帧 → CRC-16/XMODEM → 呼号/控制字/遥测字段。

**真实输出**:

```text
[1] wav: 2ch float32 44100Hz, 123157 帧 (2.79s)
[2] 频谱峰值 +398.4 Hz → 校正 -1 kHz (generator rotator_cc +1kHz)
[3] 重采样 44100 → 4800.0 Hz (4 sps), 13405 样点
[4] 定时: phase=0 fine=0.0, 眼高 1.7174, 3352 符号
[5] ASM 命中 (位反转=0), 切出 1 帧
[6] 内层帧:
  帧0: CRC PASS | 呼号 '1AB-CDE2FGHI-1' | 控制 0x03F0
        遥测载荷: flag{FAKE_FLAG}
```

解题脚本:[solutions/2023-fauxy-lady/solve_fauxy.py](../solutions/2023-fauxy-lady/solve_fauxy.py)。

## Flag

`flag{FAKE_FLAG}`——本机生成信号时用 Makefile 默认值注入。重建正确性不依赖 flag 内容:CRC-16/XMODEM PASS + 呼号 `1AB-CDE2FGHI-1` 与 `packets.py` 源码逐字节一致。赛场上同一链路重建即得真实 flag。

## AI 运用

> 本节按 [ai-workflow.md](../../docs/ai-workflow.md) 的记录规范三条逐项对应。

### 工具与角色

**副驾(Copilot)**——Claude Opus 4.8,用于:

- 制定 [M1 操作手册](../M1-playbook.md)(环境、选题、构建、解析全流程)
- 清点 Hack-A-Sat 两届共 55 道题的分类与难度,产出 [challenge-inventory.md](../challenge-inventory.md)
- 编写三个纯标准库解析工具:[`asm_deframe.py`](../../tools/asm_deframe.py)、[`ccsds_parse.py`](../../tools/ccsds_parse.py)、[`kiss_parse.py`](../../tools/kiss_parse.py)
- 阅读英文素材走**本地翻译链路**(沉浸式翻译 → Ollama → Hy-MT2-1.8B,离线运行、数据不出本机;配置见 ai-workflow.md 工具层)

**AI-as-subject** ⏳:计划不变——让 LLM 依据 hexdump 推断 `tlm_def.pdf` 之外的字段边界,再用程序验证(方法见 [M1 手册 §6](../M1-playbook.md))。解调链路已实做,重建帧的 hexdump 素材已具备,实验排下一轮。

### 人工验证

| 结论 | 验证方式 | 状态 |
|---|---|---|
| 帧结构(ASM + 双长度 + 内层帧布局) | 直接读 `generator/packets.py` 源码,非猜测 | ✅ **已验证** |
| CRC 算法 = CRC-16/XMODEM | `asm_deframe.py` 的实现与题目自带 `generator/crc.py` **逐向量比对一致**;并核对 XMODEM 标准校验值 `"123456789"` → `0x31c3` | ✅ **已验证** |
| 呼号是明文 ASCII 而非 AX.25 编码 | 源码 `struct.pack('>14s', (src+dst).encode())` 直接拼字符串,无位移 | ✅ **已验证** |
| `asm_deframe.py` 能抓出误码 | 合成测试:单 bit 翻转被 CRC 捕获;截断帧同时触发长度与 flag 两条告警 | ✅ **已验证** |
| 本题**不依赖** base 镜像 | 初判 `grep '^FROM'` 两个都是 `ubuntu:22.04`;实做时发现 `generator/Dockerfile` 还有 `COPY --from=has4/quals/generator-base/...`(见错误 4) | ❌ **已证伪**(build 引用 base;但信号生成本身不需要容器) |
| base 镜像构建流程 | 实测执行 `base_challenge/build.sh` → **失败**(EOL `ubuntu:focal` + 废弃包 `python-dev` + arm64 源 502)。结论:对本题非必需,已从必经路径移除 | ❌ **已证伪** |
| `make generator` 信号生成 | 本机无 docker;直接跑 `make_challenge.sh` 内两条源码命令(grsat 环境 `packets.py`→`satsig.py`),产出 `signal.wav` 985 KB/2.79 s,时长反推比特数精确吻合 | ✅ **已验证**(等价路线,pitfalls 坑 2) |
| 解调参数(sps=4、RRC α=0.35、1200 baud、+1 kHz 频偏) | 全部读自 `satsig.py` 流图源码;自研 numpy solver 一帧命中 ASM、CRC PASS、载荷完整重建 | ✅ **已验证** |

### AI 出错记录

> ai-workflow.md 称这类记录是"最能体现研究者判断力的素材"。以下两条都是真实发生、且被证据推翻的。

#### 错误 1:凭领域常识断言"存在 CCSDS 协议题类"

**AI 的主张**:M1 应主攻 Hack-A-Sat 的「CCSDS 协议解析」题类,并可用关键词 grep 定位相关题目。据此写出了初版手册的选题章节。

**为何看似合理**:CCSDS 确实是空间数据链路的主流标准族,而 Hack-A-Sat 是以空间系统为主题的 CTF——"这类赛事应该有 CCSDS 题类"是领域常识层面的合理外推。手册甚至给出了具体的 grep 命令。

**如何暴露**:实地 clone 仓库后按手册的方法执行,结果不对劲——

```bash
$ grep -ril "ccsds\|apid\|space packet" hackasat-qualifier-2023/challenges
challenges/5_Van_Halen_Radiation_Belt/1_Meet_Me_At_Midway/code/data/HGWellFirstMenOnTheMoon.txt
challenges/5_Van_Halen_Radiation_Belt/1_Meet_Me_At_Midway/code/data/HGWellFirstMenOnTheMoon_orig.txt
```

只有 2 处命中,且文件名可疑。逐一核查命中上下文:

```bash
$ grep -io ".\{8\}apid.\{8\}" .../HGWellFirstMenOnTheMoon.txt | head -3
ved me rapidly. I un
unning rapidly toget
thened rapidly, leng
```

命中的是 **H.G. Wells《月球上的第一批人》小说正文**里的 "ra**pid**ly" —— `apid` 作为子串被匹配。全部 7 次命中均为此类误报,**零个真实命中**。

**真实情况**:逐一读完两届 55 道题的 README 后确认——

- 2023 的分类是 The Kitchen / Aerocapture the Flag / Can't Stop the Signal, Mal / Pure Pwnage / Anomaly Review Bored / Van Halen Radiation Belt / The Magician
- 2022 的分类是 The Danger Room / Crypto / I Can Haz Satellite / Revenge of the Space Math / Rocinante Strikes Back / The Only Good Bug is a Dead Bug / We Get Signal
- **没有任何一届有以 CCSDS 命名的题类**。真正含 CCSDS 元素的仅本题一道(靠全库搜同步字 `1acffc1d` 找到,这才是有效的定位方法)

#### 错误 2:又断言"内层是 AX.25,可复用 M0 的工具"

纠正错误 1 后,AI 接着主张:本题内层帧是 AX.25,可套用 M0 写的 `kiss_parse.py` 解析呼号。

**如何暴露**:在编写 `asm_deframe.py` 时读 `generator/packets.py`,看到呼号构造是——

```python
src = "1AB-CDE"; dst = "2FGHI-1"
x2 = struct.pack('>14s', (src+dst).encode('utf-8'))   # 明文拼接，无位移
```

而真 AX.25 的呼号每字节要**左移 1 位**。`kiss_parse.py` 的 `decode_callsign()` 会对每字节右移 1 位,用在这里只会得到乱码。**表层特征相似(都有 `0x7e` flag 和 CRC)掩盖了编码层的实质差异。**

**处置**:立即改正三处文档表述(手册开篇、§5.0 层次表、§2.2 对照表),并在 `tools/README.md` 增加"三个帧解析工具怎么选"对照表,防止再次混用。

#### 错误 3:把"部分题目需要"的前置步骤写成了必做

**AI 的主张**:M1 手册 §3.1 写"部分题目容器依赖预建的基础镜像",并把 `base_challenge/build.sh` 放在构建流程第一步。

**如何暴露**:照做后构建失败——

```
E: Failed to fetch .../python3-minimal_3.8.2-0ubuntu2_arm64.deb  502 Bad Gateway
ERROR: ... exit code: 100
```

排查时才去查 Dockerfile 的 `FROM`,发现**本题两个容器都是 `ubuntu:22.04`,根本不依赖任何 base 镜像**。M1 题单四道题里只有拉伸题 Dishy 需要。这一步从头到尾是多余的。

**双重问题**:
1. "部分题目依赖"这个措辞没给出**判断自己属不属于那部分**的方法,读者只能当必做
2. 那个 base 镜像本身也建不起来:`FROM ubuntu:focal`(已 EOL)+ 安装列表含 `python-dev`(Python 2 的包,focal 里已废弃)——502 只是触发器,结构性隐患是 2023 年赛题用着 2020 年的基础设施

**处置**:§3.1 改为**默认跳过**并附依赖速查表与自查命令 `grep -h '^FROM' */Dockerfile`;§3 开头加"最短路径"提示;新建 [M1-pitfalls.md](../M1-pitfalls.md) 记录完整诊断链。

#### 错误 4:用 `grep '^FROM'` 验证"不依赖 base 镜像",漏掉了 COPY --from

**AI 的主张**:上一轮实做时,用 `grep -h '^FROM' */Dockerfile` 验证"本题两个容器都是 ubuntu:22.04,不依赖任何 base 镜像",并把结论写进上方人工验证表。

**如何暴露**:实做生成信号、通读 `generator/Dockerfile` 时,第二行就是——

```dockerfile
COPY --from=has4/quals/generator-base/generator-base:latest /upload/ /upload
```

base 镜像确实被引用——不在 FROM 里,而在 **COPY --from**(构建期从外部镜像拷文件)。`make build` 仍会因拉不到 `generator-base` 而失败,"不依赖 base"这个结论在 build 层面是错的。

**根因**:`grep '^FROM'` 只回答了"基础层来自哪里",没覆盖"构建期还要从哪些镜像取文件"。**验证方法的覆盖面必须与结论的覆盖面一致**——要证"不依赖 X",得搜 X 在 Dockerfile 里的全部引用形态(FROM / COPY --from / RUN docker pull),而不是挑一种搜法就签字。

**处置**:人工验证表修正(见上);"不依赖"改为精确表述"信号生成本身不需要容器";等价生成路线沉淀为 [pitfalls 坑 2](../M1-pitfalls.md)。

#### 教训

1. **领域常识可以生成假设,不能替代对目标数据的直接检视**。四个错误同源:都是从"这类系统通常如何"推出"这个系统就是如何",跳过了读源码/查 Dockerfile 这一步。
2. **grep 子串命中必须人工核查上下文**。`apid` 匹配到 "rapidly" 这种误报,只看文件名列表是发现不了的;若当时直接照着"命中列表"选题,会一路错下去。
3. **表层特征相似 ≠ 同一协议**。`0x7e` + CRC 让人立刻联想到 AX.25,但编码细节才决定工具能否复用。判断协议归属要看**构造代码或规范**,不是看图样。
4. **写"部分情况需要 X"时必须同时给出判断方法**。否则读者只能全做一遍,包括那些注定失败又毫无用处的步骤(错误 3)。
5. **报错要读到根因层**。`502 Bad Gateway` 看着像重试就能好的网络问题,实际背后是 EOL 镜像 + 废弃包——只重试永远不会成功。
6. 有价值的副作用:错误 1 的纠正促成主攻方向从"纯 CCSDS"调整为"信号→帧→遥测链路"——反而更契合作品集主线,因为它与阶段 B 的真实卫星接收直接呼应。
7. **验证方法的覆盖面必须与结论的覆盖面一致**(错误 4)。另外排障时 `sys.exit("消息")` 走 stderr,bash 管道只看 stdout 会误判成"静默失败、退出码 0"——本次为此多耗两轮。

## 复盘

**学到的知识点**

1. **差分编码的相位歧义**:π 歧义是 BPSK 相干解调的固有属性,差分编码是工程标准解;接收端按 0/π 门限判相邻符号相位差,比"先估载波相位再判决"稳健得多。
2. **同步字的自相关特性**:`1acffc1d` 自相关旁瓣低,才能在 100–200 字节的空闲噪声样式中一帧命中、零误同步。
3. **CRC 与长度冗余的互补**:长度双写挡"解析器错位",CRC 挡"随机误码";两者都挡不住蓄意构造——**完整性 ≠ 认证**。
4. **频谱峰 ≠ 载波**:调制样式自带谱线(空闲交替符号 = baud/2 方波),盲频偏估计前要先排除(本次 +398 Hz 那条)。

**真实系统中的对应**:小卫星下行普遍仍是「CCSDS TM 帧或其简化 + 无认证」;业余卫星遥测甚至公开格式表鼓励接收。防御者视角:任何有定向天线的人都能持续重建全量遥测——若其中含姿态、电源、载荷状态等运行数据,等于把运行状态持续广播。

**防御视角**:加认证首选在**遥测源端**对载荷做 AEAD(AES-GCM),帧结构不用动;链路层方案(帧尾扩认证域)要求收发共享密钥。对公开广播的遥测,"认证"与"可公开接收"存在结构性张力——这正是 M5 安全分析要正面回答的问题。

本次实做新踩 5 个坑,全部沉淀在 [M1-pitfalls.md](../M1-pitfalls.md) 坑 2–6。
