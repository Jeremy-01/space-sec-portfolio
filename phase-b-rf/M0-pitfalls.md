# M0 踩坑记录与经验沉淀

> 📍 [作品集首页](../README.md) › [阶段 B](README.md) › **M0 踩坑沉淀**

> 2026-07 完成 M0（SatNOGS 存档数据解出 CUBEBEL-2 遥测）过程中遇到的 8 个典型问题。
> 既是 [M0-playbook.md](M0-playbook.md) 的勘误来源，也是 M3/M4 物理接收阶段的避坑手册。
> 对应解码记录：[decodes/obs_14593136_record.md](decodes/obs_14593136_record.md)。

## 🕳️ 八个坑

### 坑 1：用 `pip install` 安装 gr-satellites

| 项目 | 内容 |
| :--- | :--- |
| **现象** | `pip install gr-satellites` 报 `No matching distribution found` |
| **原因** | gr-satellites 是 GNU Radio 的 C++ OOT 模块，不是 PyPI 包 |
| **解决** | 用 Conda：`conda install -c conda-forge gnuradio-satellites` |

### 坑 2：SatNOGS 界面筛选条件与文档对不上

| 项目 | 内容 |
| :--- | :--- |
| **现象** | 文档写 “Status: Good”，页面找不到该选项 |
| **原因** | SatNOGS 网站改版，术语和布局变了 |
| **解决** | 映射：`Results → Good`、`Rated Artifacts → With Signal`；点 `Show More Filters` 展开隐藏选项 |

### 坑 3：下载页面找不到数据文件

| 项目 | 内容 |
| :--- | :--- |
| **现象** | 详情页滚动到底，看不到下载链接 |
| **原因** | `Audio` / `Data` 是可点击的**选项卡**，需点击文字才展开 |
| **解决** | 点 `Audio`（音频）或 `Data`（IQ）选项卡，下方展开文件列表 |

### 坑 4：`$CAP` 路径变量在子目录中失效

| 项目 | 内容 |
| :--- | :--- |
| **现象** | `ffmpeg -i "$CAP.ogg"` 报 `No such file or directory`，但文件确实存在 |
| **原因** | `CAP=phase-b-rf/captures/obs_$OBS` 是**相对路径**，在 `captures/` 子目录执行时查找路径叠加成 `captures/phase-b-rf/captures/...` |
| **解决** | A：回仓库根目录执行；B：用绝对路径；C：子目录内重定义 `CAP=obs_$OBS` |

### 坑 5：METEOR-M2-4 解码报 `Satellite not found`

| 项目 | 内容 |
| :--- | :--- |
| **现象** | `gr_satellites METEOR-M2-4` 与 `gr_satellites 59051` 均报 not found |
| **原因** | 新卫星（2024-02 发射），当前 gr-satellites 版本尚未收录，卫星数据库更新滞后 |
| **解决** | 换官方支持列表（`--list_satellites`）中的老卫星：CUBEBEL-2（NORAD 57175） |

### 坑 6：用 1.024 MHz（IQ 采样率）解音频文件

| 项目 | 内容 |
| :--- | :--- |
| **现象** | 解码无输出或报错 |
| **原因** | 观测 JSON 的 `samp-rate-rx: 1.024e6` 是**射频端 IQ 采样率**；下载的 `.ogg` 是解调后**音频**，已重采样到 48000 Hz |
| **解决** | 音频统一 `--samp_rate 48000`；只有 `.dat` IQ 文件才用原始采样率 |

### 坑 7：不知道如何退出 `less` 分页器

| 项目 | 内容 |
| :--- | :--- |
| **现象** | `gr_satellites --list_satellites \| less` 后卡在分页界面 |
| **原因** | `\| less` 进入分页查看器，需按键退出 |
| **解决** | 按 `q` 退出；`/` 搜索关键词 |

### 坑 8：CUBEBEL-2 找不到遥测格式表

| 项目 | 内容 |
| :--- | :--- |
| **现象** | 搜不到 CUBEBEL-2 的电压/温度字段定义文档 |
| **原因** | 学生卫星项目，遥测格式未公开或未提交公共数据库 |
| **解决** | 暂时放弃字段级解析；换 FUNcube-1 / JY1SAT 等有完整文档的卫星练习（M4 候选） |

## 💡 关键经验

| # | 经验 |
| :--- | :--- |
| 1 | **先确认工具支持**：`gr_satellites --list_satellites` 确认卫星被支持，比盲试省时得多 |
| 2 | **分清数据格式**：SatNOGS 的 `.ogg/.wav` 是**音频**用 48k；`.dat` 是 **IQ** 用 JSON 里的 `samp-rate-rx` |
| 3 | **路径问题先打印变量**：`echo "$CAP"` 看实际值，迅速定位路径叠加 |
| 4 | **善用 `--hexdump` 快速验证**：先看能否出帧头，通路通了再保存完整数据 |
| 5 | **宁可换卫星，不啃无文档的硬骨头**：链路跑通后，优先选有公开遥测格式的卫星练字段解析 |

## 📊 最终工具链

```
SatNOGS 观测
    ↓ (下载 .ogg)
ffmpeg -i .ogg -ar 48000 .wav
    ↓
gr_satellites <NORAD> --wavfile .wav --samp_rate 48000 --kiss_out .kiss
    ↓
python3 tools/kiss_parse.py .kiss → 可读文本（AX.25 头 + payload hexdump）
    ↓
与 SatNOGS 页面 Demoded Data 对比验证
```

## 🤖 AI 协作角色（M0 实录）

全程 AI 副驾，四类角色（对应 [ai-workflow.md](../docs/ai-workflow.md) 的"副驾"侧）：

1. **概念解释**：调制难度排序（BPSK > FSK > GFSK > GMSK）、AX.25 呼号含义、KISS 协议用途、RF/音频采样率区别
2. **故障诊断**：上述 8 坑的根因定位与针对性解法
3. **流程导航**：SatNOGS 页面操作指引、ffmpeg/gr_satellites 命令构建、kiss_parse.py 使用
4. **工程决策**：选调制最简的 CUBEBEL-2、评估投入产出后跳过无文档的字段解析、推荐 M4 转向 FUNcube-1/JY1SAT

另有一层**基础设施**：外文资料阅读走本地翻译链路（沉浸式翻译/Cherry Studio → Ollama → Hy-MT2-1.8B，离线、隐私、Metal 加速），配置详见 [ai-workflow.md](../docs/ai-workflow.md) 工具层小节。
