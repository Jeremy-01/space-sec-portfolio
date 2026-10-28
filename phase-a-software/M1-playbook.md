# M1 操作手册：刷通「信号→帧→遥测」题类，产出第一篇 writeup

> 📍 [作品集首页](../README.md) › [阶段 A](README.md) › **M1 操作手册**

> 目标：用 Hack-A-Sat 往届开源题，刷通**信号→解调→帧→遥测**这条完整链路，产出第一篇 writeup。
> 交付：≥1 篇 writeup（`writeups/`）+ 可本地复现的解题脚本 + 环境记录。
> 平台：macOS。预计 2–4 周（M1 = 第 1 个月）。
>
> 📁 **路径约定**：下文命令均假设你已 `cd` 到仓库根目录（同 M0 的坑 4，相对路径在子目录会叠加失效）：
> ```bash
> cd ~/E/code/space-sec-portfolio
> ```
> 题目仓库在 `~/E/code/ctf/hackasat/`（已 clone 2022 + 2023）。
> 2023 届在本库内也有 submodule 副本（`challenges/hackasat-qualifier-2023`，`git submodule update --init` 拉取）；本手册命令沿用本地路径写法。

## ⚠️ 为什么不是"纯 CCSDS 题类"

本手册初版曾计划主攻"CCSDS 协议题类"。**实地清点两届仓库后该假设被证伪**：Hack-A-Sat 没有以 CCSDS 命名的题类，关键词 grep 命中的全是误报（小说文本里的 "ra**pid**ly"）。真正含 CCSDS 元素的题只有一道——2023 的 **FAUXY Lady**。

完整清点结论见 [challenge-inventory.md](challenge-inventory.md)。M1 因此调整为**「信号→帧→遥测」链路题类**，这样反而更好：

- **与 M0 直接衔接**：FAUXY Lady 的帧 = CCSDS 传输帧同步字 + 类 AX.25 内层，与你解 CUBEBEL-2 时拆过的结构同源（但呼号是明文，非 AX.25 位移编码）
- **复用已有工具**：BPSK 解调用 M0 装好的 GNU Radio；切帧解帧用本仓库的 [`tools/asm_deframe.py`](../tools/asm_deframe.py)
- **CCSDS 知识不浪费**：§4 的协议知识在 FAUXY Lady 的外层帧上直接用得上

> 📌 这个"假设被推翻"的过程本身是 writeup 素材——[ai-workflow.md](../docs/ai-workflow.md) 要求记录 AI 出错案例，这是一个现成的。

⚖️ **伦理边界**：本阶段的漏洞利用、帧构造、重放全部在**本地 Docker 容器**内进行，属 [ethics-and-legal.md](../docs/ethics-and-legal.md) 允许的"CTF / 自有设备 / 仿真"范围。不得把这些技术指向任何真实在轨系统。

---

## 0. 前置检查（10 分钟）

```bash
python3 --version          # 需 3.11+
git --version
docker info                # 需 Docker Desktop 已启动；报 Cannot connect 就先打开 App
```

Docker 没装：从 https://www.docker.com/products/docker-desktop/ 装，或 `brew install --cask docker`（装完需手动启动一次）。

---

## 1. 建环境（20 分钟）

与 M0 的 `grsat` 环境**隔离**，避免 GNU Radio 的依赖和 CTF 工具互相干扰：

```bash
python3 -m venv ~/.venvs/hasat
source ~/.venvs/hasat/bin/activate
pip install --upgrade pip
pip install ccsdspy pwntools scapy
```

各自的用途：

| 包 | 干什么 |
|---|---|
| `ccsdspy` | CCSDS Space Packet 字段级解析主力（NASA/NOAA 在用） |
| `pwntools` | CTF 标配：起 `remote()` 连题目端口、打包字节、交互 |
| `scapy` | 自定义协议层、构帧与嗅探 |

验证并记录环境（同 M0 的 env.md 套路）：

```bash
python3 -c "import ccsdspy, pwn, scapy; print('ok')"

#优化前
mkdir -p phase-a-software/writeups
{
  echo "## 阶段 A 环境版本 $(date '+%Y-%m-%d')"
  echo "- Python: $(python3 --version)"
  echo "- ccsdspy: $(python3 -c 'import ccsdspy; print(ccsdspy.__version__)' 2>/dev/null)"
  echo "- pwntools: $(python3 -c 'import pwn; print(pwn.__version__)' 2>/dev/null)"  ##有误，pwn 模块没有 __version__ 属性
  echo "- Docker: $(docker --version)"
  echo "- OS: $(sw_vers -productName) $(sw_vers -productVersion)"
} >> phase-a-software/env.md

#优化后
mkdir -p phase-a-software/writeups
{
  echo "## 阶段 A 环境版本 $(date '+%Y-%m-%d')"
  echo "- Python: $(python3 --version 2>/dev/null)"
  echo "- ccsdspy: $(python3 -c 'import ccsdspy; print(ccsdspy.__version__)' 2>/dev/null)"
  echo "- pwntools: $(pip show pwntools 2>/dev/null | grep '^Version:' | cut -d' ' -f2)"
  echo "- Docker: $(docker --version 2>/dev/null)"
  echo "- OS: $(sw_vers -productName) $(sw_vers -productVersion)"
} >> phase-a-software/env.md

cat phase-a-software/env.md
```

