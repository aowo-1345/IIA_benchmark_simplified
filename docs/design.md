# IIA Benchmark：单变量与联合异常检测 Pipeline 结构草案

状态：讨论草案，2026-10-18。本文件描述目标结构；目录树中的新文件尚未实现。

## 目标与边界

从实验配置启动，以同一条主链路运行两个任务：首版用火电压差数据检查单变量报警优化，用 TEP 检查联合异常检测；PRONTO、SKAB 和未来的紫金数据按同一接入约定扩展。两类实验不能互换数据集来充当任务验证。

```text
实验配置 → 解析 dataset / task / model；由 dataset + task 找到已登记的转换配置
         → Dataset Adapter → 四表 DatasetBundle
         → 该数据集的 Task Adapter → 对应 Task 的标准输入
         → Task（调用对应 Method → 评价预测）
         → TaskResult（预测 + 该任务的指标）→ 结果文件
```

- `univariate_detection`（单变量报警优化）：选定测点与报警方向；给定原有报警规则时回放基线，并在离线设计数据中搜索阈值、延时、死区的组合，在独立数据上比较。固定参数也是同一规则方法的一种配置。
- `multivariate_detection`（联合异常检测）：选定工艺变量组及工况，学习正常状态，输出该组是否异常；不区分异常类别。
- 根因分析、报警洪泛和可视化保留在仓库原有模块中，不进入这条最小 Pipeline。
- 四张现场表到接入文件的转换暂不实现；Benchmark 侧保留读取转换后数据的 Adapter 入口。

**公共数据格式只表达四类数据事实。**它对应数据契约的四张逻辑表：过程值、现有报警设置、变量分组、工况及事件。各时段的实验用途、目标测点或变量组及对齐规则由数据集下对应 Task 的转换配置给出，不进入公共数据对象；来源审计写入结果文件，也不作为第五张业务表。

## 目标文件树

沿用现有 `configs/` 和 `src/iia_benchmark/`。以下是这两个任务需要的最小组织；旧任务的文件可以继续存在。

```text
configs/
├── experiments/                  # 一次实验引用 dataset / task / model
│   ├── power_plant_pressure_univariate.json
│   └── tep_multivariate.json
├── datasets/                     # 每个数据集包含四表转换和支持的 Task 转换
│   ├── power_plant/
│   │   ├── dataset.json
│   │   └── task_adapters/univariate_detection.json
│   └── tep/
│       ├── dataset.json
│       └── task_adapters/multivariate_detection.json
├── tasks/                        # 任务类型及评价约定；不重复列指标
│   ├── univariate_detection.json
│   └── multivariate_detection.json
└── models/                       # 方法名及其参数；沿用现有配置目录名

src/iia_benchmark/
├── runner.py                     # 实验入口；加载引用、分派 Task、写结果
├── config/loader.py              # 配置读取、引用解析、兼容性检查
├── data/
│   ├── contracts.py              # DatasetBundle：任务无关的四表事实
│   ├── registry.py               # 显式登记 Bundle Adapter 与数据集内 Task Adapter
│   ├── common/                   # 共用的连续段切分、对齐和质量检查
│   └── datasets/
│       ├── power_plant/
│       │   ├── bundle.py          # MAT → 完整四表
│       │   └── task_adapters/
│       │       └── univariate.py # 四表 → UnivariateTaskInput
│       └── tep/
│           ├── bundle.py          # TEP → 完整四表
│           └── task_adapters/
│               └── multivariate.py # 四表 → MultivariateTaskInput
├── tasks/
│   ├── base.py                   # BaseTask：Runner 可调用的共同入口
│   ├── factory.py                # task kind → 具体 Task
│   ├── univariate/
│   │   ├── contracts.py          # 任务输入、标准预测、固定结果类型
│   │   ├── task.py               # 校验任务输入、调用方法、评价预测
│   │   ├── metrics.py            # 本任务的指标口径与结果组装
│   │   └── methods/
│   │       ├── base.py           # UnivariateMethod 抽象接口
│   │       ├── factory.py        # model.method → 本任务的方法实现
│   │       └── threshold_rule.py # 阈值 + 延时 + 死区的完整规则及搜索
│   └── multivariate/
│       ├── contracts.py          # 组输入、标准预测、固定结果类型
│       ├── task.py               # 校验任务输入、调用方法、评价预测
│       ├── metrics.py            # 本任务的指标口径与结果组装
│       └── methods/
│           ├── base.py           # MultivariateMethod 抽象接口
│           ├── factory.py
│           └── mahalanobis.py    # 首个可替换的联合检测方法
├── evaluation/
│   ├── binary.py                 # 仅复用同口径的逐点混淆矩阵计算
│   └── events.py                 # 按 run 提取/匹配事件和计算延迟
└── results/writer.py             # 保存配置、预测、指标与来源记录
```

