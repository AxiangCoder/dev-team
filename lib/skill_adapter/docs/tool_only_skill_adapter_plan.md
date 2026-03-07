# Claude Skill 标准库开发计划

## 1. 文档目的

本文档定义了 `skill_adapter` 的分阶段开发计划，目标是将 Claude Skill 风格的技能接入 LangChain 与 LangGraph 等智能体框架。

当前策略：

- 第一阶段仅支持 `tool_call`
- 明确暂不支持 `script_runner`
- 库的重点是加载 `SKILL.md`、注册技能、路由到应用侧工具，并返回标准化执行结果

本文覆盖：

- 产品范围
- 架构边界
- 开发计划
- 对外 API
- API 使用示例
- LangChain 与 LangGraph 集成模式

## 2. 产品目标

该库的目标不只是解析 `SKILL.md`，而是把一个 skill 转化为可被框架直接使用的运行时能力。

更具体地说，该库应提供：

1. Skill 加载与校验
2. Skill 注册与发现
3. 标准化执行请求与执行结果
4. 通过 LangChain 兼容工具完成实际执行的 `tool_call` 模式
5. 用于权限、校验、超时、追踪与可观测性的中间件扩展点
6. 面向 LangChain 与 LangGraph 的稳定集成层

## 3. 范围

### 当前里程碑包含

- 从 `SKILL.md` 加载 skill 目录
- 解析 frontmatter 与 markdown 正文
- 将 skill 注册到运行时注册表
- 通过 `tool_call` 执行 skill
- 支持应用侧提供的 LangChain 工具
- 返回标准化执行结果
- 提供中间件扩展点
- 提供 LangChain/LangGraph 集成辅助 API

### 当前里程碑不包含

- 执行 `scripts/` 下的本地脚本
- 进程沙箱执行
- skill 依赖安装
- 远程 skill 仓库
- 热更新
- 带版本的 skill 包管理

## 4. 设计原则

1. 库负责 skill 生命周期与执行协议。
2. 应用负责业务工具，例如数据库查询工具、检索工具、外部 API 工具。
3. `tool_call` 应复用 LangChain 的工具系统，而不是另造一套工具抽象。
4. 对外 API 要明确区分“当前稳定行为”和“后续规划行为”。
5. 无论底层工具如何实现，执行返回类型都必须标准化。

## 5. 高层架构

```text
SKILL.md
  -> SkillLoader
  -> SkillSpec
  -> SkillRegistry
  -> ToolCallExecutor
  -> LangChain Tool / App Tool
  -> SkillExecutionResult
```

职责：

- `SkillLoader`：解析并校验 skill 定义
- `SkillSpec`：存储 skill 的静态元数据
- `SkillRegistry`：存储运行时注册信息并执行路由
- `ToolCallExecutor`：通过应用定义的工具执行 skill
- `Middleware`：执行权限、校验、超时、追踪等横切逻辑
- `Adapters`：暴露 LangChain/LangGraph 辅助接口

## 6. 建议目录结构

```text
skill_adapter/
  __init__.py
  exceptions.py
  loader.py
  models.py
  registry.py
  middleware.py
  executors/
    __init__.py
    base.py
    tool_call.py
  adapters/
    __init__.py
    langchain.py
    langgraph.py
docs/
  tool_only_skill_adapter_plan.md
```

应用侧示例：

```text
app/
  tools/
    sql_tool.py
    order_tool.py
  bootstrap/
    skills.py
skills/
  sql-expert/
    SKILL.md
  order-analyst/
    SKILL.md
```

重要边界：

- 业务工具应位于应用项目中，而不是 `skill_adapter` 内部
- `skill_adapter` 负责 skill 管理，不负责业务逻辑实现

## 7. 开发计划

### Phase 0：稳定现有基础能力

目标：

- 修复当前库中的运行时健壮性问题

任务：