> 之后每次开工：`source ~/.venvs/hasat/bin/activate`

---

## 2. 选题（已清点完毕，直接用）

题目仓库已 clone 在 `~/E/code/ctf/hackasat/`：

```bash
ls ~/E/code/ctf/hackasat/
# hackasat-qualifier-2022  hackasat-qualifier-2023
```

若需补其他年份：

```bash
cd ~/E/code/ctf/hackasat
git clone https://github.com/cromulencellc/hackasat-qualifier-2021.git
git clone https://github.com/cromulencellc/hackasat-qualifier-2020.git
cd ~/E/code/space-sec-portfolio    # 回仓库根目录
```

> 📌 题目放在**作品集仓库之外**——体积大、有各自 license（MIT + 内嵌 cFS/COSMOS 等条款）。你的 writeup 才是要入库的产物。

### 2.1 M1 题单（已实地清点，无需自己 grep）

⚠️ **别用关键词 grep 找题**——目录名是**内部名**，且 grep "ccsds\|apid" 会大量误报（小说文本里的 "rapidly"）。完整清点结果见 [challenge-inventory.md](challenge-inventory.md)，M1 直接按下表做：

| 顺序 | 记分板名 | 内部路径（相对 `~/E/code/ctf/hackasat/`） | 难度 | 作用 |
|---|---|---|---|---|
| 1 | QAM | `hackasat-qualifier-2023/challenges/2_Cant_Stop_The_Signal_Mal/0_QAM` | 1/5 | 热身：QAM 符号解调 |
| 2 | Dashing | `hackasat-qualifier-2023/challenges/2_Cant_Stop_The_Signal_Mal/1_Dashing` | 1/5 | 热身：摩尔斯解码 |
| 3 | **FAUXY Lady** ⭐ | `hackasat-qualifier-2023/challenges/2_Cant_Stop_The_Signal_Mal/2_Fauxy_Lady` | 3/5 | **主攻**，见 §2.2 |
| 4 | Doppler | `hackasat-qualifier-2022/doppler` | 4/5 | 进阶：多普勒+路径效应下行解码 |
| 5 | Dark Side of the Dishy | `hackasat-qualifier-2023/challenges/2_Cant_Stop_The_Signal_Mal/3_Dark_Side_of_the_Dishy` | 5/5 | 拉伸（可选） |

**M1 下限**：做出 1–3 题并写透 FAUXY Lady 一篇 writeup 即达标。第 4、5 题属加分。

### 2.2 FAUXY Lady 是什么（主攻题）

**题面**：某大学立方星的遥测需要接收。给一段 `.wav` 录音 + 官方遥测定义，要求重建遥测包。信号：**BPSK 调制、差分编码、44.1k 采样率**。

**帧结构**（读 `generator/packets.py` 得出）：

```
[1a cf fc 1d] [len][len] [ 7e | 14B 收发呼号 | 03 | F0 | 80B 载荷 | CRC16 | 7e ]
 ^^^^^^^^^^^             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
 CCSDS TM 传输帧          内层 AX.25 风格帧 —— 与 M0 解 CUBEBEL-2 时同源
 同步字 (ASM)
```

**与 M0 的对应关系**：

| 环节 | M0（CUBEBEL-2） | FAUXY Lady |
|---|---|---|
| 解调 | gr-satellites 内建（9k6 FSK） | 自己搭 BPSK + 差分解码流图 |
| 帧同步 | KISS `0xC0` 分隔 | `1a cf fc 1d` 同步字 |
| 内层帧 | 真 AX.25（呼号左移 1 位，`EU11S > EU1XX`） | AX.25 **风格**（`0x7e` flag + CRC，但呼号是明文 ASCII） |
| 字段解析 | 无公开格式表（坑 8） | ✅ **官方给了 `tlm_def.pdf`** |

> 💡 M0 卡在"没有遥测格式表"，这题**官方直接给你格式表**——正好补上 M0 没做成的字段级解析。

**关键素材**：

```bash
cd ~/E/code/ctf/hackasat/hackasat-qualifier-2023/challenges/2_Cant_Stop_The_Signal_Mal/2_Fauxy_Lady
ls static/              # tlm_def.pdf（遥测定义）、tlm_def.zip
cat generator/packets.py    # 帧构造逻辑——看懂它就知道怎么反过来解
ls solver/              # solver.grc（GNU Radio 参考解流图），卡住再看
open static/tlm_def.pdf # 先读遥测定义
```

