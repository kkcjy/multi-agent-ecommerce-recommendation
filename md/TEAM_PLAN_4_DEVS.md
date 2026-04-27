# Multi-Agent E-Commerce 四人开发任务分配（详细版）

## 1. 目标与约束

本轮迭代目标：将当前课程演示项目中的 toy 实现升级为“可演示、可测试、可扩展”的工程化版本，并满足课堂答辩要求：

1. 用户体验设计（User Experience Design）
2. 系统架构（System Architecture）
3. 安全性具体设计（Security Design）
4. 性能具体设计（Performance Design）

团队规模：4 人。
分工原则：任务量均分、难度均衡、可并行开发、每人都有可演示成果。


## 2. 当前项目现状（用于拆分依据）

已具备：

1. FastAPI 主服务入口、推荐接口、实验接口、监控接口
2. 四个 Agent（画像/推荐/文案/库存）+ Supervisor 编排 + LangGraph 编排
3. 用户端与管理端基础前端页面
4. A/B 引擎与基础单测

主要 toy/占位问题：

1. 商品推荐依赖 MOCK_PRODUCTS，缺少真实召回源
2. 向量检索、库存库、特征库存在注释位，尚未完整接入
3. 安全措施较基础（无鉴权、无限流、CORS 全开放）
4. 监控为内存指标，尚未 Prometheus 化、缺少压测报告
5. 前端体验偏 demo，缺少可观测反馈与健壮交互


## 3. 均分策略（工时与难度）

按每人 25% 负载拆分，目标是每人 2 条主线 + 1 条配合线：

1. 主线 A：一个“必须演示”主题（UX/架构/安全/性能中的一个）
2. 主线 B：该主题落到后端与前端至少一端的可运行代码
3. 配合线：参与联调、测试、文档、演示彩排

统一验收口径：

1. 有代码提交（可追溯）
2. 有测试结果或验证记录
3. 有演示脚本（讲得清楚“改了什么、为什么、效果如何”）


## 4. 四人任务分配（具体到开发项）

以下使用“成员 A/B/C/D”表示，可替换为真实姓名。

---

## 4.1 成员 A（负责人：用户体验设计 + 前后端交互体验）

### A-1 目标

把当前用户端/管理端从“能用”升级到“好用、易演示、异常可见”。

### A-2 核心开发任务

1. 用户端交互优化
   - 文件：frontend/user.html, frontend/assets/user.js, frontend/assets/styles.css
   - 增加表单输入校验（user_id 非空、num_items 范围限制、recent_views 解析提示）
   - 增加请求状态机（idle/loading/success/error）及禁用态按钮
   - 增加空结果态与错误态的可理解提示（不是仅输出 Failed）

2. 推荐结果可解释展示
   - 文件：frontend/assets/user.js
   - 在结果区展示 experiment_group、耗时、返回商品数量
   - 增加“推荐理由”展示占位（先读取后端返回字段，后续由成员 B 补充）

3. 管理端可读性增强
   - 文件：frontend/admin.html, frontend/assets/admin.js, frontend/assets/styles.css
   - 实验组、权重、成功失败次数以更清晰布局展示
   - 指标区域支持“无数据引导文案”和刷新反馈
   - outcome 提交后增加成功失败提醒与自动刷新逻辑完善

4. 统一前端异常处理工具
   - 文件：frontend/assets/user.js, frontend/assets/admin.js
   - 抽离公共 escape、fetch error parser、状态展示函数

### A-3 交付物

1. 前端交互改造代码
2. 一页 UX 说明（页面改造点 + 用户路径）
3. 演示录屏或现场演示脚本（2-3 分钟）

### A-4 验收标准

1. 所有异步请求都有 loading 与失败提示
2. 用户端在接口失败时不会白屏，且可重试
3. 管理端刷新和 outcome 提交流程可重复操作
4. 移动端宽度下布局不破坏（至少 375px 宽）


---

## 4.2 成员 B（负责人：系统架构落地 + 推荐链路去 toy）

### B-1 目标

把推荐链路从 mock 驱动升级为“可替换真实数据源”的架构，实现可扩展、可维护。

### B-2 核心开发任务

1. 推荐数据源分层（去硬编码）
   - 文件：agents/product_rec_agent.py
   - 将 MOCK_PRODUCTS 抽离到 repository/service 层，保留接口：
     - recall_by_rules
     - recall_by_vector
     - merge_candidates
   - 保证无向量库时有 fallback，不阻塞主流程

2. Agent 依赖注入
   - 文件：orchestrator/supervisor.py, orchestrator/graph.py, main.py
   - 把 feature_store / vector_store / inventory_db 通过构造注入，不在 Agent 内部写死
   - 抽出统一的 container 或 factory，避免全局单例散落

3. 输出结构可解释化
   - 文件：models/schemas.py, agents/product_rec_agent.py, orchestrator/supervisor.py
   - 在推荐结果中增加 explain 字段（如命中偏好类目、价格匹配）
   - 前端可消费该字段（与成员 A 联调）

