# 数据管理

四套数据作为来源格式的副本纳入版本管理，原始来源文件保留。运行时才按需转换为四表 DatasetBundle；TEP与火电已有正式两层Adapter，PRONTO/SKAB目前仅准备数据。

```text
data/
├── README.md
├── manifest.json                 # 来源、选用范围、逐文件大小和 SHA-256；纳入 Git
└── raw/                          # 原始数据文件；纳入 Git，预处理不得覆盖
    ├── power_plant/Data_20101.mat
    ├── tep/
    │   ├── data/                 # 原有 44 个 DAT 文件及说明
    │   ├── LICENSE
    │   └── UPSTREAM_README.md
    ├── skab/
    │   ├── data/                 # 原有 35 个 CSV 文件及说明
    │   ├── LICENSE
    │   └── UPSTREAM_README.md
    └── pronto/aligned/           # 原包的对齐及标签数据目录，共 8 个文件
```

## 用途与范围

| 目录 | 计划用途 | 当前副本大小 | 来源 |
|---|---|---:|---|
| `power_plant` | 首批单变量报警优化链路 | 3,904,659 字节 | [IEEE DataPort：Dataset of delay timer design](https://ieee-dataport.org/documents/dataset-delay-timer-design)，Example 3；[论文](https://doi.org/10.1016/j.jprocont.2022.01.002) |
| `tep` | 首批联合异常检测链路 | 26,442,427 字节 | [TEP 上游仓库](https://github.com/jkitchin/tennessee-eastman-profbraatz)，固定版本见清单 |
| `skab` | 后续联合异常检测接入 | 4,440,904 字节 | [SKAB 上游仓库](https://github.com/waico/SKAB)，固定版本见清单 |
| `pronto` | 后续联合异常检测接入 | 14,958,963 字节 | [PRONTO 原始发布](https://zenodo.org/records/1341583)，仅选取 `Pre-processed data/Aligned and labelled alarm and process data/` |

合计 49,746,953 字节（约 47.4 MiB，含随附说明和许可文件）。PRONTO 的约 1.7 GB 压缩包没有复制；PIADE 不在当前任务范围内，也没有复制。

火电副本来自原项目 `.references/Examples/Example3/Data_20101.mat`，保留原 MAT 内容。原配置记录变量 `A`、测点 `X71NAO067`、单位 Pa、采样间隔 1 秒和原高限 150 Pa；这些是当前 Adapter 配置的依据，本清单不承担实验配置职责。

## 校验与同步

在仓库根目录执行：

```bash
python scripts/verify_data.py
```

脚本核对清单内每个文件的大小和 SHA-256，缺失、内容变化或软链接均报错并返回非零退出码。它只检查清单内的文件；额外放入的文件不属于已登记数据。

`data/raw/` 与本说明、清单和校验脚本一同纳入 Git。取得仓库后先运行校验；补充或更新数据时，按照 `manifest.json` 中的 `source_path` 和 `path` 保持来源及目录结构，并更新清单。任务划分和预处理由 `configs/datasets/` 及 Adapter 实现，不修改原始数据。

## 随附条款记录

- TEP、SKAB 已随副本保留上游 `LICENSE` 和 README。SKAB 上游标注 GPL v3.0，不沿用旧项目配置中的 BSD 标记。
- PRONTO 保留原对齐数据说明；旧配置标记 CC BY 4.0，但本次尚未独立确认该标记，应以原发布页为准。
- 火电原文件的再分发条件尚未确认，目前仅作本地副本。

本目录不替数据源变更许可，也不将本地复制等同于已确认可公开发布。