---

## 3. 本地起题（每题 20–40 分钟）

> 以下命令摘自 `hackasat-qualifier-2023/README.md` 官方原文。**未在本机实测**（需 Docker Desktop 运行），首次执行时以各题目录自己的 `README.md` 为准。
>
> 🚦 **做 FAUXY Lady 的最短路径**：§3.0 装 socat（其实也可跳过——本题不起服务）→ **直接 §3.3**。
> §3.1 的 base 镜像与 §3.4–3.7 的服务化流程对本题都用不上。

### 3.0 先装 socat

`make challenge` 用 socat 把容器暴露成一个端口。macOS 上先装：

```bash
brew install socat
```

### 3.1 基础镜像 —— ⏭️ **M1 默认跳过，直接看 §3.3**

> ✅ **主攻题 FAUXY Lady 不需要任何 base 镜像**，QAM、Dashing 也不需要。
> 已实测：跑 `base_challenge/build.sh` 会失败，而且**跑它对 M1 毫无用处**。直接跳到 §3.3。

M1 题单的实际依赖（`grep '^FROM' */Dockerfile` 实测）：

| 题目 | generator / solver 的 FROM | 需要 base？ |
|---|---|---|
| **FAUXY Lady**（主攻） | `ubuntu:22.04` × 2 | ❌ **不需要** |
| QAM | `ubuntu:22.04` × 2 | ❌ 不需要 |
| Dashing | `python:3` / `python:3.10` | ❌ 不需要 |
| Dark Side of the Dishy（拉伸 5/5） | generator = `has4/quals/challenges/ctfphasedarray` | ✅ 需要 |

**换一道题时怎么自查**（一条命令）：

```bash
grep -h '^FROM' <题目目录>/*/Dockerfile
# 出现 has4/quals/... → 需要先建 base
# 全是 ubuntu:/python: → 直接 make build
```

<details>
<summary>只有要做 Dishy 时才展开：如何建 base（已知会失败）</summary>

```bash
cd ~/E/code/ctf/hackasat/hackasat-qualifier-2023
pushd challenges/base_challenge/    # ⚠️ 是 base_challenge（单数），官方 README 写成了复数
./build.sh
popd
docker images | grep -i 'has4/quals/challenges/ctf' | wc -l    # 官方称应有 ≥7
```

**实测失败**，报错形如：

```
E: Failed to fetch http://ports.ubuntu.com/.../python3-minimal_3.8.2-0ubuntu2_arm64.deb  502
ERROR: process "/bin/sh -c apt-get update -y && ... python-dev ..." exit code: 100
```

三层原因（详见 [M1-pitfalls.md](M1-pitfalls.md) 坑 1）：

1. `phased_array_base` 与 `pyctf_base` 都是 `FROM ubuntu:focal`（20.04，**已 EOL**）
2. 安装列表含 **`python-dev`** —— Python 2 的开发包，focal 里已废弃，网络正常也大概率装不上
3. Apple Silicon 拉 `ports.ubuntu.com` 的 arm64 包，该源返回 502

**这是 2023 年赛题的历史包袱，不是你的环境问题。** 若非做 Dishy 不可，可试（均未实测）：
`--platform linux/amd64` 走模拟；把 Dockerfile 里的 `python-dev` 删掉或换成 `python3-dev`；换 apt 镜像源。

</details>

### 3.2 理解三件套

每道题最多有三个 Docker 镜像：

| 镜像 | 作用 | 你怎么用 |
|---|---|---|
| **generator** | 生成发给选手的静态文件（二进制、录音等） | 先跑它拿题目附件 |
| **challenge** | 题目服务本体 | 起它，然后连上去打 |
| **solver** | 官方参考解 | **卡住时才看**，先自己打 |

> ⚠️ **不是每道题三个都有**。先看该题 Makefile 有哪些 target：`grep -E "^[a-z_]+:" Makefile`

### 3.3 FAUXY Lady 的实际流程（离线题，无需起服务）

**已核实**：Fauxy Lady 的 Makefile 只有 `build` / `generator` / `solver`，**没有 `challenge` target**——它是纯离线题，生成一个 `.wav` 给你解，不用连任何服务。

```bash
cd ~/E/code/ctf/hackasat/hackasat-qualifier-2023/challenges/2_Cant_Stop_The_Signal_Mal/2_Fauxy_Lady
cat README.md
grep -E "^[a-z_]+:" Makefile      # 确认有哪些 target

make build                        # 构建 generator 与 solver 镜像（内部名 satsig）
make generator                    # 产出 out/signal.wav ← 这就是题目附件
ls -la out/
open static/tlm_def.pdf           # 官方遥测定义，解字段要用
```

