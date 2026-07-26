# M0 操作手册：无硬件解出第一条真实遥测

> 📍 [作品集首页](../README.md) › [阶段 B](README.md) › **M0 操作手册**

> 目标：装好 GNU Radio + gr-satellites，用 [SatNOGS](https://network.satnogs.org/) 存档观测数据解出**一条**真实卫星遥测。
> 交付：解码截图 + 本手册最后一节的《步骤记录》填好。
> 平台：macOS（Apple Silicon / Intel 通用，命令一致）。预计 0.5–1 天。
>
> 📁 **路径约定**：下文命令均假设你已 `cd` 到仓库根目录，所有路径用相对写法：
> ```bash
> cd ~/E/code/space-sec-portfolio    # 只需在开工时执行一次
> ```

---

## 0. 前置检查（5 分钟）

```bash
# 确认 Homebrew 在位；没有就先装 https://brew.sh
brew --version

# 确认 Python 3.11+
python3 --version
```

若 `brew` 不存在：

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

---

## 1. 安装工具链（30–60 分钟，取决于网速）

### 1.1 GNU Radio

```bash
brew install gnuradio
```

验证：

```bash
# 命令行版本号
gnuradio-config-info --version

# 图形界面能打开（打开后可直接关掉，确认不报错即可）
gnuradio-companion
```

> ⚠️ 若 `gnuradio-companion` 报 Qt / 显示相关错误，多为 Homebrew 的 Qt 依赖没链上。先跑
> `brew reinstall pyqt@5 && brew link --overwrite pyqt@5`，再重开。

### 1.2 gr-satellites

> ⚠️ **坑 1 实测**：`pip install gr-satellites` 装不上（`No matching distribution found`）——它是
> GNU Radio 的 **C++ OOT 模块**，不是 PyPI 包。用 conda-forge 装（会连同 GNU Radio 一起进环境）：

```bash
# 没有 conda 就先装 miniforge：brew install miniforge && conda init zsh（重开终端）
conda create -n grsat -c conda-forge gnuradio-satellites
conda activate grsat
```

验证：

```bash
gr_satellites --help          # 有输出即成功
gr_satellites --version
```

> 说明：`gr_satellites` 命令行工具可**脱离 GNU Radio 图形流图**独立解码文件，这是 M0 最省事的路径。GNU Radio 本体主要留给后续 M3/M4 做实时流图。
> 之后每次开工记得 `conda activate grsat`。

### 1.3 记录环境版本（写进交付物）

```bash
mkdir -p phase-b-rf/decodes phase-b-rf/captures
{
  echo "## 环境版本 $(date '+%Y-%m-%d')"
  echo "- GNU Radio: $(gnuradio-config-info --version)"
  echo "- gr-satellites: $(gr_satellites --version 2>&1 | head -1)"
  echo "- Python: $(python3 --version)"
  echo "- OS: $(sw_vers -productName) $(sw_vers -productVersion)"
} >> phase-b-rf/decodes/env.md
cat phase-b-rf/decodes/env.md
```

---

## 2. 挑一次好解的存档观测（15 分钟）

在 [SatNOGS Network](https://network.satnogs.org/observations/) 找一次**成功的**观测。选择标准（从易到难）：

- **调制简单**：优先 `BPSK` / `AFSK` / `FSK`，避开高阶调制。
- **状态 Good**：观测列表里带绿色/"Good"标记，波形图能看到明显信号。
- **有解码框架**：卫星在 gr-satellites 支持列表内。查支持列表：

```bash
gr_satellites --list_satellites | less    # 按 q 退出分页，/ 搜索
# 常见易解目标示例：CUBEBEL-2（M0 实测）、JY1SAT、FUNcube-1 (AO-73)
# ⚠️ 坑 5：发射不久的新卫星（如 METEOR-M2-4）可能未收录，报 Satellite not found——换列表里的老卫星
```

**筛选技巧（在网页上操作，术语按 2026-07 版 UI；再改版就按语义找对应项）**：
1. 打开 https://network.satnogs.org/observations/
2. 左侧过滤器选 `Results → Good`、`Rated Artifacts → With Signal`（旧文档说的 "Status: Good" 已改名；部分选项藏在 `Show More Filters` 里）。
3. 点进一次观测。**下载链接藏在 `Audio` / `Data` 选项卡里**——它们是可点击的选项卡，点文字才会展开文件列表（`Audio` = 音频 .ogg，`Data` = IQ .dat）。
4. 记下：卫星名、NORAD ID、观测编号（Observation #）、频率、采样率。

> ⚠️ **采样率是最大坑（坑 6）**：观测 JSON 里的 `samp-rate-rx`（如 `1.024e6`）是**射频端 IQ 采样率**，
> 只在解 `.dat` IQ 文件时用。下载的 `.ogg/.wav` 是解调后的**音频**，已重采样——解码一律 `--samp_rate 48000`。

下载文件（右键"Download"→复制链接，或直接浏览器下）：

```bash
# captures/ 已在 1.3 步建好；大文件走 .gitignore，仅存元数据与截图
# 把 <URL> 换成观测页里的音频/IQ 下载直链
curl -L -o phase-b-rf/captures/obs_<观测号>.ogg "<URL>"
```

---

## 3. 解码（核心步骤，10–30 分钟含试错）

先设两个变量，后面命令都复用（省得反复写路径）：

```bash
OBS=12345                          # 换成你的 SatNOGS 观测号
CAP=phase-b-rf/captures/obs_$OBS   # 采集文件前缀
DEC=phase-b-rf/decodes/obs_$OBS    # 解码产物前缀
```

> ⚠️ **坑 4**：这两个变量是**相对路径**，只在**仓库根目录**执行有效。若 `cd` 进了子目录
> （如 `captures/`），路径会叠加成 `captures/phase-b-rf/captures/...` 而报 `No such file`。
> 出问题先 `echo "$CAP"` 看实际值；要么回根目录，要么改绝对路径。

`gr_satellites` 的通用形态：

```bash
gr_satellites <卫星名或NORAD> <输入源参数> --samp_rate <采样率> [解码输出参数]
```

### 3.1 用音频文件解（最常见）

SatNOGS 音频是 **44.1k/48k 的 WAV/OGG**。gr-satellites 直接吃 WAV；OGG 先转 WAV：

```bash
# 若下的是 .ogg，转成 wav（ffmpeg 没有就 brew install ffmpeg）
ffmpeg -i "$CAP.ogg" -ar 48000 "$CAP.wav"

# 解码：--wavfile 走音频输入
gr_satellites "<卫星名>" \
  --wavfile "$CAP.wav" \
  --samp_rate 48000 \
  --hexdump
```

- `--hexdump`：把解出的帧以十六进制打印到终端——**这就是"解出一条遥测"最直接的证据**。
- 用 NORAD ID 更稳（名字里有空格/特殊字符时）：把 `"<卫星名>"` 换成 `--satcfg` 对应项，或直接用 `gr_satellites --list_satellites` 里显示的准确名称。

### 3.2 用 IQ 文件解

IQ 文件需指明数据类型（SatNOGS 多为 `complex64`，即交错的 float32 I/Q）和采样率：

```bash
gr_satellites "<卫星名>" \
  --iq \
  --samp_rate <IQ采样率> \
  --f_offset 0 \
  --input_file "$CAP.dat" \
  --hexdump
```

> 若解不出，先怀疑三件事：**采样率填错**、**卫星框架选错**、**信号本身太弱**。换一次 Status=Good 且波形明显的观测通常立竿见影。

### 3.3 把解码结果落盘（交付证据）

```bash
# 把终端解码输出同时存文件（decodes/ 已在 1.3 步建好）
gr_satellites "<卫星名>" \
  --wavfile "$CAP.wav" \
  --samp_rate 48000 \
  --hexdump 2>&1 | tee "${DEC}_decode.txt"

# 另存 KISS 帧，供 3.4 用脚本解析 payload
gr_satellites "<卫星名>" \
  --wavfile "$CAP.wav" \
  --samp_rate 48000 \
  --kiss_out "${DEC}.kiss"
```

**截图**：终端里出现十六进制帧的那一刻，截屏存到 `phase-b-rf/decodes/obs_<观测号>_screenshot.png`（`Cmd+Shift+4`）。

### 3.4 把 KISS 帧解析成结构（本仓库自带脚本）

`--hexdump` 给的是裸字节。想看清 **AX.25 收/发呼号 + payload 分段**，用仓库里的
[`tools/kiss_parse.py`](../tools/kiss_parse.py)（纯标准库，无需 pip）：

```bash
python3 tools/kiss_parse.py "${DEC}.kiss" | tee "${DEC}_parsed.txt"
```

输出形如：

```
=== 帧 1 / 3  (27 字节) ===
  AX.25: MYSAT-1 > BEACON  control=0x03 pid=0xf0
  0000  48 45 4c 4c 4f 20 54 4c 4d ...                   HELLO TLM...
```

> 字段级遥测（电压/温度等）是**每颗卫星各异**的，需要该星的遥测格式表。脚本做到通用的
> “帧 → AX.25 头 + payload” 这一层；再往里的字段解析，等选定卫星后用它的格式表另写，
> 或直接用 gr-satellites 自带的 telemetry parser。可选参数 `--no-ax25` / `--raw-only` 见脚本头注释。

---

## 4. 交叉校验（证明不是自己蒙的，15 分钟）

回到该观测的 SatNOGS 页面，网络已由其他地面站解出的 **Demoded/Decoded Data** 应与你的十六进制帧**一致或高度吻合**。

- 对比帧头、长度、关键字段。
- 若卫星在 [SatNOGS DB](https://db.satnogs.org/) 有遥测解析模板，可看到字段级（电压/温度等）解出的值，进一步印证。

把校验结论写进下面的《步骤记录》。

---

## 5. 交付物清单

放在 `phase-b-rf/decodes/`：

- [x] `env.md` —— 环境版本（第 1.3 步生成）
- [x] `obs_<观测号>_decode.txt` —— 解码终端输出
- [x] `obs_<观测号>_parsed.txt` —— KISS 帧结构化解析（第 3.4 步生成）
- [x] `obs_<观测号>_screenshot.png` —— 出帧截图
- [x] 《步骤记录》→ [decodes/obs_14593136_record.md](decodes/obs_14593136_record.md)
- [x] 踩坑与经验沉淀 → [M0-pitfalls.md](M0-pitfalls.md)
- [x] 更新 `phase-b-rf/README.md` 进度：勾上 `- [x] M0`

✅ **M0 已于 2026-07-25 完成**（CUBEBEL-2，观测 #14593136）。

---

## 6. 步骤记录（照抄填空，即为交付文档）

```
### M0 解码记录
- 日期：
- 卫星名 / NORAD ID：
- SatNOGS 观测编号：https://network.satnogs.org/observations/<号>/
- 频率 / 调制 / 采样率：
- 输入文件类型：音频(.wav) / IQ(.dat)
- 解码命令（完整）：
- 解出帧数：
- 帧样例（前 1–2 行 hex）：
- 交叉校验结论：与 SatNOGS 网络解出数据是否一致 =
- 遇到的坑与解决：
- AI 用在哪：（如让 AI 解释调制/排查解码失败/解析 payload 字段）
```

---

## 7. 排障速查

| 症状 | 最可能原因 | 处理 |
|---|---|---|
| `gr_satellites: command not found` | 没激活 conda 环境 | `conda activate grsat` |
| `pip install gr-satellites` 装不上 | 它是 C++ OOT 模块，不在 PyPI | `conda install -c conda-forge gnuradio-satellites`（坑 1） |
| `Satellite not found`（名字和 NORAD 都试过） | 新卫星未收录进当前版本 | `--list_satellites` 里换老卫星（坑 5） |
| 有信号但 0 帧解出 | 采样率填错 | 音频用 48000；IQ 才用 JSON `samp-rate-rx`（坑 6） |
| 0 帧且波形也很弱 | 观测本身信噪比差 | 换 Results=Good、波形明显的观测 |
| `No such file` 但文件存在 | 相对路径变量在子目录叠加 | `echo "$CAP"` 查实际值，回根目录执行（坑 4） |
| OGG 无法读取 | gr-satellites 不吃 ogg | 先 `ffmpeg` 转 wav |
| 卡在 `less` 分页界面 | 分页器需按键退出 | 按 `q` 退出，`/` 搜索（坑 7） |
| `gnuradio-companion` 打不开 | Qt 未链上 | `brew reinstall pyqt@5 && brew link --overwrite pyqt@5` |

完整踩坑记录（8 坑 + 经验）见 [M0-pitfalls.md](M0-pitfalls.md)。

---

## Kill-switch（来自 roadmap）

若**两周内工具链始终装不通**，先跳去纯软件的[阶段 A](../phase-a-software/)（Hack-A-Sat writeup），RF 推后。工具链是软件问题，不阻塞整体进度。

**M0 实际结果：未触发。** 工具链一次走通（conda 路线），2026-07-25 交付完成。
