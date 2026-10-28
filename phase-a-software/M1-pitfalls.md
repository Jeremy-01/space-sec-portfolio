# M1 踩坑记录与经验沉淀

> 📍 [作品集首页](../README.md) › [阶段 A](README.md) › **M1 踩坑沉淀**

> 做 M1（信号→帧→遥测题类）过程中遇到的真实问题。体例同 [M0-pitfalls.md](../phase-b-rf/M0-pitfalls.md)。
> 既是 [M1-playbook.md](M1-playbook.md) 的勘误来源，也是后续题类的避坑手册。
>
> ✅ 已沉淀 6 条真实坑（2026-10-29，FAUXY Lady 全链路实做）——只记**真实踩过**的坑，不写预判。

## 🕳️ 坑 1：照手册建 base 镜像，构建失败（而且根本不用建）

| 项目 | 内容 |
| :--- | :--- |
| **现象** | 执行 M1 手册 §3.1 的 `challenges/base_challenge/build.sh`，apt 阶段报错退出：<br>`E: Failed to fetch http://ports.ubuntu.com/.../python3-minimal_3.8.2-0ubuntu2_arm64.deb 502 Bad Gateway`<br>`ERROR: ... exit code: 100`；随后 `docker images \| grep has4 \| wc -l` 返回 `0` |
| **原因** | 三层叠加，见下 |
| **解决** | **不用建**——M1 主攻的 FAUXY Lady 及 QAM、Dashing 都不依赖 base 镜像，直接 `make build` |

### 三层原因

**① 最根本的：这一步对 M1 是多余的**

查各题 Dockerfile 的 `FROM` 才发现，M1 题单里只有拉伸题 Dishy 需要 base：

```bash
$ grep -h '^FROM' 2_Cant_Stop_The_Signal_Mal/2_Fauxy_Lady/*/Dockerfile
FROM ubuntu:22.04
FROM ubuntu:22.04
```

| 题目 | FROM | 需要 base？ |
|---|---|---|
| FAUXY Lady（主攻） | `ubuntu:22.04` × 2 | ❌ |
| QAM | `ubuntu:22.04` × 2 | ❌ |
| Dashing | `python:3` / `python:3.10` | ❌ |
| Dark Side of the Dishy（5/5 拉伸） | `has4/quals/challenges/ctfphasedarray` | ✅ |

手册原文写的是"部分题目容器依赖预建的基础镜像"——措辞太弱，读起来像必做前置。已改为**默认跳过**。

**② 基础镜像已 EOL**

`build.sh` 第一步构建的 `phased_array_base`（以及 `pyctf_base`）都是：

```dockerfile
FROM ubuntu:focal      # 20.04，已 EOL
```

这解释了报错里为什么出现 `python3-minimal_3.8.2`（focal 的 Python 版本）。

**③ Dockerfile 里有废弃包**

```dockerfile
RUN apt-get install -y --no-install-recommends \
        python3-venv \
        python-dev \        # ← Python 2 的开发包，focal 里已废弃
        build-essential \
        ...
```

即便 apt 源完全正常，`python-dev` 这条也大概率装不上。**502 只是触发器，EOL 镜像 + 废弃包才是结构性隐患**——这是 2023 年的赛题，基础设施早已过期。

另：本机是 Apple Silicon（arm64），拉的是 `ports.ubuntu.com` 的 arm64 包，该源当时返回 502。

### 若非做 Dishy 不可（均未实测）

- `docker build --platform linux/amd64 ...` 走 Rosetta 模拟，避开 arm64 源
- 把 Dockerfile 里的 `python-dev` 删掉，或换成 `python3-dev`
- 换 apt 镜像源（阿里云/清华）

## 🕳️ 坑 2：本机没有 docker，`make generator` 跑不了

| 项目 | 内容 |
| :--- | :--- |
| **现象** | `docker: command not found`（本机未装 Docker/OrbStack/colima）；而 `make generator` 依赖 `docker build` + `docker run` |
| **原因** | 容器只是「打包运行环境」，信号生成本身只依赖两条 python 命令（`make_challenge.sh` 里写得明明白白） |
| **解决** | 直接跑源码命令（grsat conda 环境自带 GNU Radio 3.10）：<br>`FLAG='flag{FAKE_FLAG}' python3 packets.py` → `tx_stream`（420 B）<br>`python3 satsig.py` → `signal.wav`（985 KB，2.79 s） |
| **验证等价性** | 文件时长反推：420 B × 8 bit ÷ 1200 baud = 2.8 s，与实际 2.79 s 精确吻合——容器内外产出同一码流 |

### ⚠️ 坑 1 勘误（实做时发现）

坑 1 的 `grep '^FROM'` 验证**不完整**：`generator/Dockerfile` 第 2 行是

```dockerfile
COPY --from=has4/quals/generator-base/generator-base:latest /upload/ /upload
```

base 镜像确实被引用——不在 FROM，而在 **COPY --from**（构建期从外部镜像拷文件）。所以「FAUXY Lady 不依赖 base」在 **build 层面不成立**，`make build` 仍会因拉不到 `generator-base` 而失败。上表「需要 base？❌」应修正为：