拿到 `out/signal.wav` 就可以离线做题了：44.1k 采样、BPSK、差分编码 → 解调出比特流 → 按 `1acffc1d` 切帧（§5.1）→ 按 `tlm_def.pdf` 解字段。

想自定义 flag：`make generator FLAG='flag{my_test}'`。

卡住再看参考解（`make solver`，或直接读 `solver/solver.grc` 的 GNU Radio 流图参数）。

### 3.4 其他题的通用流程（需要起服务时）

```bash
cd <题目目录>
cat README.md              # 永远先读这个
make build                 # 主入口
make challenge             # 起容器 + socat，会打印 "To connect: nc localhost 12345"
```

另开终端连上去：

```bash
nc localhost 12345
```

**调试**：socat 把所有输出写到同目录的 `log` 文件。题目卡死或没反应，先看它：

```bash
cat log
```

杀掉题目：`docker kill <容器>`。

### 3.5 手动跑三件套（需要精细控制时）

官方 README 给的完整参数形式：

```bash
# generator：生成某个 seed 对应的题目文件
docker run -t --rm -v <输出目录>:/out -e SEED=<seed> -e FLAG=<flag> <container>:generator

# challenge：基本形式
docker run --rm -i -e SEED=<seed> -e FLAG=<flag> <container>:challenge
# 需要生成文件时
docker run --rm -i -e DIR=/mnt -v <dir>:/mnt -e SEED=<seed> -e FLAG=<flag> <container>:challenge
# 需要额外开端口（受管连接）时
docker run --rm -i -e SERVICE_HOST=<host> -e SERVICE_PORT=<port> -e SEED=<seed> -e FLAG=<flag> <container>:challenge

# solver：验证题目可解
docker run -it --rm -e HOST=<host> -e PORT=<port> <container>:solver
docker run -it --rm -e HOST=<host> -e PORT=<port> -e DIR=/mnt -v <dir>:/mnt <container>:solver
```

不用 xinetd 自建监听：

```bash
# 注意把上面命令里的冒号用反斜杠转义
socat -v tcp-listen:<port>,reuseaddr "exec:<上面的 docker run 命令>"
```

### 3.6 ⚠️ ticket-taker 未开源——怎么绕

官方明确未开源 `ticket-taker`、`lifecycle-manager`、`sat-solver`、`async/lounge`。比赛时 `ticket-taker` 负责：拿 ticket → 生成 seed 和 flag → 用环境变量启动题目容器。

本地绕法：

1. **自己指定 SEED 和 FLAG**（最简单）：如 §3.5，直接 `-e SEED=1234 -e FLAG=flag{test}`，跳过票务
2. **用官方 decoder ring 复现原题**：仓库根的 `tickets.csv` 把比赛当时的 ticket 映射到 seed，可还原出与当年某队完全相同的题目实例
   ```bash
   head -3 ~/E/code/ctf/hackasat/hackasat-qualifier-2023/tickets.csv
   ```
3. **离线做题**：协议/信号解析类题目只需 generator 产出的静态文件，根本不用起服务

> 💡 FAUXY Lady 属第 3 类——拿到 `.wav` 和 `tlm_def.pdf` 就能离线做完，本地门槛最低。

### 3.7 用 pwntools 交互（需要连服务的题）

```python
from pwn import *
io = remote('localhost', 12345)
print(io.recvline())
io.send(b'...')
print(io.recvall())
```

---

## 4. CCSDS 速成（1 小时，做题前必读）

> 本节讲 **Space Packet 主包头**——CCSDS 家族里最常见的一层。FAUXY Lady 用的是**传输帧同步字**那一层（§5.0 会分清三层），但这套"定长头+位域"的读法通用，且后续 cFS/真实遥测必用。

### 4.1 主包头：6 字节，全是位域

```
 字节:  0        1        2        3        4        5
      +--------+--------+--------+--------+--------+--------+
      |vvvT S aaaaaaaaaaa|ff cccccccccccccc|  包数据长度     |
      +--------+--------+--------+--------+--------+--------+
       ^^^ ^ ^  ^^^^^^^^^^^ ^^  ^^^^^^^^^^^^^^  ^^^^^^^^^^^^
```

| 字段 | 位宽 | 位置 | 含义 |
|---|---|---|---|
| 版本号 Version | 3 | 字节 0 高 3 位 | 恒为 `000` |
| 类型 Type | 1 | | **0=遥测 TM，1=遥控 TC** |
| 次级头标志 Sec Hdr Flag | 1 | | 1 表示主包头后还有次级头（常放时间戳） |
| **APID** | 11 | 跨字节 0–1 | **应用进程标识——最关键的字段**，相当于"这包数据是谁发的/给谁的" |
| 序列标志 Seq Flags | 2 | 字节 2 高 2 位 | `11`=独立包，`01`=首段，`00`=继续段，`10`=末段 |
| 序列计数 Seq Count | 14 | | 递增计数器，**断号=丢包，重复=可疑重放** |
| 包数据长度 | 16 | 字节 4–5 | ⚠️ **值 = 用户数据区字节数 − 1**（经典 off-by-one 陷阱） |

