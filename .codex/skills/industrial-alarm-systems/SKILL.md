---
name: industrial-alarm-systems
description: 查阅 Wang、Hu、Chen 的 Intelligent Industrial Alarm Systems，理解工业报警的问题定义、单变量阈值与延时设计、多变量正常运行区、根因分析、报警洪泛和可视分析。用于按章节或主题查找书中概念、方法及适用条件，核对相关问题定义时使用。
---

# Intelligent Industrial Alarm Systems

**Advanced Analysis and Design Methods**

作者：Jiandong Wang、Wenkai Hu、Tongwen Chen。Springer，2024。
DOI：10.1007/978-981-97-6516-4。原 PDF 433 页，正文六章。
生成：2026-10-18。类型：技术书；深度：查阅型；说明语言：中文，保留英文术语。

原书：[references/source.pdf](references/source.pdf)。页码均明确区分书内印刷页和 PDF 阅读器中的物理页；不同章节偏移不同。

章节配图放在 `references/figures/章节号/`，如第一章的 `references/figures/1/`；目录内 `1.png`、`2.png` 等按该篇 Markdown 中的出现顺序编号，图旁另保留原书图表号及 PDF 页码。远程预览不显示时，可在项目文件树中按编号直接打开 PNG。

图示来源如下；AI 图只作讲解，不作实验结果，提示词保存在同号 `.prompt.txt`，编辑纠正也记录其中。原书图旁保留图号及 PDF 页码。

| 章 | AI 讲解图编号 | 其余图片 |
|---|---|---|
| 1 | 无 | 原书图表 |
| 2 | 1、2、3、7、9、11 | 13 按原书表 2.15 数据重绘，其余来自原书 |
| 3 | 1、2、6、8、11 | 原书图表 |
| 4 | 1、2、5、6 | 原书图表 |
| 5 | 1、2、4、5 | 原书图表 |
| 6 | 1、6 | 原书图表 |

## 使用方式

- 查全书：先读本文件的核心思路和章节索引。
- 查一个主题：按主题索引打开相应章节，需要术语解释时看 glossary。
- 查具体方法：阅读章节内对应的小节及 patterns；精确公式、完整推导和图表回到所注明的 PDF 页。
- 问题超出笔记覆盖时，查原书相应小节；笔记未记载的细节保持待核，不补成作者结论。

## 核心思路

### 把过程变量、报警状态和报警事件分清

过程变量是压力、流量等连续测量；报警变量表示报警与非报警的状态；状态从 0 到 1、从 1 到 0 分别形成发生、解除事件。过程时序、二值报警序列、按时间排序的事件表适合回答不同问题，转换时要保留时间和语义。

书中把报警变量的生命周期分成配置、设计、移除三个研究阶段：配置决定哪些过程变量需要报警及其优先级；设计决定报警生成机制和参数；移除涉及报警发生后查明原因与采取行动。第 1 章的这一划分不同于把所有工作统称为异常检测。

### 单变量关注报警机制与参数设计

第 2 章面对一支过程变量及其报警机制。阈值、延时、死区是设计对象；报警状态是配置应用于数据后的输出。当前阈值是已有工艺参考或设计起点，并不意味着所有逐点越限都是独立确认的真实异常。

§2.1 对 IID 过程用分布与延时器模型计算 FAR、MAR、AAD，先筛满足要求的候选，再按偏好或加权分数选择 H、n。§2.1.3 在两类分布未知时，以均值变点、段均值检验归类，再把同类段原始点合并估计一个 q(x)、一个 p(x)。参考构造有均值差异与工艺先验等条件。

相邻测量有关联时，单点概率不足以确定连续情况。§2.2 先数全部连续越限／回落长度，再估计达到候选 n 的原始段比例，选择两项最接近期望值的 H、n；目标函数不含 AAD。§2.3 用归一化幅度与持续时间判断死区适用性，再在正常历史上选宽度。§2.4 根据数值分区及相邻转移估计概率和时间，选择区间下边界作为新阈值；有样本量与转移模型条件。四节不是必须顺序执行的四个步骤。

### 同名指标要连同定义一起读

§2.1 的 FAR/MAR 是给定正常/异常状态下的报警或不报警概率；§2.2 同名的 ratio 按达到延时长度的原始干扰事件比例定义；§2.3 另用新旧误报警事件数之比。它们不能因名字相同就混成同一个分数。AAD 描述异常发生后报警所需等待时间，不能用配置的 delay 参数替代。

### 多变量利用关系，而不只是把单点阈值堆起来

第 3 章有两类通用特征：联合正常运行区（NOZ）和变量变化方向；还有电泵、冷凝器的专用物理特征。§3.1 从物理意义明确的相关变量及正常历史建立 NOZ，并给出每支变量随其他变量变化的动态上下限；联合报警来自对正常关系的违反。

NOZ 历史正常数据应能代表后续正常分布。书中用 β 控制正常点排除比例，有分布一致等前提；不能据此认为后续任意工况的实际误报率都等于 β。变化方向法还需要已知正常方向关系，设备专用法需要对应物理量和模型。

### 建信息流图与定位当前根因是相关的两件事