1. 在整个执行链中将 `context` 默认处理为一个空字典。
2. 对 `conflict_policy` 做显式校验。
3. 清晰区分 frontmatter 与 markdown 正文。
4. 增强 frontmatter 解析，或接入标准 YAML 解析器。
5. 统一执行错误包装逻辑。

交付物：

- 现有 loader 与 registry 具备可持续迭代的稳定基础

### Phase 1：引入仅工具执行模式

目标：

- 仅支持 `tool_call` 执行模式

任务：

1. 为执行请求增加 `mode`
2. 引入执行器抽象
3. 实现 `ToolCallExecutor`
4. 增加 tool resolver / tool map 注册机制
5. 统一 `SkillExecutionResult` 结构
6. 文档化第一版“一 skill 对应一 tool”约定

交付物：

- 一个 skill 可从 `SKILL.md` 被加载、路由到应用工具，并通过 `registry.execute()` 执行

### Phase 2：框架适配层

目标：

- 降低 LangChain 与 LangGraph 用户的接入成本

任务：

1. 增加 `to_langchain_tool(...)`
2. 增加 `build_registry(...)` 便捷 API
3. 增加 LangGraph 集成辅助示例
4. 增加可用 skill 的 prompt 构建辅助函数

交付物：

- 该库可用最小样板代码接入常见智能体编排流程

### Phase 3：校验与可观测性增强

目标：

- 使运行时具备生产可用性

任务：

1. 增加输入校验中间件
2. 增加超时中间件
3. 增加追踪中间件
4. 增加结构化错误码
5. 增加测试夹具与契约测试

交付物：

- 更稳定的执行行为与更好的运维可观测能力

### Deferred Phase：脚本执行支持（后置）

后续计划：

- 增加 `script_runner`
- 增加进程隔离 / 沙箱能力
- 增加脚本权限模型

该阶段明确延后，不纳入当前里程碑。

## 8. 对外 API 设计

本节定义“仅工具执行”里程碑下的目标公开 API。

### 8.1 模型

#### `SkillSpec`

用途：

- 表示一个 skill 的静态定义（解析后结构）

建议结构：

```python
@dataclass(frozen=True)
class SkillSpec:
    name: str
    description: str
    version: str | None
    body: str
    root_path: Path
    metadata: dict[str, Any] = field(default_factory=dict)
    input_schema: dict[str, Any] | None = None
    output_schema: dict[str, Any] | None = None
```

用法：

- 由 `SkillLoader` 产出
- 存储在 `SkillRegistry`
- 供执行器与适配层消费

#### `SkillExecutionRequest`

用途：

- 表示一次运行时调用请求

建议结构：

```python
@dataclass(frozen=True)
class SkillExecutionRequest:
    skill_name: str
    input_data: Any
    context: dict[str, Any] = field(default_factory=dict)
    mode: str = "tool_call"
```

用法：

- 由应用侧或便捷 API 构造
- 经过中间件链并进入执行器

#### `SkillError`

用途：

- 提供标准化错误载荷

建议结构：

```python
@dataclass(frozen=True)
class SkillError:
    code: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)
```

用法：

- 放入 `SkillExecutionResult` 返回
- 便于 agent 与日志系统进行稳定处理

#### `SkillExecutionResult`

用途：

- 表示一次 skill 调用的标准化结果

建议结构：

```python
@dataclass(frozen=True)
class SkillExecutionResult:
    skill_name: str
    status: str
    output: Any = None
    error: SkillError | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
```

用法：

- 由 `SkillRegistry.execute(...)` 返回
- 供应用、agent 或适配层直接消费

### 8.2 Loader API

#### `SkillLoader.load_skill(path) -> SkillSpec`

用途：

- 加载单个 skill 目录，并生成已校验的 `SkillSpec`

预期行为：

1. 校验目录存在
2. 校验 `SKILL.md` 存在且非空
3. 解析 frontmatter
4. 提取 markdown 正文
5. 构造 `SkillSpec`