**整包长度 = 6 + (包数据长度字段 + 1)**

### 4.2 与 M0 的 AX.25 对照（认知迁移）

| | AX.25（M0 已做） | CCSDS Space Packet |
|---|---|---|
| 头部 | 16 字节（双呼号+control+PID） | 6 字节主包头 |
| 寻址 | 呼号 `EU11S > EU1XX` | APID（11 bit 数字） |
| 分帧 | KISS 的 `0xC0` 分隔符 | 靠**长度字段**自描述，无分隔符 |
| 载荷 | info 字段 | 用户数据区（可能先有次级头） |

> 关键差异：CCSDS **没有帧分隔符**，全靠长度字段自描述往前推。所以长度字段填错 = 后面所有包全乱——这本身就是常见的题眼和漏洞点。

### 4.3 安全视角（写 writeup 时的"防御视角"素材）

做题时留意这几处，它们既是题眼也是真实系统的弱点：

- **无认证**：Space Packet 本身不带签名/MAC，任何人能构造合法包 → 指令伪造
- **序列计数可预测**：14 bit 明文递增，重放/注入难被察觉
- **长度字段可撒谎**：声明长度与实际不符 → 解析器缓冲区溢出或包边界错乱
- **APID 无访问控制**：知道 APID 就能冒充该应用发包

---

## 5. 解析实操

### 5.0 先分清三层——用错工具是最常见的浪费

CCSDS 是一族标准，**同步字和 Space Packet 不是一回事**：

| 层 | 标志 | FAUXY Lady 里 | 用什么解 |
|---|---|---|---|
| **传输帧**（TM Transfer Frame） | 同步字 `1a cf fc 1d` | ✅ 有 | [`tools/asm_deframe.py`](../tools/asm_deframe.py) |
| **内层链路帧** | `0x7e` flag + 呼号 + CRC | ✅ 有（呼号是**明文 ASCII**） | 同上，一并解完 |
| **Space Packet** | 6 字节主包头（APID/序列/长度） | ❌ 无 | [`tools/ccsds_parse.py`](../tools/ccsds_parse.py) / ccsdspy |
| 真 AX.25（呼号左移 1 位） | KISS `0xC0` 分隔 | ❌ 无（M0 才是） | [`tools/kiss_parse.py`](../tools/kiss_parse.py) |

> ⚠️ **FAUXY Lady 用的是前两层**，一个 `asm_deframe.py` 全包。`ccsds_parse.py`（Space Packet）和
> `kiss_parse.py`（真 AX.25）对这题**都不适用**——虽然内层帧长得像 AX.25，但呼号是明文没做位移。
> 那两个工具留给后续真正的 Space Packet 数据（cFS、真实任务遥测）和 M0 那类真实卫星帧。

### 5.1 按同步字切帧（FAUXY Lady 用这个）

解调出比特流后，用本仓库的 [`tools/asm_deframe.py`](../tools/asm_deframe.py)（纯标准库）一步到位：

```bash
# 完整解析：切帧 + 呼号 + CRC 校验 + 载荷 hexdump
python3 tools/asm_deframe.py demod_bits.bin

# 只要可打印文本——flag 直接出来
python3 tools/asm_deframe.py demod_bits.bin --ascii-only

# 其他开关
python3 tools/asm_deframe.py stream.hex --hex        # 输入是 hex 文本
python3 tools/asm_deframe.py demod.bin --no-inner    # 只切帧，不解内层
python3 tools/asm_deframe.py demod.bin --raw-only    # 每帧原始 hex，方便贴 writeup
python3 tools/asm_deframe.py demod.bin --sync <hex>  # 自定义同步字
```

输出形如：

```
=== 帧 1 / 2 ===
  长度字段: 100 / 100 (一致)
  呼号: 1AB-CDE > 2FGHI-1   control=0x03 pid=0xf0
  CRC-16/XMODEM: 收到 0x88d7 / 计算 0x88d7 ✅
  0000  66 6c 61 67 7b 74 68 31 73 ...                   flag{th1s...
```

它会自动抓出三类异常，都是解调没调好的信号：

- **双份长度字段不一致** → 比特流有误码
- **CRC ❌** → 载荷被破坏（哪怕只翻转 1 bit 也能抓到）
- **帧被截断 / 结束 flag 不是 0x7e** → 采样窗口截短或丢帧

