# IIA Benchmark Simplified

单变量报警优化与联合异常检测的独立 Benchmark 实现仓库。

TEP 联合检测、火电固定规则回放和方法内非 IID 统计搜索已实现。接口与职责见 [设计文档](docs/design.md)。

## 运行已有实验

使用现有 Python 3.11+ 安装本仓库，不要求另建环境。在仓库根目录运行：

```bash
python -m pip install -e '.[test]'
python scripts/verify_data.py
python -m iia_benchmark.runner configs/experiments/tep_multivariate.json
python -m iia_benchmark.runner configs/experiments/power_plant_pressure_fixed.json
python -m iia_benchmark.runner configs/experiments/power_plant_pressure_univariate.json
python -m pytest
python -m pytest -m real_data -k tep
python -m pytest -m real_data -k power_plant
python -m pytest -m real_data
```

默认测试使用小样例；真实数据验收需本地数据，缺失会失败。运行结果在 `experiments/runs/日期/实验名/时间-唯一ID/`，包含配置快照、来源 SHA／代码与依赖版本、预测、指标和参数。可用 `--output-root` 指定其他结果根目录。配置引用按本仓库根目录解析，不依赖执行时的工作目录；从其他目录运行时给实验 JSON 的完整路径。

TEP 用 d00 拟合、d00_te 正常校准、d01_te 评价。火电的 `power_plant_pressure_univariate.json` 做36候选统计设计，`power_plant_pressure_fixed.json` 仅固定规则回放；都经正式 Runner，后者不执行统计分段。安装后也可使用 `iia-benchmark` 命令。

## 代码在哪里

```text
configs/
  experiments/                   # name + dataset/task/model 三引用
  datasets/<id>/dataset.json      # 来源 Adapter、参数及支持的 Task Adapter 配置
    task_adapters/<task>.json     # 目标／分组、用途区间、对齐与断段规则
  tasks/                         # 任务共用参数，不配置指标清单
  models/                        # 方法名、算法和搜索参数
src/iia_benchmark/
  runner.py                      # 公共调度，不认识具体文件或算法
  config/loader.py                # 解析配置引用与组合身份
  data/contracts.py              # 四表 DatasetBundle
  data/registry.py               # 来源及数据集内 Task Adapter 登记
  data/datasets/{tep,power_plant}/
    bundle.py                    # 来源文件 → 四表事实
    task_adapters/               # 四表 → 所属任务标准输入
  tasks/base.py                  # 连续段、Reference、Detection、共同执行／结果入口
  tasks/factory.py               # 任务登记
  tasks/{univariate,multivariate}/
    contracts.py                 # 本任务输入视图与标准 Method 结果
    task.py                      # 校验、调用方法、统一评价及结果组织
    metrics.py                   # 本任务评分／报告
    methods/base.py              # 本任务 Method 抽象接口
    methods/factory.py           # 方法登记
    methods/*.py                 # 完整算法，不把死区单独当 Task
  evaluation/                    # 同口径的逐点、事件纯计算
  results/writer.py               # 统一实验产物
tests/                           # 数据、链路、方法、指标及真实验收
```

数据流：`原始文件 → Dataset Adapter → 四表 → 数据集内 Task Adapter → Task → Method → 标准预测 → Task 评分 → 输出`。四表顶层仅有 `process_values`、`tag_alarm_settings`、`variable_groups`、`status_events`，不承载训练测试角色。

一次实验只引用 `configs/datasets/`、`configs/tasks/`、`configs/models/` 三份配置。来源 Adapter 输出四表，数据集内 Task Adapter 再整理任务输入；划分与变量组选择在对应转换配置中。TEP 评价使用过程级故障参考，不能解释成四个测点各自的故障真值；示例结果用于检验链路，不表示紫金现场效果。

## 怎么接自己的方法或数据

多变量方法实现 [MultivariateMethod](src/iia_benchmark/tasks/multivariate/methods/base.py) 的 `fit(training)`／`predict(evaluation)`，返回 [MultivariatePrediction](src/iia_benchmark/tasks/multivariate/contracts.py)，在同目录 [factory.py](src/iia_benchmark/tasks/multivariate/methods/factory.py) 的 `METHODS` 登记并增加 model JSON，再让 experiment 引用它。正常拟合／可选正常校准视图和无评价真值的检测视图已由 Task 提供；特定方法缺少校准资料时应明确拒绝。Task 统一评分，方法不读取来源文件或评价真值，不自己报告最终 F1/FAR。