> build 引用 base；但**信号生成不需要容器**（坑 2 的等价路线）。

## 🕳️ 坑 3：GNU Radio 写的 WAV，Python `wave` 模块读不了

| 项目 | 内容 |
| :--- | :--- |
| **现象** | `wave.open('signal.wav')` 报 `wave.Error: unknown format: 3` |
| **原因** | `wavfile_sink(FORMAT_FLOAT)` 写的是 IEEE float WAV（format tag 3），`wave` 模块只认 PCM（tag 1） |
| **解决** | 用 `scipy.io.wavfile.read`；双声道两列即 I/Q：`iq = raw[:,0] + 1j*raw[:,1]` |

## 🕳️ 坑 4：差分译码拿 `angle(u) > 0` 当判决，星座带残余旋转时全错

| 项目 | 内容 |
| :--- | :--- |
| **现象** | 符号星座肉眼干净（空闲段 −5°/176° 完美交替），差分译码输出却是碎 run（最长 9），ASM 搜不到 |
| **原因** | 相邻符号共轭乘积 `u = s[n]·conj(s[n-1])` 带残余相转 θ 时，「1→0」与「0→1」两种翻转分别落在 **+180°−θ** 与 **−180°+θ** 两侧——`angle(u) > 0` 把同一个「翻转」拆成两类，输出退化为符号流本身 |
| **解决** | 按 0/π 门限判：`bits = u.real < 0`（等价于判相位差更接近 0 还是 π），对任意固定相转免疫。改后最长 run 1289，ASM@1318 命中 |
| **教训** | 差分检测的判决门限是 **±90°（实部符号）**，不是 ±180° 分界（角度符号） |

## 🕳️ 坑 5：长度字段写了两遍，切片把两遍并成一个巨大的长度值

| 项目 | 内容 |
| :--- | :--- |
| **现象** | ASM 已命中（比特流 1318 处），帧解析却永远产出 0 帧；打印 `ln` 发现是 `0x00640064 = 6553700` |
| **原因** | 帧布局是 `ASM(4B) + len(2B) + len(2B) + 内层帧`——两遍长度各 16 bit；切片写成了 `s[pp+32 : pp+64]`（32 bit），把 `00 64 00 64` 并成一个数；载荷起点也随之错成 `pp+96`（正确是 `pp+64`） |
| **解决** | 第一遍 16 bit 取长度，第二遍做**一致性校验**（不一致弃帧），载荷从 `pp+64` 起 |
| **教训** | 「字段冗余」在解析器里应是「第二份当校验用」，不是「跳过 32 bit」——跳过量算错一次，后面全部错位 |

## 🕳️ 坑 6：Welch 谱峰 +398 Hz，不是载波频偏

| 项目 | 内容 |
| :--- | :--- |
| **现象** | 频谱峰值在 +398 Hz，若当载波中心去校正，频偏就错了 600 Hz |
| **原因** | 空闲段 `0xFF` 经差分编码变成 ±1 **交替**符号，等效 600 Hz 方波（baud/2）；载波 1 kHz 两侧各一条谱线，上边 1600 Hz 被 generator 的 1.5 kHz 低通压掉，只剩 1000−600=400 Hz 这条 |
| **解决** | 载波中心 = 谱线对的对称中心，或对照流图源码的 `rotator_cc` 直接确认；**谱峰 ≠ 载波**，盲频偏估计前先排除调制自带的谱线 |

### 附：排障方法教训

`sys.exit("消息")` 的消息走 **stderr**——bash 管道接 `grep` 后只看 stdout，会误判成「静默失败、退出码 0」。本次排障为此多耗两轮，管道调试一律 `2>&1`。

## 💡 关键经验

| # | 经验 |
| :--- | :--- |
| 1 | **照手册执行前，先确认这一步是不是当前目标所必需**。本次白跑一遍失败的构建，就是因为把"部分题目需要"读成了"必做前置"。一条 `grep '^FROM' */Dockerfile` 就能免掉。 |
| 2 | **老赛题的 Docker 环境天然脆弱**。2023 年的题用 2020 年的基础镜像，EOL + 废弃包 + 源变动叠加，构建失败是常态而非例外。遇到就先问"能不能绕过"，而不是硬修。 |
| 3 | **报错要读到根因层**。`502 Bad Gateway` 看着像网络问题（重试即可），但真正的隐患是 `ubuntu:focal` + `python-dev`——只重试永远不会成功。 |
| 4 | 手册里凡是"部分/某些 X 需要 Y"的表述，都应补上**怎么判断自己属不属于那部分**的具体命令。 |
| 5 | **判决门限要与调制结构对齐**。差分检测判的是"相位差是 0 还是 π"，门限在 ±90°（实部符号）；拿角度正负当门限，星座一有残余旋转就全错（坑 4）。 |
| 6 | **冗余字段要按"第二份做校验"来解析**，不是"多跳 16 bit"。两遍长度并读成 6553700，整帧解析全错（坑 5）。 |
| 7 | **频谱峰不一定是载波**。调制样式自带谱线（空闲交替符号 = baud/2 方波），盲频偏估计前先排除（坑 6）。另外 `sys.exit()` 的消息走 stderr，管道排障要 `2>&1`。 |