> ✅ 该脚本的 CRC 实现已与题目自带的 `generator/crc.py` **逐向量比对一致**（含 XMODEM 标准校验值 `0x31c3`），并用照 `packets.py` 逻辑合成的数据做过完整自测。

**帧格式**（脚本 docstring 里也有）：

```
[1a cf fc 1d][len:2][len:2][ 7e | 14B 呼号 | 03 | F0 | 载荷 | CRC:2 | 7e ]
              长度写两遍     CRC 覆盖：呼号+control+PID+载荷（不含 flag）
```

⚠️ **别用 `kiss_parse.py` 解这题**：本格式的呼号是**明文 ASCII**（`1AB-CDE2FGHI-1`），而真 AX.25 的呼号每字节左移 1 位。M0 的 `decode_callsign()` 用在这里会输出乱码。三个工具的分工见 [tools/README.md](../tools/README.md)。

### 5.2 快速 triage：Space Packet 数据用这个

若拿到的是真正的 CCSDS Space Packet 流（**不是** FAUXY Lady），用 [`tools/ccsds_parse.py`](../tools/ccsds_parse.py)（纯标准库）：

```bash
python3 tools/ccsds_parse.py dump.bin

# 输入是 hex 文本
python3 tools/ccsds_parse.py dump.hex --hex

# 只看某个 APID
python3 tools/ccsds_parse.py dump.bin --apid 100

# 只要原始 hex，方便贴进 writeup
python3 tools/ccsds_parse.py dump.bin --raw-only
```

输出形如：

```
=== 包 1 / 3 ===
  APID=100 (0x064)  TM(遥测)  次级头=无  版本=0
  序列: 独立包 #1   数据区 11 字节（长度字段=10）
  0000  48 45 4c 4c 4f 20 54 4c 4d 00 01                 HELLO TLM..
```

它会自动标出**截断包**（声明长度 > 实际字节数）——这类异常往往就是题眼。

### 5.3 字段级解析：用 ccsdspy

`ccsds_parse.py` 只做到主包头层。要把用户数据区解成有意义的字段（时间、电压、温度、指令参数），用 ccsdspy 按该题的遥测定义写结构：

```python
import ccsdspy
from ccsdspy import PacketField, PacketArray

pkt = ccsdspy.FixedLength([
    PacketField(name='TIME_SEC',  data_type='uint', bit_length=32),
    PacketField(name='OPMODE',    data_type='uint', bit_length=3),
    PacketField(name='SPACER',    data_type='fill', bit_length=5),   # 填充位用 fill
    PacketField(name='VOLTAGE',   data_type='int',  bit_length=16),
    PacketArray(name='SENSORS',   data_type='uint', bit_length=16, array_shape=(8,)),
])

result = pkt.load('dump.bin', include_primary_header=True)
print(result['CCSDS_APID'])      # 主包头字段默认可取
print(result['VOLTAGE'])         # 每个字段是一个数组（所有包的该字段）
```

要点：
- 主包头**不用**写进 `fields` 列表，`include_primary_header=True` 即可取到
- 变长数据用 `PacketArray(..., array_shape="expand")` 撑满剩余
- 字段定义从哪来？题目给的文档、源码里的结构体、或 §6 让 AI 推断后验证

### 5.4 构造包（做主动题时）

```python
def build_ccsds(apid, payload, ptype=0, sec_hdr=0, seq_flags=0b11, seq_count=0):
    w0 = (0 << 13) | (ptype << 12) | (sec_hdr << 11) | (apid & 0x7FF)
    w1 = (seq_flags << 14) | (seq_count & 0x3FFF)
    return (w0.to_bytes(2, 'big') + w1.to_bytes(2, 'big')
            + (len(payload) - 1).to_bytes(2, 'big') + payload)

# 注意长度字段是 len-1，这是最常踩的坑
pkt = build_ccsds(apid=0x64, payload=b'\x01\x02\x03', ptype=1)
```

---

## 6. AI-as-subject：LLM 辅助协议帧解析与异常标注

> 这是阶段 A 的**差异化产出**（见 [ai-workflow.md](../docs/ai-workflow.md)），不是可选项——每篇 writeup 都要有这一节。
> 核心纪律：**AI 负责猜，程序负责验**。AI 的字段推断必须被解析脚本或校验程序证实后才能写进结论。
>
> 📌 本手册开头那条"CCSDS 题类"假设被实地清点推翻，就是一条现成的 AI 出错记录——直接写进第一篇 writeup。

### 6.1 用法一：让 AI 推断未知字段布局

拿到一段不知道结构的用户数据区，把 hexdump 喂给模型：