`threshold_rule.py` 是一个完整方法。阈值、延时、死区是它的可组合参数，不分别作为三种异常检测方法。每个 Method 实现所属 Task 的抽象接口；工厂按 `model.method` 构造实现，Method 本身不实现工厂方法。以后接入另一种完整算法，在所属 Task 的 `methods/` 中实现接口、加入工厂并提供 model 配置，不改 Dataset Adapter 或该 Task 的指标定义。

每个 `datasets/<id>/dataset.json` 用 `adapter` 和 `adapter_config` 说明原始文件、字段、时间、质量、已有报警设置及来源标签如何变成完整四表；`task_adapters` 只登记本数据集支持的 Task 类型及其转换配置路径。转换配置位于同一数据集目录下，规定该 Task 的目标、设计/拟合/校准/评价时段和数据整理规则。配置中的原始数据路径相对项目根目录，`task_adapters` 中的配置路径相对 `dataset.json`。`data.registry` 把配置里的 Adapter ID 映射到显式实现，Runner 不直接拼 Python 模块名。Runner 通过实验引用的 dataset 与 task kind 查找并校验这一登记项，将解析后的转换配置一并写入结果快照；没有登记就明确报不支持。只为实际支持的数据集—Task 组合登记转换；相同处理可复用 `data/common/`，无须按所有数据集与任务的笛卡尔积写代码。首版每个组合只登记一份转换配置，不增设独立的 `configs/splits/` 或顶层 `configs/task_adapters/`。

## Adapter 输出的标准数据格式

`DatasetBundle` 是各来源 Adapter 的共同输出，顶层**只有四个字段**，名称与 09-02 数据契约的四张逻辑表一致：

| 字段 | 内容 |
|---|---|
| `process_values` | `timestamp, run_id, tag_id, value, quality_flag`；按原始采样保留时间和值，包括无效点及其质量标记，不预先拼成 `N×D`。 |
| `tag_alarm_settings` | Tag 元数据和现有阈值、方向、延时、死区；来源没有现有设置时为空表。 |
| `variable_groups` | 组与成员 Tag 的关系；来源没有预声明组时为空表。 |
| `status_events` | 工况、可信正常区间及可选事件/来源标签；缺少相应记录时为空表，不编造确认事故。 |

```text
DatasetBundle(
    process_values=...,
    tag_alarm_settings=...,
    variable_groups=...,
    status_events=...,
)
```

设计/拟合、校准、评价的用途划分留在 `datasets/<id>/task_adapters/<task>.json`；数据集的 Task Adapter 按 Bundle 中的 run ID、时间或采样序号验证边界，输出该 Task 的标准输入。来源文件、校验值、四表转换版本及 Task Adapter 配置写入运行结果的 `manifest.json`，都不是 DatasetBundle 的第五个字段。

这些是四类逻辑数据，不要求公开数据真的存在四个 CSV 文件；TEP、PRONTO、SKAB 和火电压差的 Adapter 只填来源实际具备的表/行。Adapter 做字段、时间及质量语义转换，不为凑齐指标生成异常标签。每张表的行可以由类定义语义，但大时序的内存表示不必强制为每点一个 Python 对象。当前火电压差文件只在相邻工作树中，尚未接入此工作树。

