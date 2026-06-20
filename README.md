# 多 Agent 电商推荐与营销系统

> 软件工程课程结项项目 — 基于 Supervisor 编排模式的多 Agent 协同推荐系统

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue?logo=python)](python/)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

---

## 目录

1. [项目简介](#项目简介)
2. [系统架构](#系统架构)
3. [核心模块](#核心模块)
4. [技术栈](#技术栈)
5. [快速运行](#快速运行)
6. [API 接口](#api-接口)
7. [项目结构](#项目结构)
8. [测试说明](#测试说明)
9. [小组成员](#小组成员)
10. [参考资料与致谢](#参考资料与致谢)

---

## 项目简介

### 背景

随着电子商务的快速发展，用户对个性化商品推荐的需求日益增长。传统推荐系统往往将推荐、营销、库存等环节割裂处理，导致推荐结果与实际库存脱节、营销文案缺乏个性化、各模块之间无法协同等问题。

### 目标

本项目设计并实现了一个基于多 Agent 协同架构的电商推荐与营销系统。系统采用 Supervisor 编排模式，通过用户画像、商品推荐、营销文案、库存决策四个专业化 Agent 的并行协作，为用户提供端到端的个性化推荐服务。

### 主要功能

- **用户画像分析**：基于 Redis 实时特征和 RFM 模型进行用户分群
- **智能商品推荐**：多路召回 + LLM 精排的两阶段推荐策略
- **个性化文案生成**：根据用户画像动态切换 Prompt 模板，生成合规营销文案
- **库存实时校验**：过滤缺货商品，输出限购策略和库存预警
- **A/B 测试**：支持 Thompson Sampling 动态流量调优

---

## 系统架构

### 整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                         用户发起推荐请求                           │
│                    {"user_id": "u001", "num_items": 5}           │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Supervisor 编排器                              │
│                  (python/orchestrator/supervisor.py)              │
│                                                                   │
│  ════════════════ Phase 1: 并行执行 ═══════════════════           │
│  ┌──────────────────────┐    ┌──────────────────────┐            │
│  │   用户画像 Agent      │    │   商品推荐 Agent      │            │
│  │  user_profile_agent  │    │  product_rec_agent   │            │
│  │  ──────────────────  │    │  ────────────────── │            │
│  │  Redis → 实时行为特征 │    │  多路召回 → LLM精排   │            │
│  │  RFM模型 → 用户分群   │    │  返回候选商品列表     │            │
│  └──────────┬───────────┘    └──────────┬──────────┘            │
│             │                           │                         │
│  ════════════════ Phase 2: 并行执行 ═══════════════════           │
│  ┌──────────────────────┐    ┌──────────────────────┐            │
│  │   商品推荐 Agent      │    │   库存决策 Agent      │            │
│  │  (LLM精排重调用)     │    │   inventory_agent    │            │
│  │  ──────────────────  │    │  ────────────────── │            │
│  │  用户画像 × 商品属性  │    │  实时库存查询         │            │
│  │  精排，返回TopN       │    │  过滤缺货，输出限购策略│            │
│  └──────────┬───────────┘    └──────────┬──────────┘            │
│             │                           │                         │
│  ════════════════ Phase 3: 串行执行 ═══════════════════           │
│             └──────────────┬────────────┘                         │
│                            ▼                                      │
│             ┌──────────────────────────────┐                      │
│             │   营销文案 Agent              │                      │
│             │  marketing_copy_agent        │                      │
│             │  ────────────────────────── │                      │
│             │  Prompt模板 × 用户分群       │                      │
│             │  LLM生成 + 广告法合规校验    │                      │
│             └──────────────┬───────────────┘                      │
│                            ▼                                      │
│             ┌──────────────────────────────┐                      │
│             │   A/B 测试引擎               │                      │
│             │  用户ID哈希分桶              │                      │
│             │  Thompson Sampling 动态调优  │                      │
│             └──────────────┬───────────────┘                      │
└──────────────────────────────┬──────────────────────────────────┘
                               ▼
              ┌─────────────────────────────────┐
              │  个性化推荐响应（返回给用户）      │
              │  商品列表 + 个性化文案 + 实验分组 │
              └─────────────────────────────────┘
```

### 编排模式说明

本系统采用 Supervisor 编排模式，由 Supervisor 统一协调各 Agent 的执行顺序和数据流转：

- Phase 1：用户画像 Agent 和商品推荐 Agent 并行执行（`asyncio.gather()`）
- Phase 2：LLM 精排和库存校验并行执行
- Phase 3：营销文案 Agent 串行执行（依赖前两阶段结果）

该模式具有集中控制、流程清晰、并行执行、异常统一处理等优点。

---

## 核心模块

### 用户画像 Agent

**文件**：[`python/agents/user_profile_agent.py`](python/agents/user_profile_agent.py)

负责用户行为数据的采集、分析和分群。通过 Redis Feature Store 获取实时行为特征，结合 RFM 模型（Recency、Frequency、Monetary）计算用户得分，并将用户分为新客、VIP、价格敏感、活跃、流失风险五个群体。

- L1 内存缓存（TTLCache）+ L2 Redis 缓存，减少重复计算
- 支持演示用户快速路径，方便测试验证

### 商品推荐 Agent

**文件**：[`python/agents/product_rec_agent.py`](python/agents/product_rec_agent.py)

采用两阶段推荐策略：第一阶段通过多路召回（类目匹配、热门、新品、向量检索）获取候选商品集；第二阶段根据用户画像属性进行规则重排序，返回 TopN 结果。

- 每个商品附带 explain 字段，记录召回来源和匹配信息
- 支持场景化推荐（首页、搜索、分类等）

### 营销文案 Agent

**文件**：[`python/agents/marketing_copy_agent.py`](python/agents/marketing_copy_agent.py)

根据用户分群自动选择合适的 Prompt 模板，调用 LLM 生成个性化营销文案。内置广告法合规校验，自动过滤违禁词，防止 Prompt 注入攻击。

### 库存决策 Agent

**文件**：[`python/agents/inventory_agent.py`](python/agents/inventory_agent.py)

实时查询商品库存状态，过滤缺货商品，计算安全库存和低库存预警，输出限购策略。

---

## 技术栈

| 类别 | 技术 |
|------|------|
| 后端框架 | FastAPI + Uvicorn |
| 编排框架 | LangGraph |
| LLM 服务 | GLM-5.1 (meai.cloud) |
| 缓存 | Redis |
| 向量数据库 | Milvus |
| 数据库 | SQLite / MySQL |
| 容器化 | Docker Compose |
| 测试 | pytest + Locust |
| 前端 | HTML / CSS / JavaScript |

---

## 快速运行

### 环境要求

- Python 3.11+
- LLM API Key（meai.cloud 或其他兼容 OpenAI 接口的服务）

### 运行步骤

```bash
# 1. 克隆项目
git clone https://github.com/bcefghj/multi-agent-ecommerce-recommendation.git
cd multi-agent-ecommerce-recommendation/python

# 2. 创建虚拟环境
python -m venv .venv
.venv\Scripts\activate   # Windows
# source .venv/bin/activate   # Linux/Mac

# 3. 安装依赖
pip install -r requirements.txt

# 4. 配置环境变量
cp .env.example .env
# 编辑 .env 文件，填入 LLM_API_KEY

# 5. 启动服务
python main.py
# 访问 http://localhost:8866
```

### Docker 部署

```bash
docker-compose up -d
# 等待服务启动后访问 http://localhost:8866
```

---

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/v1/recommend` | 核心推荐接口 |
| `POST` | `/api/v1/recommend/graph` | LangGraph 状态图推荐 |
| `GET` | `/api/v1/experiments` | 查看 A/B 实验状态 |
| `GET` | `/api/v1/metrics` | 系统监控指标 |
| `GET` | `/health` | 健康检查 |

### 请求示例

```json
POST /api/v1/recommend
Content-Type: application/json

{
  "user_id": "user_001",
  "scene": "homepage",
  "num_items": 5,
  "context": {
    "recent_views": ["手机", "耳机"],
    "avg_order_amount": 500
  }
}
```

### 响应示例

```json
{
  "request_id": "a3f8c2d1-...",
  "user_id": "user_001",
  "products": [
    {
      "product_id": "P001",
      "name": "iPhone 16 Pro",
      "category": "手机",
      "price": 7999.0,
      "score": 0.95
    }
  ],
  "marketing_copies": [
    {
      "product_id": "P001",
      "copy": "根据您的浏览偏好，为您精选 iPhone 16 Pro，好评率 98%。"
    }
  ],
  "experiment_group": "treatment",
  "total_latency_ms": 1523.4
}
```

---

## 项目结构

```
multi-agent-ecommerce-recommendation/
│
├── README.md                          # 项目说明文档
├── docker-compose.yml                 # Docker 一键部署配置
│
└── python/                            # Python 后端实现
    ├── main.py                        # FastAPI 服务入口
    ├── requirements.txt               # Python 依赖列表
    ├── .env.example                   # 环境变量模板
    ├── agents/                        # 4 个 Agent 实现
    │   ├── base_agent.py              # Agent 基类：重试/超时/降级
    │   ├── user_profile_agent.py      # 用户画像 Agent
    │   ├── product_rec_agent.py       # 商品推荐 Agent
    │   ├── marketing_copy_agent.py    # 营销文案 Agent
    │   └── inventory_agent.py         # 库存决策 Agent
    ├── orchestrator/
    │   ├── supervisor.py              # Supervisor 并行编排器
    │   └── graph.py                   # LangGraph 状态图
    ├── services/
    │   ├── ab_test.py                 # A/B 测试引擎
    │   ├── feature_store.py           # Redis 实时特征服务
    │   ├── metrics.py                 # 监控指标
    │   ├── order_service.py           # 订单模拟服务
    │   ├── review_service.py          # 评价数据服务
    │   ├── catalog_service.py         # 商品目录服务
    │   └── vector_store.py            # 向量存储服务
    ├── models/schemas.py              # Pydantic 数据模型
    ├── config/settings.py             # 配置管理
    ├── containers/app_container.py    # 依赖注入容器
    ├── repositories/                  # 数据仓库层
    ├── frontend/                      # 前端静态页面
    └── tests/                         # 测试套件
```

---

## 测试说明

### 测试套件

| 测试类型 | 文件 | 说明 |
|---|---|---|
| 单元测试 | `tests/test_product_rec_agent.py` | 推荐 Agent 单元测试 |
| 单元测试 | `tests/test_container.py` | 依赖注入容器测试 |
| 单元测试 | `tests/test_repositories.py` | 数据仓库层测试 |
| 单元测试 | `tests/test_ab_test.py` | A/B 测试引擎测试 |
| 集成测试 | `tests/test_supervisor_integration.py` | Supervisor 端到端测试 |
| 集成测试 | `tests/test_graph_supervisor_alignment.py` | Graph 与 Supervisor 输出对齐测试 |
| 安全测试 | `tests/test_security_guards.py` | 鉴权、限流、输入校验测试 |
| 冒烟测试 | `tests/smoke_ui_api_harness.py` | UI/API 端点可用性检查 |
| 性能测试 | `tests/load_test_locust.py` | Locust 压力测试 |

### 运行测试

```bash
cd python

# 运行所有 pytest 测试
python -m pytest tests/ -v

# 运行冒烟测试
python tests/smoke_ui_api_harness.py --base-url http://localhost:8866

# 运行压力测试（需先启动服务）
locust -f tests/load_test_locust.py --host=http://localhost:8866 --users=100 --spawn-rate=2 --run-time=60s
```

---

## 小组成员

| 成员 | 负责模块 |
|------|---------|
| 成员 A | 可行性分析、运行维护、项目规划 |
| 成员 B | 需求分析、用户场景、用例建模 |
| 成员 C | UI/UX 设计、系统设计、程序开发 |
| 成员 D | 测试验收、演示视频 |

---

## 参考资料与致谢

- [NVIDIA Retail Agentic Commerce](https://github.com/NVIDIA-AI-Blueprints/Retail-Agentic-Commerce)
- [Spring AI Alibaba](https://github.com/spring-ai-alibaba/spring-ai-alibaba-multi-agent-demo)
- [LangGraph 官方文档](https://langchain-ai.github.io/langgraph/)
- [FastAPI 官方文档](https://fastapi.tiangolo.com/)
- [MiniMax API](https://www.minimax.chat/)

---

## License

[MIT License](LICENSE)