4. LangGraph 与 Supervisor 行为对齐
   - 文件：orchestrator/graph.py, orchestrator/supervisor.py
   - 对齐实验分组、过滤逻辑、指标埋点字段
   - 保证两条接口输出结构尽量一致（/recommend 与 /recommend/graph）

### B-3 交付物

1. 架构重构代码（至少包含 1 个数据访问抽象层）
2. 系统架构图（建议画 C4 Level 2 或模块图）
3. 演示脚本：说明“如何从 toy 切换到真实服务”

### B-4 验收标准

1. 推荐链路不再直接依赖固定 mock 常量
2. 数据源不可用时，系统可降级返回结果（不 500）
3. 两条推荐接口核心字段一致，便于前端复用
4. 至少新增 3 条单元测试覆盖重构点


---

## 4.3 成员 C（负责人：安全性具体设计与实现）

### C-1 目标

补齐 API 侧安全基线，让系统具备“课堂可讲清楚”的安全设计与最小可行防护。

### C-2 核心开发任务

1. 接口鉴权（管理端优先）
   - 文件：main.py, config/settings.py
   - 对 /api/v1/experiments, /api/v1/metrics, /api/v1/experiments/*/outcome 增加 API Key 鉴权
   - API Key 从环境变量读取，不写死代码

2. CORS 与配置收敛
   - 文件：main.py, config/settings.py, .env.example
   - 将 allow_origins 从 * 改为配置化白名单
   - 明确 dev/prod 的不同默认值

3. 请求输入校验与安全过滤
   - 文件：models/schemas.py, agents/marketing_copy_agent.py
   - 对 scene、num_items、context 长度做边界约束
   - 对 LLM 输入增加基础 prompt 注入防护（长度、关键字段净化）

4. 限流与滥用防护
   - 文件：main.py（可新增 middleware 模块）
   - 对推荐接口按 user_id/IP 做基础限频
   - 超限返回明确状态码与提示

5. 安全文档
   - 输出威胁模型简表（资产、威胁、控制措施）

### C-3 交付物

1. 可运行的鉴权 + 限流 + 输入约束代码
2. 安全设计说明（用于助教演示）
3. 攻防演示脚本（非法请求如何被拦截）

### C-4 验收标准

1. 未带 Key 访问管理接口被拒绝
2. CORS 只允许白名单来源
3. 超长/异常输入不会导致服务崩溃
4. 限流策略可观测（日志可看到命中记录）


---

## 4.4 成员 D（负责人：性能优化与可观测性）

### D-1 目标

建立“可量化性能”的闭环：基线、优化、对比、结论。

### D-2 核心开发任务

1. 指标体系升级
   - 文件：services/metrics.py, main.py
   - 增加 Prometheus 指标（QPS、P95 延迟、错误率、Agent 耗时分布）
   - 暴露 /metrics（Prometheus 格式）

2. 热路径优化
   - 文件：orchestrator/supervisor.py, agents/*
   - 避免重复计算（如同请求内重复构造数据）
   - 对可缓存结果增加短 TTL 缓存（如用户短期画像）

3. 压测与报告
   - 新增：压测脚本（locust 或 k6）
   - 场景至少包含：
     - 正常推荐流量
     - 峰值突刺
     - 管理接口并发查询
   - 输出优化前后对比：平均延迟、P95、错误率

4. 超时与重试策略校准
   - 文件：agents/base_agent.py, config/settings.py
   - 根据压测结果调整 timeout/retry，避免盲目重试放大压力

### D-3 交付物

1. 性能监控与压测代码
2. 性能设计与结果报告（图表优先）
3. 现场演示：展示优化前后指标差异

### D-4 验收标准

1. 有清晰基线数据（不是口头说快了）
2. 有至少一项可复现优化并量化收益
3. 指标可实时查看且字段含义明确
4. 压测脚本可被队友复用执行


## 5. 联调与公共任务（四人共同）

1. 统一代码规范
   - Python：ruff/black（若课程允许）
   - JS：eslint/prettier（若课程允许）

2. 测试补齐
   - 新增测试优先覆盖：
     - 推荐主流程成功/降级
     - 鉴权失败分支
     - 限流命中分支
     - 指标输出格式

3. 文档与演示统一口径
   - 每人负责自己的设计说明
   - 最终汇总为一套答辩材料，避免重复和冲突



## 8. 风险与预案

1. 外部依赖不可用（LLM/Redis/Milvus）
   - 预案：保留可控 fallback，演示时可切换“离线模式”

2. 重构影响主流程稳定性
   - 预案：分支开发 + 小步 PR + 基础回归测试

3. 时间不足
   - 预案：优先保证“四大演示点”闭环，次要功能延后


## 9. 最终完成定义（Definition of Done）

以下 4 条全部满足即视为本轮完成：

1. UX、架构、安全、性能四个主题均有真实代码改动与可演示结果
2. 四位成员任务量接近且每人都有独立可讲模块
3. 主流程可稳定运行，关键接口有测试或验证记录
4. 课堂演示可在 10-15 分钟内完整跑通