火电压差 Example 3 是单个 Tag `X71NAO067` 的时序，已有高报警阈值为 150 Pa、采样周期 1 秒；原论文示例只验证固定阈值下的 Delay 设计。阈值×Delay 联合搜索使用 Pettitt+t 检验建立正常/异常统计代理，**不是**原始数据自带的异常真值，也不是论文原设定复现。该数据可以检查单变量方法迁移和完整执行链，代理 FAR/MAR 必须单独标注，真实 F1/ADD 不可计算。TEP、PRONTO、SKAB 的过程级标签不能直接当成单测点异常真值，当前只纳入联合检测的首批数据集。

### 数据集到 Task 的标准输入

每个 Task 在自己的 `contracts.py` 中定义输入类型；每个数据集在 `task_adapters/` 中实现已登记的转换。两类输入都保留 `run_id`、时间、源行对应关系和连续段边界，使预测能够回写、报警状态不会跨无效点或 run 延续。数据集的 Task Adapter 只接收四表 Bundle 与本组合的转换配置；来源文件已由 `bundle.py` 读取，它不再读取 MAT、CSV 等原始文件，也不拟合模型或计算最终指标。

| Task 输入 | 必需内容 | 允许缺失并明确记录 |
|---|---|---|
| `UnivariateTaskInput` | 目标报警通道（Tag、工况、方向）；一维连续设计段和评价段；已有阈值及来源。 | 原有 Delay/Deadband、设计段参考、评价段独立异常真值；回放缺少的原有参数需要明示假设。 |
| `MultivariateTaskInput` | 目标变量组与固定列序；对齐后的正常拟合段和待检测评价段；拟合段正常依据。 | 独立正常校准段、评价段异常真值；具体 Method 若要求校准段，由 Task 在调用前验证。 |

已知正常、已知异常与未知必须区分；没有标签不能默认为正常。标签还需保留来源及作用范围，例如 TEP 的过程级故障不等于组内每个测点的独立故障。Task Adapter 整理可用的参考和评价依据，Task 保管评价真值，向 Method 仅传递设计/拟合允许的信息与无真值的评价视图。方法内部特有的标准化和特征构造由 Method 自己完成。现有 `ProcessSeries(N×D)` 可作为任务内矩阵输入的参考，不是四表输出。

**火电压差这条单变量链路。**`power_plant/bundle.py` 读取 MAT 中的 `A`，以采样序号对应的相对秒数生成同一 `run_id` 下的 `process_values`；9 个哨兵值仍保留并标成无效。已有高限 150 Pa 成为 `tag_alarm_settings` 的一行；没有提供的 Delay/Deadband 保持缺失，不冒充现场配置。`variable_groups` 为空；联合搜索没有独立异常真值，`status_events` 不由 Adapter 伪造事故。`power_plant/task_adapters/univariate.py` 根据组合配置选 `X71NAO067`，把 `[0,484975)` 作为设计段、`[484984,2678400)` 作为评价段，遇无效点断开连续段，并输出 `UnivariateTaskInput`。Task 使用 Task 配置指定的 Pettitt+t 代理参考规则建立统计参考；候选方法只用设计段搜索阈值×Delay，冻结后回放评价段。相对固定 150 Pa 即时阈值规则统计报警事件变化时，必须把“即时”作为明确的基线假设，而不是现场原有 Delay；代理 FAR/MAR 单独标注，没有独立故障真值时不输出真实 F1/ADD。

**TEP 这条联合检测链路。**`tep/bundle.py` 将 TEP 文件中的每列展开为 `process_values` 行；`tag_alarm_settings` 为空，预先声明的四测点组进入 `variable_groups`；d00、d00_te 的来源正常区间和 d01_te 从第 160 个采样点起的来源故障区间进入 `status_events`，后者不能写成现场确认事故。`tep/task_adapters/multivariate.py` 根据组合配置选组，按时间对齐成 `N×4`，把 d00、d00_te、d01_te 分别整理为正常拟合、正常校准和评价段，输出 `MultivariateTaskInput`。马氏距离 Method 拟合、校准阈值并对评价段输出逐点分数和异常状态；Task 再用来源故障区间形成评价真值，计算 F1、FAR、MAR、ADD。它们是相对 TEP **过程级故障标签**的指标，不能称为该四测点组的独立故障真值；标签不进入 Method 的拟合或阈值校准。

## 每层对外提供什么