示例：

```python
loader = SkillLoader()
spec = loader.load_skill("./skills/sql-expert")
print(spec.name)
print(spec.body)
```

#### `SkillLoader.load_directory(path) -> list[SkillSpec]`

用途：

- 批量加载根目录下所有合法 skill

示例：

```python
loader = SkillLoader()
specs = loader.load_directory("./skills")
```

### 8.3 Registry API

#### `SkillRegistry(conflict_policy="error")`

用途：

- 创建 skill 定义与执行路由的运行时注册表

支持值：

- `error`
- `override`
- `keep_existing`

示例：

```python
registry = SkillRegistry(conflict_policy="error")
```

#### `register(spec: SkillSpec) -> None`

用途：

- 注册单个 skill 定义

示例：

```python
registry.register(spec)
```

#### `register_many(specs: list[SkillSpec]) -> None`

用途：

- 批量注册 skill 定义

示例：

```python
registry.register_many(specs)
```

#### `get(name: str) -> SkillSpec`

用途：

- 按名称获取已注册的 skill 定义

示例：

```python
sql_spec = registry.get("sql-expert")
```

#### `list() -> list[str]`

用途：

- 返回可用 skill 名称列表

示例：

```python
skills = registry.list()
```

#### `unregister(name: str) -> None`

用途：

- 从注册表移除 skill

示例：

```python
registry.unregister("sql-expert")
```

### 8.4 执行器 API

#### `add_executor(mode: str, executor: SkillExecutor) -> None`

用途：

- 为指定 `mode` 注册执行器实现

示例：

```python
registry.add_executor("tool_call", tool_call_executor)
```

#### `execute(request: SkillExecutionRequest) -> SkillExecutionResult`

用途：

- 通过中间件链与指定执行器执行一次 skill 请求

预期流程：

1. 校验请求
2. 解析目标 skill
3. 按 mode 解析执行器
4. 应用中间件链
5. 执行工具调用
6. 返回标准化结果

示例：

```python
req = SkillExecutionRequest(
    skill_name="sql-expert",
    input_data={"sql": "select 1"},
    context={"allowed_skills": ["sql-expert"], "logs": []},
    mode="tool_call",
)

result = registry.execute(req)
```

#### `execute_by_name(skill_name, input_data, context=None, mode="tool_call")`

用途：

- `SkillExecutionRequest` 的便捷封装入口

示例：

```python
result = registry.execute_by_name(
    "sql-expert",
    {"sql": "select 1"},
    context={"allowed_skills": ["sql-expert"]},
    mode="tool_call",
)
```

### 8.5 中间件 API

#### `use(middleware: SkillMiddleware) -> None`

用途：

- 将一个中间件加入执行链

示例：

```python
registry.use(PermissionMiddleware())
registry.use(TimeoutMiddleware(timeout_ms=8000))
registry.use(TracingMiddleware())
```

#### `SkillMiddleware.wrap(next) -> next`

用途：

- 作为横切逻辑扩展点的基础协议

仅工具模式下的常见中间件：

1. `PermissionMiddleware`
2. `ValidationMiddleware`
3. `TimeoutMiddleware`
4. `TracingMiddleware`

### 8.6 构建 API

#### `build_registry(...) -> SkillRegistry`

用途：

- 提供一键初始化的常用构建入口

建议签名：

```python
def build_registry(
    skills_directory: str | Path,
    *,
    conflict_policy: str = "error",
    executors: dict[str, SkillExecutor] | None = None,
    middleware: list[SkillMiddleware] | None = None,
) -> SkillRegistry:
    ...
```

示例：

```python
registry = build_registry(
    "./skills",
    executors={"tool_call": tool_call_executor},
    middleware=[
        PermissionMiddleware(),
        ValidationMiddleware(),
        TracingMiddleware(),
    ],
)
```