```
下面是同一个 APID 的 5 个 CCSDS 包的用户数据区 hexdump。
请推断字段布局：哪几字节是单调递增的计数器/时间戳？哪些字节在包间恒定
（可能是 ID 或常量）？哪些像是浮点数或有符号整数？
给出一个 ccsdspy 的 FixedLength 定义草稿，并说明每个字段推断的**依据**
以及你的**置信度**。不确定的地方明确说不确定，不要猜一个确定的答案。

<粘贴 ccsds_parse.py 的输出>
```

然后**验证**：把 AI 给的 `FixedLength` 定义跑一遍，看解出的值是否物理合理（电压在 0–30V？时间单调递增？模式字段只取少数几个值？）。不合理就回去改。

### 6.2 用法二：异常标注

把多个包的解析结果交给 AI 做模式挖掘：

```
以下是 N 个 CCSDS 包的主包头字段（APID / 序列计数 / 长度）。
请找出异常：序列计数断号或重复、长度字段与实际不符、APID 突变、
时间戳倒流。对每个异常说明它在**安全**上可能意味着什么
（丢包 / 重放 / 注入 / 解析器攻击），并区分"已确认"与"推测"。
```

这类"AI 找异常 → 人工确认 → 写进 writeup"的闭环，就是 ai-workflow.md 说的 AI-as-subject。

### 6.3 必须记录的三件事

每篇 writeup 的「AI 运用」节按 [`_TEMPLATE.md`](writeups/_TEMPLATE.md) 记：

1. **工具与角色**：哪个模型、做副驾还是 subject
2. **人工验证**：AI 的关键结论怎么被证实的（跑了什么脚本、对比了什么），标注"已验证/存疑"
3. **AI 出错记录**：AI 猜错字段边界、编造 CCSDS 规范细节的案例——**这是最有价值的素材**，体现你的判断力而非盲信

> M0 的经验可参照：[M0-pitfalls.md](../phase-b-rf/M0-pitfalls.md) 里 AI 四类角色的实录写法。
> 读英文规范/题目时可用本地翻译链路（Hy-MT2-1.8B，见 ai-workflow.md 工具层）。

---

## 7. 写 writeup

用现成模板：

```bash
cp phase-a-software/writeups/_TEMPLATE.md \
   phase-a-software/writeups/<年份>-<题目名>.md
```

各节要写什么：

| 节 | 要点 |
|---|---|
| 题目描述 | 一两句，别整段抄原题 |
| **背景知识** | 面向不懂空间的读者讲清 CCSDS 传输帧/AX.25 是什么、这题涉及哪个特性——**这节最能体现水平** |
| 侦察与分析 | 你怎么认出同步字 `1acffc1d` 和内层 AX.25 的？贴切帧脚本的输出 |
| 攻击思路 | 解调参数怎么定的、帧结构怎么反推的 |
| 解题步骤 | **可复现**的命令与脚本，别人照做能出同样结果 |
| AI 运用 | 见 §6.3 三件事（"CCSDS 题类"假设被证伪就是一条现成的 AI 出错记录） |
| 复盘 | 真实系统里的对应 + **防御视角**（§4.3 的素材用在这里）+ 与 M0 真实卫星的对照 |

**质量标准**（README 定的）：让不看题的人也能读懂攻击原理；题目可本地复现。

解题脚本放 `phase-a-software/solutions/<题目名>/`，writeup 里链过去。

---

## 8. 交付物清单

- [ ] `phase-a-software/env.md` —— 环境版本（§1 生成）
- [x] `writeups/2023-fauxy-lady.md` —— **M1 核心交付**，写透一篇 ✅ 2026-10-29 全链路实做完成
- [ ] （可选）QAM / Dashing / Doppler 各一篇短 writeup，凑成题类系列
- [x] `solutions/2023-fauxy-lady/` —— 可复现的解题脚本（`solve_fauxy.py`：频偏校正→RRC→定时→差分译码→切帧→CRC）
- [x] writeup「AI 运用」节完整（✅ 含 4 条 AI 出错记录；AI-as-subject 实验待下一轮）
- [x] 更新 `phase-a-software/README.md` 进度勾选
- [x] `M1-pitfalls.md` 已沉淀 6 条真实坑

---

## 9. 排障速查

> 除标注"实测"外，以下为按官方 README 与 M0 经验的预判；做完后用真实踩坑替换。