| 层 | 对外接口（概念） | 内部负责 |
|---|---|---|
| `config` | `load_experiment(path) → ExperimentPlan` | 读取实验名和 dataset、task、model 三个引用；按 dataset 的登记表解析并校验 Task Adapter；校验 task 与 method 的匹配关系；保留全部配置快照。 |
| `data.datasets.<id>.bundle` | `load_bundle(adapter_config) → DatasetBundle` | 读取具体来源并翻译为四张逻辑表；保留 run、时间、质量、已有规则、变量组和来源标签。 |
| `data.contracts` | `DatasetBundle` | 仅定义四表的任务无关数据表示；不承载划分、来源审计、预测或训练/评价角色。 |
| `data.registry` | `get_bundle_adapter(id)`、`get_task_adapter(id)` | 将配置 ID 映射到已登记实现，并核对目标 Task 输入类型；Runner 不按文件名动态导入代码。 |
| `data.datasets.<id>.task_adapters.<task>` | `prepare(bundle, adapter_config) → 该 Task 的标准输入` | 按已登记的组合配置选目标、验证划分、处理质量/连续性/对齐并标明参考依据；不读原始文件、不拟合方法。 |
| `tasks.factory` | `create_task(task_spec.kind) → BaseTask` | 根据实验引用的 task 配置创建单变量或联合检测 Task；`BaseTask.run(...) → TaskResult` 是 Runner 唯一依赖的任务入口。 |
| `tasks.univariate` | `run(UnivariateTaskInput, task_spec, model_spec) → TaskResult` | 校验单变量任务前提及基线语义；通过本任务的方法工厂创建 Method、调用预测并按本任务口径评价。 |
| `tasks.multivariate` | `run(MultivariateTaskInput, task_spec, model_spec) → TaskResult` | 校验正常拟合/校准和标签作用范围；调用方法；计算本任务指标并返回。 |
| 各 Task 的 `methods.factory` | `create_method(model_spec) → 该 Task 的 Method 抽象类型` | 校验方法属于此任务，并按配置构造实现；工厂负责选择，不承载算法。 |
| 各 Task 的 `methods` | 实现所属 Task 的抽象接口，返回该 Task 的标准预测 | 自己的拟合、设计、参数搜索和预测；算法特有的数据变换封装在方法内部，不读原始数据路径或计算最终报告指标。 |
| `evaluation` | 逐点计数、事件提取/匹配等纯函数 | 只复用已确认口径相同的计算；不决定标签来源、指标可用性或 Task 的最终报告字段。 |
| `results.writer` | `write(TaskResult, ExperimentPlan)` | 按运行日期、实验名和唯一运行 ID 创建目录；保存预测、参数、指标可用性和数据/配置来源。 |

这里的共同入口是 `BaseTask.run`；两类 Task **不强行共用同一个输入对象、Method 抽象类或训练步骤**。数据集侧 Task Adapter 负责将同一个四表协议转换为各 Task 自己定义的输入类型；Task 无须知道 MAT/TEP 文件布局。工厂与抽象接口各有职责：工厂解决“配置选哪个实现”，抽象类约束“该实现接收什么、返回什么”。Runner 只知道标准转换入口、Task 入口及结果。

### Task 与 Method 之间的约定

```text
单变量数据集 Task Adapter：DatasetBundle + 组合转换配置
  → UnivariateTaskInput（目标、连续设计/评价段、已有规则、参考及其可用性）
单变量 Task：UnivariateTaskInput + Task 配置 + Model 配置
  → UnivariateDesignView（仅设计段可用的参考；评价真值留在 Task）
  → 本 Task 的工厂创建 UnivariateMethod
  → UnivariateMethod.design(设计视图) → 冻结方法状态/报警规则
  → UnivariateMethod.predict(无真值的评价视图) → UnivariatePrediction
  → 单变量 Task 评价预测并输出 TaskResult

联合检测数据集 Task Adapter：DatasetBundle + 组合转换配置
  → MultivariateTaskInput（固定变量组、正常拟合/可选校准段、评价段及参考）
联合检测 Task：MultivariateTaskInput + Task 配置 + Model 配置
  → MultivariateTrainingView（不含评价真值的正常拟合段、可用校准段）
  → 本 Task 的工厂创建 MultivariateMethod
  → MultivariateMethod.fit(正常拟合段、正常校准段) → 冻结检测器
  → MultivariateMethod.predict(无真值的评价矩阵) → MultivariatePrediction
  → 联合检测 Task 评价预测并输出 TaskResult
```