第 4 章先用历史报警或过程序列推断信息流路径，缩小根因搜索范围；再讨论当前报警的根因推断。NTE/NDTE 面向二值报警及随机发生延迟，IGTE/IGDTE 用信息粒和聚类处理过程序列。递归 Bayesian network 面向已知候选原因的特定结构；PLR 趋势方法面向关键变量及其影响变量。相关性图、显著信息流边、当前事件根因不能直接互换。

### 洪泛包含检测、相似、模式和预测四种问题

第 5 章的输入已经是报警状态或事件。Criterion C 关注新出现的报警变量，减轻重复抖动与长期滞留报警对计数的影响。局部对齐比较有顺序的洪泛事件；闭合频繁模式比较报警集合；最大熵方法根据已发生的前缀预测下一报警。集合、序列和前缀的区别决定保留哪些信息。

### 可视分析让报警负担和关系可追查

第 6 章从 A&E 日志及相关过程数据出发，分别展示整体报警表现、报警与响应关系、洪泛模式。计数、持续时间、发生与解除等含义应先明确，再选择气泡图、treemap、HDAP、事件流或相似性图。图形帮助解释数据和分析结果，不能自行确证异常或因果。

## 章节索引

| 章 | 查阅文件 | 主要内容 | 书页 / PDF 页 |
|---|---|---|---|
| 1 | [工业报警系统概述](chapters/ch01-overview.md) | 基本对象、报警过载、生命周期与研究问题 | 1–47 / 13–59 |
| 2 | [单变量报警设计](chapters/ch02-univariate-alarm-design.md) | IID、Non-IID、Deadband、Alarm Probability Plot | 49–127 / 60–138 |
| 3 | [多变量报警设计](chapters/ch03-multivariate-alarm-design.md) | Convex/Search-cone NOZ、变化方向、电泵、冷凝器 | 129–220 / 139–230 |
| 4 | [根因分析](chapters/ch04-root-cause-analysis.md) | NTE/NDTE、IGTE/IGDTE、Bayesian network、PLR | 221–301 / 231–311 |
| 5 | [报警洪泛](chapters/ch05-alarm-floods.md) | 检测、序列对齐、闭合模式、下一报警预测 | 303–379 / 312–388 |
| 6 | [可视分析](chapters/ch06-visual-analytics.md) | KPI、bad actor、关系、响应、洪泛可视化 | 381–420 / 389–428 |

## 主题索引

- A&E、alarm state、报警发生/解除 → ch01、ch06；[术语表](glossary.md)。
- AAD、FAR、MAR、指标含义 → ch02；冷凝器的不确定性指标另见 ch03 §3.4。
- Alarm configuration / design / removal、八个研究问题 → ch01。
- Alarm Probability Plot、Pka/Tka/Pam/Tam → ch02 §2.4。
- Bayesian：持续时间与死区估计 → ch02；模型估计 → ch03；根因后验 → ch04。
- Chattering、long-standing、bad actor → ch01、ch05、ch06。
- Convex hull、Quickhull、dynamic alarm thresholds、NOZ、search cone → ch03 §3.1。
- Deadband Index、死区宽度 → ch02 §2.3。
- IID、Markov chain、on/off delay → ch02 §2.1。
- IGTE、IGDTE、information granulation、OPTICS → ch04 §4.2。
- NTE、NDTE、surrogate significance test → ch04 §4.1。
- Non-IID、alarm duration / interval、Bayesian interval → ch02 §2.2。
- Pettitt、T-test、KDE、正常/异常分段 → ch02 §2.1.3。
- PLR、qualitative trend、time-varying contribution → ch04 §4.4。
- 泵模型、参数变化率 → ch03 §3.3；冷凝器物理模型 → ch03 §3.4。
- 洪泛 Criterion C → ch05 §5.1；SW/BLAST 对齐 → §5.2；CHARM → §5.3；maximum entropy → §5.4。
- 气泡图、treemap、HDAP、雷达图、动态 3D → ch06 §6.2。
- 相关图、响应工作流、event flow → ch06 §6.3；burst / similarity / spiral → §6.4。

## 支持文件

- [glossary.md](glossary.md)：中英文术语及章节位置。
- [patterns.md](patterns.md)：方法步骤与取舍，按主题查阅。
- [cheatsheet.md](cheatsheet.md)：条件判断和方法选择速查。

## 来源与范围

本 Skill 是原书的中文查阅提炼，保留作者章节关系；紫金任务约定、仓库代码状态、公开数据实验分数不作为书中结论写入。

本次用 book-to-skill 的 technical 模式运行；Docling 不可用，实际回退 pdftotext，并参照已有逐页文本定位。文字提取未完整理解书内图像，公式上下标、求和边界和表格须以 PDF 为准。已回看 §2.1 的评分数值及 §2.2 的公式方向疑点，核对说明留在 ch02，不把疑点数值作为已验证结果。

附带 PDF 的 SHA-256：`d002db25abf162a7afcd06dfe08953ee38e37e708ff425120cabf326fac2e4b0`。PDF 为本地参考来源；本 Skill 与源文件一并保留在当前项目本地，不作为公开发布产物。