| 症状 | 最可能原因 | 处理 |
|---|---|---|
| `docker: Cannot connect to the Docker daemon` | Docker Desktop 没启动 | 打开 Docker Desktop App，等鲸鱼图标稳定 |
| `make challenge` 报 socat not found | macOS 默认没有 socat | `brew install socat`（§3.0）；FAUXY Lady 用不到 |
| `base_challenge/build.sh` 报 apt 502 / exit code 100 | ✅**实测坑**：base 是 EOL 的 `ubuntu:focal` + 含废弃包 `python-dev`，arm64 源不稳 | **先确认题目真需要它**——M1 只有 Dishy 需要，其余跳过（§3.1、[pitfalls 坑 1](M1-pitfalls.md)） |
| `docker images \| grep has4 \| wc -l` 返回 0 | base 未建成 | 同上；不影响 FAUXY Lady / QAM / Dashing |
| 题目容器起来就退出 | 缺 SEED/FLAG 环境变量 | 自己指定 `-e SEED=1234 -e FLAG=flag{test}`（§3.6） |
| 本机没有 docker，`make generator` 跑不了 | ✅**实测坑**：容器只是打包，信号生成本身只依赖两条 python 命令 | 直接跑 `packets.py` + `satsig.py`（grsat 环境），见 [pitfalls 坑 2](M1-pitfalls.md) |
| `wave.Error: unknown format: 3` | ✅**实测坑**：GNU Radio 写 IEEE float WAV，`wave` 只认 PCM | 用 `scipy.io.wavfile`，双声道即 I/Q（pitfalls 坑 3） |
| 解调比特全是碎 run、搜不到 ASM | ✅**实测坑**：差分译码门限错（`angle>0`），或长度字段按 32 bit 切 | 0/π 门限 `u.real<0`；长度取 16 bit、第二遍做校验（pitfalls 坑 4/5） |
| 题目没反应/像是崩了 | 容器内异常 | **看同目录的 `log` 文件**——socat 把输出都写那儿（§3.4） |
| 镜像构建慢/拉不动 | 网络 | 配 Docker 镜像加速器，或走离线路线（§3.6 绕法 3） |
| Apple Silicon 上镜像跑不起来 | 镜像是 amd64 的 | `docker run --platform linux/amd64 ...` |
| 切不出帧 / 帧数不对 | 同步字找错层 | FAUXY Lady 用 `1acffc1d`，**不是** Space Packet 主包头（§5.0） |
| `ccsds_parse.py` 解 FAUXY Lady 全是乱码 | **用错工具**——它解的是 Space Packet | 这题走 AX.25 路线，见 §5.1 |
| ccsdspy 解出的值离谱 | 字段定义与实际布局不符 | 检查填充位（`data_type='fill'`）、大小端、有无次级头占位 |
| 找不到题目对应的目录 | 目录用**内部名**不是记分板名 | 查 [challenge-inventory.md](challenge-inventory.md) 的映射表 |

---

## 10. Kill-switch

- **单题卡死 >2 天** → 换题单里的下一道；原题记入"待回头"，别死磕
- **FAUXY Lady 卡死** → 仓库自带 `team_writeups/`（**20 支队伍的官方 writeup**，含 Solar Wine、PPP、mhackeroni、DiceGang）：
  ```bash
  ls ~/E/code/ctf/hackasat/hackasat-qualifier-2023/team_writeups/
  ```
  读完**自己复现一遍**再写 writeup，文中如实注明"参考了 XX 队 writeup"——诚实的复现记录仍是有效产出
- **解调整体走不通** → 直接读 `generator/packets.py` 理解帧结构，用 `solver/solver.grc` 的参数搭流图；实在不行退回纯帧解析（跳过 DSP 层，用 solver 产出的比特流做后半段）
- **Docker 路线整体走不通** → FAUXY Lady 本来就能离线做（`.wav` + `tlm_def.pdf`），不受影响

> M1 的下限是**一篇高质量 writeup**。宁可一篇写透（背景+复现+防御视角俱全），不要三篇流水账。

---

## 参考

- **本地题库**：`~/E/code/ctf/hackasat/`（2022 + 2023）· 完整题目清单见 [challenge-inventory.md](challenge-inventory.md)
- [Hack-A-Sat 2023 quals](https://github.com/cromulencellc/hackasat-qualifier-2023) · [2022](https://github.com/cromulencellc/hackasat-qualifier-2022) · [2021](https://github.com/cromulencellc/hackasat-qualifier-2021) · [2020](https://github.com/cromulencellc/hackasat-qualifier-2020)
- 官方 writeup：2023 仓库内 `team_writeups/`（20 支队伍）· [2022 techpapers](https://github.com/cromulencellc/hackasat-qualifier-2022-techpapers) · [2021 techpapers](https://github.com/cromulencellc/hackasat-qualifier-2021-techpapers)
- [hack-a-sat-library（空间文档与教程合集）](https://github.com/deptofdefense/hack-a-sat-library)
- [solar-wine/writeups（强队解法）](https://github.com/solar-wine/writeups)
- [CCSDSPy 文档](https://docs.ccsdspy.org/) · [CCSDS 蓝皮书原文](https://public.ccsds.org/)
- M0 经验：[M0-playbook](../phase-b-rf/M0-playbook.md) · [M0-pitfalls](../phase-b-rf/M0-pitfalls.md) · [解码记录](../phase-b-rf/decodes/obs_14593136_record.md)