两个抽象接口可以先按以下最小签名落地；`design` / `fit` 会改变方法实例的已拟合状态，调用后方可 `predict`，因此无须每个实现再暴露一个“工厂方法”：

```python
class UnivariateMethod(ABC):
    @abstractmethod
    def design(self, data: UnivariateDesignView) -> None: ...

    @abstractmethod
    def predict(self, data: UnivariateEvaluationView) -> UnivariatePrediction: ...

class MultivariateMethod(ABC):
    @abstractmethod
    def fit(self, data: MultivariateTrainingView) -> None: ...

    @abstractmethod
    def predict(self, data: MultivariateEvaluationView) -> MultivariatePrediction: ...
```

`UnivariatePrediction` 必有 `run_id、timestamps[N]、alarm_state[N]、selected_parameters`；`MultivariatePrediction` 必有 `run_id、timestamps[N]、abnormal_state[N]`，可带 `score[N]` 和判定界限。每个标准预测都要验证长度、时间顺序及 run 对应关系；分数不是所有方法的必需输出。Method 可以提供参数和诊断信息，但不输出自己定义的最终 F1/FAR 等报告指标。Task 对所有同类方法提供相同的**任务数据语义**，特定方法需要的标准化、统计量或内部特征由该方法完成。评价标签由 Task 留到评测阶段，不随评价输入送给方法。单变量的当前规则可以由同一 `threshold_rule` 方法以固定参数回放，候选规则只在设计段搜索。

### 指标的共用边界

单变量 Task 的固定结果字段是 F1、ADD、MAR、FAR 和报警压缩率；联合检测 Task 的固定结果字段是 F1、ADD、MAR、FAR。Task 自己确定评价标签的来源、作用范围、有效点及 run/事件边界；各 Task 的 `metrics.py` 调用 `evaluation/binary.py` 或 `evaluation/events.py` 的纯函数，组装约定的结果。`configs/tasks/` 不重复列指标清单，也无须为新 Pipeline 设置独立的 `configs/metrics/`。

只有**定义、分母、时间单位和事件匹配规则完全相同**的指标才共用底层函数。例如两个任务都采用逐点 F1，可复用一次混淆矩阵实现；若一个 FAR 是正常采样点中的误报比例，另一个是按正常时段计的误报事件率，必须分别命名和实现，不能因缩写相同就合并。ADD 要明确事件起点、跨 run 边界及未检出事件的处理。单变量报警压缩率由其 Task 比较基线与候选的报警事件数，联合检测无此必填字段。

结果中的每个固定字段要么有数值及口径信息，要么明确 `unavailable` 及原因；缺少独立真值时不把空值写成零。火电压差的 Pettitt+t 参考所算 FAR/MAR 必须以 `proxy_*` 单独报告，不能混入真实 F1/ADD；TEP 联合检测的标签作用范围应写明为过程级故障。Method 的调参只能使用设计/拟合/校准段允许的信息，评价真值由 Task 在预测完成后才取出用于计算指标。

## 实验配置如何启动这条链路

实验配置只写实验名，以及对 `datasets / tasks / models` 三类配置的引用；它自己构成第四类。Runner 从 dataset 的 `task_adapters[task.kind]` 解析该数据集到该 Task 的转换配置，路径相对 `dataset.json` 所在目录，不靠文件名猜测，也不要求实验配置重复写第四个引用。Task 配置只写该任务通用的处理/评价参数，Model 配置写算法与搜索参数；数据集—Task 组合特有的目标、时段用途和整理规则写在组合转换配置。下面是**目标格式示意，不是当前 Runner 已支持的配置**。火电原始文件目前只在相邻工作树，正式接入此工作树时要核对路径。

`configs/experiments/power_plant_pressure_univariate.json`：

```json
{
  "name": "power_plant_pressure_univariate",
  "dataset": "configs/datasets/power_plant/dataset.json",
  "task": "configs/tasks/univariate_detection.json",
  "model": "configs/models/non_iid_threshold_delay_search.json"
}
```