默认例子是 [mahalanobis.py](src/iia_benchmark/tasks/multivariate/methods/mahalanobis.py)；独立替代方法和异源 CSV 的接入样例见 [test_pipeline.py](tests/test_pipeline.py)。新来源只在 `src/iia_benchmark/data/datasets/<id>/` 增加四表读取、实际支持的 Task Adapter、dataset 配置及 `data/registry.py` 登记，无需修改已有 Method、Runner 或 Task 评分。不要求补齐所有数据集—任务组合。

数据集中存放在 `data/raw/` 并纳入版本管理。TEP 和火电已有正式 Adapter；SKAB、PRONTO 目前仅准备数据，尚未接入。来源、版本、文件路径和 SHA-256 见 [数据清单](data/manifest.json)，取得仓库后运行 `python scripts/verify_data.py` 校验；用途及来源说明见 [数据管理](data/README.md)。

`.codex/` 中的技能与参考资料随仓库管理。工业报警方法参考 skill 的入口为 [SKILL.md](.codex/skills/industrial-alarm-systems/SKILL.md)。

单变量方法实现 [UnivariateMethod](src/iia_benchmark/tasks/univariate/methods/base.py) 的 `design`／`predict`，返回 [UnivariatePrediction](src/iia_benchmark/tasks/univariate/contracts.py)。Task 固定输出 F1、ADD、MAR、FAR、报警压缩率；无评价依据的项注明原因。火电固定回放不生成统计标签，只报告有依据的报警压缩；非 IID 方法自行生成公开统计参考材料，Task 仍负责统一评分；外部参考即使全部未知也优先保留，不用代理补未知点。

## 输出和指标怎么核对

| 文件 | 内容 |
|---|---|
| `config.snapshot.json` | experiment、dataset、数据集内转换、task、model 的完整解析配置 |
| `manifest.json` | 来源路径／SHA／大小、Git提交与dirty状态、Python和依赖版本、输出位置及完成／失败状态 |
| `predictions.csv` | 每段 run、秒数时间、原始采样序号、预测与参考；联合检测可带分数，单变量带基线状态 |
| `metrics.json` | Task 固定指标、定义、可用性及不可用原因 |
| `details.json` | 参数、参考依据、混淆计数、事件计数和方法声明的诊断材料 |

两任务共用逐点 F1、`FAR=FP/(FP+TN)`、`MAR=FN/(TP+FN)`；未知点不进分母，没有已知异常样本时不报告 F1/MAR。ADD 以秒计已检出且有已知 0→1 起点的事件延迟，另报未检出和左截断数量，不把未检出写零。单变量另报 `alarm_compression_rate=1−候选事件数/基线事件数`，并在 details 用同一参考报告基线四项质量指标；多变量无必填压缩率。

仅工况不等于正常真值。来源 `status_events.event_kind` 可以区分显式参考和工况记录，字段及默认语义见 [四表契约](src/iia_benchmark/data/contracts.py)。只有整段没有外部参考对象时，单变量才可使用方法披露的统计参考。

## 当前规则和实验限制

规则延时以秒表示：连续条件第一次被观测到时开始计时，0秒立即切换；规则不跨连续段。死区模式显式选择 `onset_shift`（高报警H+d发生、低于H解除）或 `recovery_shift`（高报警H发生、低于H-d解除），低报警镜像。火电基线明确假设原150高限即时、无死区，不声称企业提供过这些缺失参数；若用来源设置回放，则所有所需参数和非零死区的实际模式必须已知。

非 IID 实现位于 [non_iid_search.py](src/iia_benchmark/tasks/univariate/methods/non_iid_search.py)，Pettitt/t检验和36候选搜索全在该Method内。搜索优化的是书中连续游程尾部比例，不保证Task逐点FAR/MAR或ADD；最终指标由Task对预测重新计算。当前粗网格示例虽把报警事件从192937压到35，逐点FAR却约93.24%，存在严重报警滞留，不能称为优化成功。它用于验证框架及暴露这种差异，不是历史结果复现或排行榜成绩。参考来自原150阈值与统计分段，非现场确认事故。联合检测只判断是否异常，不需要故障类别，但漏检、F1和延迟仍需要异常评价依据，公共数据不能替代紫金现场验收。