### 8.7 LangChain 适配 API

#### `to_langchain_tool(registry, skill_name, *, mode="tool_call")`

用途：

- 将已注册 skill 包装为 LangChain tool，供 LangChain agent 直接调用

示例：

```python
tool = to_langchain_tool(registry, "sql-expert", mode="tool_call")
```

#### `build_skills_prompt(registry) -> str`

用途：

- 生成简明的 skill 能力摘要，用于 prompt 注入

示例：

```python
skills_prompt = build_skills_prompt(registry)
```

## 9. ToolCall 执行模型

### 概要

在当前里程碑中，skill 不执行本地脚本，而是路由到应用定义的 LangChain tool。

执行流程：

1. 加载 `SKILL.md`
2. 注册 skill
3. 注册 `tool_call` 执行器
4. 建立 skill 名称到应用 tool 的映射
5. 调用 `registry.execute(...)`
6. 返回 `SkillExecutionResult`

### 应用侧职责

真实业务 tool 由应用定义。

示例：

```python
from langchain_core.tools import tool

@tool
def sql_tool(sql: str) -> dict:
    """Run a read-only SQL query."""
    return {"rows": [], "row_count": 0}
```

然后应用侧将 tool 注入执行器：

```python
tool_map = {
    "sql-expert": sql_tool,
}
```

标准库不应包含应用特定业务工具。

## 10. API 使用示例

### 10.1 基础初始化

```python
from skill_adapter import (
    SkillLoader,
    SkillRegistry,
    PermissionMiddleware,
    ValidationMiddleware,
    TracingMiddleware,
    ToolCallExecutor,
)

loader = SkillLoader()
specs = loader.load_directory("./skills")

registry = SkillRegistry(conflict_policy="error")
registry.register_many(specs)

tool_map = {
    "sql-expert": sql_tool,
    "order-analyst": order_tool,
}

registry.add_executor(
    "tool_call",
    ToolCallExecutor(tool_resolver=lambda skill_name: tool_map[skill_name]),
)

registry.use(PermissionMiddleware())
registry.use(ValidationMiddleware())
registry.use(TracingMiddleware())
```

### 10.2 直接执行

```python
req = SkillExecutionRequest(
    skill_name="sql-expert",
    input_data={"sql": "select * from orders limit 10"},
    context={
        "allowed_skills": ["sql-expert"],
        "logs": [],
        "trace_id": "req-001",
    },
    mode="tool_call",
)

result = registry.execute(req)

if result.status == "success":
    print(result.output)
else:
    print(result.error.message)
```

### 10.3 一 skill 一 tool 约定

第一版建议约定：

- 一个 skill 映射一个业务 tool
- 路由逻辑简单
- 集成成本低

后续可扩展为：

- 一个 skill 映射多个 tool
- 按 metadata 或 planner 逻辑进行 tool 路由

## 11. LangGraph 集成示例

这是当前仅工具模式下推荐的 LangGraph 使用模式。

```python
from typing import TypedDict, Any
from langgraph.graph import StateGraph, END


class AgentState(TypedDict, total=False):
    user_query: str
    chosen_skill: str
    skill_result: dict[str, Any]
    answer: str
    logs: list[str]


def planner_node(state: AgentState) -> AgentState:
    query = state["user_query"]
    if "order" in query.lower():
        return {"chosen_skill": "sql-expert"}
    return {"chosen_skill": "order-analyst"}


def execute_skill_node(state: AgentState) -> AgentState:
    req = SkillExecutionRequest(
        skill_name=state["chosen_skill"],
        input_data={"query": state["user_query"]},
        context={
            "allowed_skills": [state["chosen_skill"]],
            "logs": state.get("logs", []),
        },
        mode="tool_call",
    )
    result = registry.execute(req)

    if result.status == "success":
        return {
            "skill_result": {"ok": True, "output": result.output},
            "logs": req.context["logs"],
        }
    return {
        "skill_result": {"ok": False, "error": result.error.message},
        "logs": req.context["logs"],
    }


def respond_node(state: AgentState) -> AgentState:
    if state["skill_result"]["ok"]:
        return {"answer": f"Result: {state['skill_result']['output']}"}
    return {"answer": f"Execution failed: {state['skill_result']['error']}"}


graph = StateGraph(AgentState)
graph.add_node("planner", planner_node)
graph.add_node("exec_skill", execute_skill_node)
graph.add_node("respond", respond_node)

graph.set_entry_point("planner")
graph.add_edge("planner", "exec_skill")
graph.add_edge("exec_skill", "respond")
graph.add_edge("respond", END)

app = graph.compile()
```