`configs/datasets/power_plant/dataset.json`：

```json
{
  "id": "power_plant",
  "adapter": "power_plant.bundle",
  "adapter_config": {
    "path": ".references/Examples/Example3/Data_20101.mat",
    "variable": "A",
    "run_id": "example3",
    "tag_id": "X71NAO067",
    "sample_period_seconds": 1,
    "alarm_setting": {"direction": "high", "threshold": 150.0},
    "invalid_below": -1000.0
  },
  "task_adapters": {
    "univariate_detection": "task_adapters/univariate_detection.json"
  }
}
```

`configs/datasets/power_plant/task_adapters/univariate_detection.json`：

```json
{
  "dataset_id": "power_plant",
  "task_kind": "univariate_detection",
  "adapter": "power_plant.univariate",
  "adapter_config": {
    "tag_id": "X71NAO067",
    "direction": "high",
    "roles": {
      "design": {"run_id": "example3", "start_index": 0, "stop_index": 484975},
      "evaluation": {"run_id": "example3", "start_index": 484984, "stop_index": 2678400}
    },
    "invalid_policy": "break_continuity",
    "minimum_segment_samples": 3600,
    "baseline_replay": "declared_instant_threshold_assumption"
  }
}
```

Runner 应校验转换配置的 `dataset_id` 和 `task_kind` 与实验所选配置一致，并验证目标 Tag、run 和索引确实存在。`baseline_replay` 明确说明本示例用已有 150 Pa 阈值构造即时报警比较基线；它不声称来源给过原始 Delay/Deadband。

`configs/tasks/univariate_detection.json`：

```json
{
  "kind": "univariate_detection",
  "parameters": {
    "reference_policy": "pettitt_ttest_proxy",
    "pettitt_alpha": 0.05,
    "ttest_beta": 0.05,
    "event_merge_gap_samples": 0
  }
}
```

`configs/models/non_iid_threshold_delay_search.json`：

```json
{
  "method": "non_iid_threshold_delay_search",
  "parameters": {
    "threshold_relative_range": 0.05,
    "threshold_step": 0.5,
    "maximum_delay": 512,
    "target_far": 0.05,
    "target_mar": 0.05
  }
}
```

这份 model JSON 仍是结构示意，尚未写全比较符号（`>` 或 `>=`）、启动/解除延时、死区状态转移、搜索目标的精确定义；现有单变量实现对这些细节并不一致，必须在方法协议和配置中固定后才能称为可执行配置。火电 MAT 的相对路径在当前交付工作树不存在，文件目前只在相邻工作树，不能直接照抄此示意运行。

TEP 的实验也只引用三份配置，Dataset Adapter 保留 52 个原始变量并把预声明的四测点组写入 `variable_groups`。以下两个 JSON 与紧随其后的组合转换配置配套；d01_te 从第 160 个采样点起的来源故障标签由 TEP 的 `bundle.py` 转成四表事件，不写在转换配置中当成划分规则。

`configs/experiments/tep_multivariate.json`：

```json
{
  "name": "tep_multivariate",
  "dataset": "configs/datasets/tep/dataset.json",
  "task": "configs/tasks/multivariate_detection.json",
  "model": "configs/models/mahalanobis.json"
}
```

`configs/datasets/tep/dataset.json`：

```json
{
  "id": "tep",
  "adapter": "tep.bundle",
  "adapter_config": {
    "sample_period_seconds": 180,
    "runs": [
      {"run_id": "d00", "path": "data/public_datasets/tep_classic/data/d00.dat", "source_status": "normal"},
      {"run_id": "d00_te", "path": "data/public_datasets/tep_classic/data/d00_te.dat", "source_status": "normal"},
      {"run_id": "d01_te", "path": "data/public_datasets/tep_classic/data/d01_te.dat", "fault_start_zero_based": 160, "label_scope": "process"}
    ],
    "variable_groups": [
      {"group_id": "tep_feed", "tag_ids": ["XMEAS_01", "XMEAS_02", "XMEAS_03", "XMEAS_04"]}
    ]
  },
  "task_adapters": {
    "multivariate_detection": "task_adapters/multivariate_detection.json"
  }
}
```

`configs/datasets/tep/task_adapters/multivariate_detection.json`：

```json
{
  "dataset_id": "tep",
  "task_kind": "multivariate_detection",
  "adapter": "tep.multivariate",
  "adapter_config": {
    "group_id": "tep_feed",
    "roles": {
      "fit": ["d00"],
      "calibration": ["d00_te"],
      "evaluation": ["d01_te"]
    },
    "alignment": {"mode": "exact_timestamp", "missing": "reject"}
  }
}
```

以 TEP 的四测点马氏距离实验为例，**新 Runner 的目标调用顺序**是：

| 步骤 | 输入 | 输出与下一步 |
|---|---|---|
| 配置加载 | `configs/experiments/tep_multivariate.json` | 实验名及 dataset、task、model 三份引用；由 dataset 的登记表找到 TEP→联合检测转换配置，校验数据集、任务和方法兼容性。 |
| Dataset Adapter | TEP `dataset.json` 的 `adapter_config`，含 d00/d00_te/d01_te 文件、180 秒采样周期、预声明测点组及来源故障事件 | 四表 `DatasetBundle`；三份文件共 `125840` 条过程值逻辑记录（`(500+960+960)×52`），不先选成四列。 |
| TEP→联合检测 Adapter | Bundle、TEP 的 `task_adapters/multivariate_detection.json` | 取四测点组并按 run 和时间对齐，得到 `MultivariateTaskInput`：`fit[500,4]`、`calibration[960,4]`、`evaluation[960,4]`，保留评价标签及其过程级作用范围。 |
| Task | `MultivariateTaskInput`、task/model 配置 | 校验输入，向 Method 提供无评价真值的矩阵视图；评价标签由 Task 留待预测完成后使用。 |
| Method | 无评价真值的三个矩阵及 model 参数 | 拟合正常模型、独立正常段校准、对评价段返回 `abnormal_state[960]`，可选 `score[960]`。 |
| Task 评价 | 标准预测、Task 保管的过程级标签、时间及 run 边界 | 返回固定指标及标签范围、指标可用性；预测与指标组成 `TaskResult`。 |
| Runner 写出 | `TaskResult` 和配置/数据来源 | 日期/实验名/唯一运行号下的配置快照、预测、指标、来源记录。 |

单变量火电实验复用“配置 → Dataset Adapter 四表 → 本数据集的 Task Adapter → Task → Method → Task 指标 → Runner 写出”的外层调用；火电→单变量 Adapter 选一个 Tag，设计段可携带明确标识的统计代理供方法搜索，评价段真值仍不传给 Method；没有独立真值时真实 F1/ADD 留空。

火电 Bundle Adapter 把现有报警设置转换为 `tag_alarm_settings` 的一行；其单变量 Task Adapter 按组合配置取得目标 Tag 和现有阈值。TEP 联合检测的 `variable_groups` 来源可在 TEP 的 `adapter_config` 内预声明；紫金现场数据到来后则由其 Bundle Adapter 读取 `variable_groups.csv`。各数据集的联合检测 Task Adapter 只消费四表，不关心这些组最初来自内嵌列表还是文件。固定指标、不可用指标的原因和输出路径由 Task / Runner 管理，不再进入实验配置。

输出位置遵循统一默认约定：Runner 使用项目时区（当前为 Asia/Shanghai）的运行日期，将 `name` 与日期组成可读运行名；默认根目录为 `experiments/runs/`，生成 `experiments/runs/YYYY-MM-DD/<name>/<HHMMSS-唯一后缀>/`。例如同一天两次执行上面的实验会得到两个独立目录：

```text
experiments/runs/2026-10-18/power_plant_pressure_univariate/
├── 093012-a1b2c3/
│   ├── manifest.json         # 完整运行 ID、时间、数据/配置来源
│   ├── config.snapshot.json  # 本次解析后的 dataset/组合转换/task/model 配置
│   ├── metrics.json
│   └── predictions.csv
└── 104521-d4e5f6/
```

`name` 只写稳定的实验名；日期由 Runner 生成，避免下次运行时忘记改日期。Runner 创建新目录，不覆盖已有结果。普通实验无须配置输出路径；需要将结果放到其他磁盘时，由可选的 `--output-root` 覆盖默认根目录，并将实际路径记录在 `manifest.json`。这不改变 experiment JSON 的职责。