集成规则：

- LangGraph 节点应统一调用 `registry.execute(...)`
- 除非有意绕开 skill 层，否则图节点不应直接调用底层原始 tools

## 12. LangChain 集成示例

概念上支持两种集成方式。

### 风格 A：在应用代码中直接调用 Registry

```python
result = registry.execute_by_name(
    "sql-expert",
    {"sql": "select count(*) from orders"},
    context={"allowed_skills": ["sql-expert"]},
    mode="tool_call",
)
```

### 风格 B：将注册后的 skill 暴露为 LangChain Tool

```python
langchain_tool = to_langchain_tool(registry, "sql-expert", mode="tool_call")
```

该方式适用于：

- 外层 agent 系统要求接收 LangChain tools
- 你希望在 agent 边界把 skill 直接呈现为 tool

## 13. 建议初始约定

为保证第一版简单且稳定，建议采用以下约定：

1. 仅支持 `mode="tool_call"`
2. 一 skill 对应一个应用侧 tool
3. 应用侧 tool 放在 `skill_adapter` 外部
4. `SkillExecutionResult` 作为唯一执行返回结构
5. `context` 必须是字典

## 14. 测试计划

至少应覆盖以下测试：

1. 加载一个合法 skill
2. 拒绝空 `SKILL.md` 或非法 `SKILL.md`
3. 在三种冲突策略下测试同名 skill 注册
4. 通过 `tool_call` 成功执行 skill
5. 当 skill 不在允许列表时拒绝执行
6. 当工具执行失败时返回结构化错误
7. 保留 tracing metadata 与 logs

建议测试层级：

- loader 单元测试
- registry 单元测试
- middleware 单元测试
- 使用假 LangChain tool 的集成测试

## 15. 待确认问题

在实现开始前建议先决策：

1. `SkillSpec` 中的 `version`、`input_schema`、`output_schema` 是第一阶段就引入，还是第二阶段再加？
2. `ToolCallExecutor` 第一版是否支持异步工具？
3. `to_langchain_tool(...)` 应归入第一阶段还是第二阶段？
4. `build_registry(...)` 是否自动安装默认中间件链？
5. “一 skill 多 tools”是否应放到首个稳定版之后再做？

## 16. 建议实现顺序

实际编码建议按以下顺序推进：

1. 修复当前 loader 与 registry 的健壮性问题
2. 围绕 `SkillSpec`、`SkillExecutionRequest`、`SkillExecutionResult` 与 `SkillError` 重构模型
3. 引入执行器抽象
4. 实现 `ToolCallExecutor`
5. 更新 `build_registry(...)`
6. 增强中间件能力
7. 增加 LangChain 适配辅助函数
8. 增加 LangGraph 集成示例与测试

## 17. 最终建议

首个里程碑的正确路径是：

- 将 `skill_adapter` 定位为 skill 运行时协议层
- 只支持 `tool_call`
- 让应用侧拥有业务 tools
- 先采用“一 skill 一 tool”约定

这种路径能在不提前引入脚本执行复杂度的前提下，以更小成本实现稳定、可预测，并兼容 LangChain/LangGraph 的能力。