因此，新增数据集需要生成四表的 Bundle Adapter、dataset 配置，以及它实际支持的各 Task 的转换实现和组合配置；新增检测方法主要增加该 Task 内的 Method 和 model 配置；新增任务需要定义其标准输入、预测约定与指标输出，已有数据集要支持这个新 Task 时再登记相应转换。

当前旧实验仍要求 `metrics` 字段并读取 `configs/metrics/*.json`。在现有 T1/T2 路径中，这些文件主要是指标清单和文字说明，任务函数没有收到这份配置；新 Pipeline 的配置版本应允许省略该字段。旧实验配置与旧入口继续按原格式读取，迁移时不批量删除已有文件。

当前旧实验还引用 `configs/splits/*.json`，其中部分内容和 dataset/model/experiment 的职责混在一起。新 Pipeline 把任务用途划分写在对应数据集的 `task_adapters/<task>.json` 中，不设独立的 split 引用；故障起点等来源标签写入四表事件，不当成划分配置。旧文件继续供旧实验使用。

现有 `configs/tasks/downstream_tasks.json` 是全仓库任务盘点，供报告和覆盖审计脚本读取；当前 Runner 按实验配置中的任务字符串分派，并不通过这份盘点文件构造任务。目标结构复用 `configs/tasks/` 目录，新增可由实验引用的任务配置。

## 和当前代码的关系

当前仓库**已有素材，尚不是上面这条统一链路**：

| 可利用的现有文件 | 在目标结构中的位置 |
|---|---|
| `data/tep.py`、`data/pronto.py`、`data/skab.py` | 作为来源读取函数，由新的 Dataset Adapter 调用；补足必要的来源语义。 |
| `models/univariate.py`、`models/univariate_book.py` | 单变量规则与设计计算可逐项复用；Task 的方法模块提供统一入口。 |
| `models/multivariate.py` | Mahalanobis 等数值实现可复用；联合检测 Method 包装任务输入和预测输出。 |
| `tasks/t1_alarm.py`、`tasks/t2_detection.py`、`tasks/adapters.py` | 保留为旧实验入口和迁移参考；其来源读取、组合转换、方法调用应分别归入新的 Bundle Adapter、数据集内 Task Adapter 和 Task。 |
| `config/loader.py`、`runner.py` | 已会读取旧实验引用；新链路补上三引用实验配置、数据集内组合配置解析、任务工厂分派和统一结果入口。 |
| `configs/tasks/downstream_tasks.json` | 保留旧任务盘点；新实验通过各自的 task 配置选择可运行的任务。 |

先用火电压差检查单变量链路，用 TEP 检查联合检测链路；PRONTO、SKAB 后续各自补 Bundle Adapter 和联合检测转换。公开数据标签与现场标签各自保留来源和作用范围。第一轮只需要单变量 `threshold_rule` 与联合检测 `mahalanobis` 两个完整方法，其他方法按相同接口继续接入。火电数据来源、原始文件和既有实验见相邻工作树 `configs/datasets/delay_timer_examples_example3.json`、`configs/experiments/book_t1_example3_non_iid_joint.json`；迁入前不可声称此工作树已能运行该实验。

## 实现前必须固定的协议

上述文件树和 JSON **目前不是可运行实现**。现有 `config/loader.py` 仍要求 `system/split/metrics/outputs`，现有 T2 Adapter 直接输出 `ProcessSeries/DatasetPartitions`，尚无四表 Bundle、数据集内 Task Adapter 及对应 Task/Method 工厂。首条 TEP 链路落地前必须确定 run 内的时间对齐和缺失点规则、事件边界与未检出 ADD 的处理；首条火电链路还必须确定阈值比较、启动/解除延时、死区状态和代理目标的精确定义。四表的时间字段还需兼容紫金的绝对时间与公开数据的相对采样时间，不能把后者伪写成北京时间。否则接口虽然长得一致，预测和指标仍可能不一致。

四张现场原始表的上游转换与正式榜单协议可在相应工作启动时再定，但不能跳过首条链路所需的上述定义。
