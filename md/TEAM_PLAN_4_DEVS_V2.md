# Multi-Agent E-Commerce 四人开发任务分配 V2（评审改进版）

## 1. 背景与改进目标

基于老师评审意见，本轮迭代重点解决三个核心问题：

| 序号 | 评审意见 | 改进方向 |
|------|---------|---------|
| 1 | 商品不一定要很多，但需要把图标换成真实图片 | 图片由团队自行下载，保存在项目本地 `assets/images/products/` 目录，前端直接引用本地路径 |
| 2 | 用户账号需要多搞几个账号，不要只是一个账号演示 | 预置多个差异化用户账号，支持切换体验不同画像 |
| 3 | 总体再完善一下，把系统做得真实一点 | 全局仿真度提升：购物车、订单流、评价系统、更真实的交互链路 |

### 当前项目现状

- **商品数据**：45+ 个商品（P001-P045+），`image_url` 字段全部为空，前端通过 emoji 占位
- **用户系统**：前端 localStorage 随机生成 `user_xxxxx`，无多账号、无预置画像
- **前端页面**：6 个页面全部用 emoji 显示商品
- **后端**：FastAPI + 4 Agent + Supervisor + LangGraph，已有完整推荐链路

### 图片方案说明

图片由开发者自行从品牌官网/电商平台下载，保存到项目本地目录：

```
python/frontend/assets/images/products/
├── P001.jpg          # iPhone 16 Pro 主图
├── P001_1.jpg        # iPhone 16 Pro 细节图
├── P001_2.jpg        # iPhone 16 Pro 场景图
├── P002.jpg          # 华为 Mate 70 主图
├── ...
├── default_phone.jpg   # 品类兜底图
├── default_earphone.jpg
├── default_tablet.jpg
├── default_laptop.jpg
├── default_accessory.jpg
├── default_monitor.jpg
└── default_wearable.jpg
```

- 命名规则：`{商品ID}.jpg` 为主图，`{商品ID}_{序号}.jpg` 为多角度图
- 每个品类准备 1 张品类兜底图（用于图片加载失败 fallback）
- 前端通过 `/assets/images/products/P001.jpg` 路径引用（项目已 mount `/assets` → StaticFiles）
- 后端 `image_url` 字段存储相对路径如 `/assets/images/products/P001.jpg`

---

## 2. 四人分工总览（均分 ~25%）

```
┌───────────────────────────────────────────────────────────────┐
│                     任务分配总览（均分版）                        │
├──────────┬─────────────────────────────┬───────────────────────┤
│  成员     │  核心任务                     │  预估工时              │
├──────────┼─────────────────────────────┼───────────────────────┤
│  开发者 A │  商品图片 + 商品数据 + 图片渲染  │  ~25%                 │
│  开发者 B │  多账号用户系统                 │  ~25%                 │
│  开发者 C │  前端交互升级（购物车/订单/页脚） │  ~25%                 │
│  开发者 D │  后端服务 + 数据完善            │  ~25%                 │
└──────────┴─────────────────────────────┴───────────────────────┘
```

---

## 3. 开发者 A：商品图片系统 + 商品数据 + 前端图片渲染（~25%）

### 3.1 目标

完成本地图片资源准备、商品数据精简、以及所有前端页面的 emoji → 真实图片渲染改造。

### 3.2 核心任务

#### A-1：下载并组织本地图片资源

**操作**：在 `python/frontend/assets/images/products/` 目录下保存图片文件

- 从品牌官网或电商平台下载 22 款商品的高清产品图（JPG 格式，宽 400-800px）
- 每款商品至少 1 张主图，核心商品（手机、耳机）准备 3 张多角度图
- 每个品类准备 1 张品类兜底图（fallback 用）

**精简后商品清单（22 款）**：

| 品类 | 数量 | 商品 |
|------|------|------|
| 手机 | 4 | iPhone 16 Pro, 华为 Mate 70, 小米 15, Samsung Galaxy S26 |
| 耳机 | 4 | AirPods Pro 3, Sony WH-1000XM6, Bose QC Ultra, Redmi Buds 6 Pro |
| 平板 | 3 | iPad Air M3, 小米平板 7 Pro, Galaxy Tab S10 |
| 笔记本 | 3 | MacBook Air M4, 联想拯救者 Y9000P, Dell XPS 14 |
| 配件 | 3 | 罗技 MX Master 3S, Anker 140W 充电器, Keychron K3 Pro |
| 显示器 | 3 | 戴尔 U2724D, LG 27GP850, 华为 MateView SE |
| 穿戴 | 2 | Apple Watch Ultra 3, 华为 Watch GT 6 |

需要下载的图片文件数量：
- 22 款商品 × 1 张主图 = 22 张主图
- 10 款核心商品 × 2 张额外图 = 20 张多角度图
- 7 个品类兜底图 = 7 张
- **合计约 49 张图片**

#### A-2：精简商品数据 + 填充图片路径

**涉及文件**：`python/repositories/in_memory_product_repository.py`

- 从 45+ 款精简至 22 款核心商品
- 为每个商品添加 `image_url`（主图本地路径）和 `image_urls`（多角度图列表）
- 示例：`image_url="/assets/images/products/P001.jpg"`，`image_urls=["/assets/images/products/P001.jpg", "/assets/images/products/P001_1.jpg"]`
- 删除未保留的商品条目

#### A-3：前端图片渲染改造（所有页面）

**涉及文件**：所有前端 JS 文件

| 文件 | 改造点 |
|------|--------|
| `python/frontend/assets/home.js` | `getProductEmoji()` → 渲染 `<img>` 标签，onerror fallback 到品类 emoji |
| `python/frontend/assets/product.js` | 详情页 gallery 从 emoji → `<img>` 标签，支持多图切换 |
| `python/frontend/assets/user.js` | 个性化推荐卡片图片渲染 |
| `python/frontend/assets/category.js` | 分类页商品卡片图片渲染 |
| `python/frontend/assets/search.js` | 搜索结果页商品图片渲染 |

渲染改造通用模式：

```javascript
// 改造前
<div class="product-image">${emoji(product.category)}</div>

// 改造后
<div class="product-image">
  <img src="${product.image_url || ''}" alt="${product.name}"
       loading="lazy"
       onerror="this.onerror=null;this.src='';this.parentNode.innerHTML='${emoji(product.category)}'" />
</div>
```

- 添加 `loading="lazy"` 懒加载
- `onerror` fallback：图片加载失败时回退到品类 emoji
- 保持 CSS `.product-image` 容器尺寸不变

### 3.3 交付物

1. `python/frontend/assets/images/products/` 目录：~49 张本地图片文件
2. 更新后的 `in_memory_product_repository.py`（22 款商品 + 图片路径）
3. 5 个前端 JS 文件的图片渲染改造

### 3.4 验收标准

- [ ] 22 款商品均有本地图片，页面可正常显示
- [ ] 图片加载失败时自动 fallback 到品类 emoji
- [ ] 商品详情页 gallery 支持多图切换
- [ ] 所有页面（首页/分类/搜索/商品详情/个人中心）图片正常
- [ ] 页面布局在图片替换后不破坏（375px - 1440px）

---

## 4. 开发者 B：多账号用户系统（~25%）

### 4.1 目标

建立多用户账号体系，支持演示时快速切换不同用户画像，展示个性化推荐差异。

### 4.2 核心任务

#### B-1：预置用户账号数据

**涉及文件**：新建 `python/services/demo_users.py`

设计 6 个差异化预置用户，覆盖不同画像分群：

| 用户 ID | 昵称 | 年龄 | 城市 | 分群 | 偏好类目 | 价格区间 | 演示场景 |
|---------|------|------|------|------|---------|---------|---------|
| `demo_tech` | 数码极客·张伟 | 28 | 北京 | high_value | 手机, 笔记本, 配件 | 5000-15000 | 旗舰新品推荐 |
| `demo_student` | 校园达人·李明 | 21 | 上海 | price_sensitive | 手机, 耳机, 平板 | 1000-4000 | 性价比好物推荐 |
| `demo_worker` | 都市白领·王芳 | 32 | 深圳 | active | 配件, 显示器, 穿戴 | 2000-8000 | 办公效率装备 |
| `demo_sport` | 运动达人·赵强 | 26 | 成都 | active | 穿戴, 耳机 | 1500-6000 | 运动户外装备 |
| `demo_newbie` | 萌新用户·陈静 | 19 | 杭州 | new_user | 手机, 耳机 | 500-2000 | 入门级推荐 |
| `demo_return` | 回归用户·刘洋 | 35 | 广州 | churn_risk | 笔记本, 显示器 | 3000-10000 | 召回优惠推荐 |

每个用户包含：`user_id`、`nickname`、`avatar`（头像 emoji 或纯色首字母）、`age`、`gender`、`city`、`segments`、`preferred_categories`、`price_range`、`recent_views`、`recent_purchases`、`rfm_score`、`login_count`、`register_time`

#### B-2：用户切换 API

**涉及文件**：修改 `python/main.py`

- `GET /api/v1/demo-users`：返回所有预置用户列表（id、昵称、头像、分群标签）
- `GET /api/v1/demo-users/{user_id}`：返回单个用户完整画像
- `POST /api/v1/demo-users/switch`：切换当前演示用户（body: `{"user_id": "xxx"}`）
- 切换后推荐接口自动使用新用户画像

#### B-3：前端用户切换交互

**涉及文件**：修改 `python/frontend/user.html`，修改 `python/frontend/assets/user.js`

改造个人中心页面：

1. **顶部用户切换区**：
   - 显示当前用户头像 + 昵称 + 分群标签
   - "切换用户"按钮 → 弹出用户选择弹窗
   - 弹窗中展示 6 个预置用户卡片（头像 + 昵称 + 偏好标签）

2. **用户画像展示区**：
   - 展示当前用户完整画像（分群、偏好、价格区间、RFM 评分）
   - 与后端 `UserProfileAgent` 返回的数据联动

3. **浏览历史 + 购买记录**：
   - 展示当前用户的浏览历史和模拟购买记录
   - 订单状态（已完成/配送中/待评价）

#### B-4：首页用户身份感知

**涉及文件**：修改 `python/frontend/home.html`，修改 `python/frontend/assets/home.js`

- 首页导航栏显示当前用户头像 + 昵称
- 个性化推荐标题："XXX，为你推荐"
- 切换用户后自动刷新推荐内容

### 4.3 交付物

1. `python/services/demo_users.py`：预置用户数据模块
2. 更新后的 `main.py`：3 个用户相关 API
3. 更新后的 `user.html` + `user.js`：多用户切换交互
4. 更新后的 `home.html` + `home.js`：首页用户身份感知

### 4.4 验收标准

- [ ] 个人中心可查看并切换 6 个预置用户
- [ ] 切换用户后推荐内容自动更新，体现画像差异
- [ ] 每个用户有独立的浏览历史和购买记录
- [ ] 首页显示当前用户身份信息

---

## 5. 开发者 C：前端交互升级（~25%）

### 5.1 目标

从前端交互层面提升"真实电商"感，包含购物车、订单流程、导航升级、页脚等。

### 5.2 核心任务

#### C-1：导航栏 + 全局 UI 升级

**涉及文件**：`python/frontend/assets/styles.css`，各页面 HTML

1. **导航栏升级**（所有 6 个页面的 header）：
   - 添加购物车图标 + 角标数字（从 localStorage 读取商品数量）
   - 购物车图标链接到 `/cart`
   - 添加消息通知铃铛图标（空态即可）

2. **商品卡片升级**（CSS + 各 JS 文件中卡片模板）：
   - 评分使用 ★ 星星图标（如 ★★★★☆）替代纯数字
   - 销量显示从 `9800` 改为"已售 9800+"
   - 价格展示增加划线原价 + "立减"优惠标签

3. **页面底部**（所有页面）：
   - 添加电商风格页脚：关于我们 | 帮助中心 | 联系客服 | 隐私政策 | 营业执照

#### C-2：购物车功能

**涉及文件**：新建 `python/frontend/cart.html`，新建 `python/frontend/assets/cart.js`

- 任何商品卡片可"加入购物车"（存入 `localStorage`，key 按用户隔离：`cart_{user_id}`）
- 购物车页面展示：商品图片 + 名称 + 单价 + 数量调整 + 小计 + 删除
- 底部合计金额 + "去结算"按钮
- 空购物车时显示引导："购物车空空如也，去逛逛吧 →"
- 导航栏购物车角标实时更新

#### C-3：订单模拟流程

**涉及文件**：新建 `python/frontend/assets/order.js`，修改 `python/frontend/assets/product.js`

- 商品详情页"立即购买" → 弹出订单确认面板：
  - 收货地址（预置 2 个演示地址可选）
  - 支付方式选择（支付宝/微信/银行卡）
  - 商品信息确认
- 提交订单 → 显示"下单成功"页面（订单号 + 预计送达时间）
- 订单记录存入 `localStorage`（key: `orders_{user_id}`）
- 个人中心可查看历史订单列表

#### C-4：评价系统前端

**涉及文件**：修改 `python/frontend/assets/product.js`

- 商品详情页"用户评价"Tab：
  - 从后端 `GET /api/v1/product/{id}/reviews` 获取评价数据
  - 每条评价：用户头像（彩色首字母圆）+ 昵称 + ★ 星级 + 评价文字 + 时间
  - 支持按评分筛选（全部/好评/中评/差评）
  - 无评价时显示"暂无评价"

### 5.3 交付物

1. `python/frontend/cart.html` + `python/frontend/assets/cart.js`：购物车页面
2. `python/frontend/assets/order.js`：订单流程逻辑
3. 更新后的 `styles.css`：全局 UI 升级（导航栏、卡片、页脚）
4. 各页面 HTML 中导航栏和页脚的更新

### 5.4 验收标准

- [ ] 导航栏有购物车图标 + 数量角标
- [ ] 任何商品卡片可一键加入购物车
- [ ] 购物车页面可修改数量、删除、查看合计
- [ ] "立即购买"触发完整下单流程
- [ ] 订单记录可在个人中心查看
- [ ] 页面底部有电商风格页脚
- [ ] 评价 Tab 可正常展示评价数据

---

## 6. 开发者 D：后端服务 + 数据完善（~25%）

### 6.1 目标

从后端数据和接口层面提升仿真度，为前端提供评价、订单、推荐理由等数据支撑。

### 6.2 核心任务

#### D-1：评价数据与 API

**涉及文件**：新建 `python/services/review_service.py`，修改 `python/main.py`

- `ReviewService`：为每个商品生成 5-8 条模拟评价
- 评价包含：用户昵称、评分（1-5 星）、评价文字、评价时间、点赞数
- 覆盖好评/中评/差评场景
- 新增 API：
  - `GET /api/v1/product/{product_id}/reviews`：分页获取评价
  - `GET /api/v1/product/{product_id}/review-summary`：评价汇总（好评率、各星级占比）

#### D-2：订单服务

**涉及文件**：新建 `python/services/order_service.py`，修改 `python/main.py`

- `OrderService`：管理模拟订单数据
- 为 6 个预置用户各生成 3-5 条历史订单（不同状态：已完成/配送中/待发货/待评价）
- 新增 API：
  - `POST /api/v1/orders`：创建新订单
  - `GET /api/v1/orders?user_id=xxx`：获取用户订单列表
  - `GET /api/v1/orders/{order_id}`：获取订单详情

#### D-3：商品数据丰富

**涉及文件**：`python/repositories/in_memory_product_repository.py`（与开发者 A 协作）

- 为 22 款商品补充 `description` 字段（100-200 字商品描述）
- 补充 `specs` 字段（详细规格参数字典）
- 确保标签、价格区间、库存分布合理
- 与开发者 A 协作完成精简后的商品数据合并

#### D-4：用户画像数据完善

**涉及文件**：修改 `python/agents/user_profile_agent.py`

- 预置用户匹配时直接返回预设画像（不依赖 LLM）
- 非预置用户走原有 LLM 推理链路
- 补充各预置用户的 `rfm_score` 计算逻辑

#### D-5：推荐接口数据丰富

**涉及文件**：修改 `python/services/catalog_service.py`，修改 `python/main.py`

- 推荐结果增加"推荐理由"字段（如"因为你最近浏览了手机"）
- 搜索接口支持按价格区间、品牌、评分筛选
- 分类接口返回每个分类的商品数量和价格区间

### 6.3 交付物

1. `python/services/review_service.py`：评价服务
2. `python/services/order_service.py`：订单服务
3. 更新后的商品数据（丰富 description/specs）
4. 更新后的 API 接口（评价、订单、推荐理由、搜索筛选）

### 6.4 验收标准

- [ ] 每个商品有 5+ 条评价，API 可正常获取
- [ ] 每个预置用户有 3+ 条历史订单
- [ ] 推荐结果包含推荐理由
- [ ] 搜索支持多维度筛选
- [ ] 预置用户画像直接返回，不依赖 LLM

---

## 7. 协作计划与联调节点

### 7.1 时间线

```
Day 1-2: 各自开发核心模块
  A: 下载图片 + 精简商品数据 + 填充图片路径
  B: 预置用户数据 + 切换 API
  C: 导航栏升级 + 购物车页面 + 页脚
  D: 评价服务 + 订单服务

Day 3-4: 功能集成
  A: 前端所有页面 emoji → 图片渲染改造
  B: 前端用户切换交互 + 首页身份感知
  C: 订单流程 + 评价 Tab 前端 + 卡片样式升级
  D: 商品数据丰富 + 用户画像完善 + 推荐理由

Day 5: 全员联调 + Bug 修复
  A+D: 商品数据合并确认（图片路径 + description/specs）
  B+C: 购物车数据随用户切换隔离
  全员: 接口联调、数据一致性、UI 适配

Day 6: 演示彩排 + 文档
  全员: 演示脚本、PPT 更新、README 更新
```

### 7.2 接口依赖关系

```
开发者 D (评价/订单/推荐理由 API)
    ↓ 提供接口
开发者 C (购物车/订单/评价前端)     开发者 A (图片渲染)
    ↓                                    ↓
    └─────────── 开发者 B (用户切换) ─────┘
                     ↓
                全员联调
```

### 7.3 交叉配合

| 配合方 | 配合内容 |
|--------|---------|
| A ↔ D | 商品数据协作：A 负责精简+图片路径，D 负责 description/specs，Day 5 合并 |
| A → C | 提供商品 image_url 格式规范，C 适配卡片 CSS（图片容器尺寸等） |
| B → C | 提供用户切换事件 + 用户 ID，C 实现购物车按用户隔离 |
| D → C | 提供评价 API 和订单 API，C 实现前端对接 |
| 全员 | Day 5 联调日统一解决接口/数据/样式问题 |

---

## 8. 文件变更清单

### 新建文件

| 文件 | 负责人 | 说明 |
|------|--------|------|
| `python/frontend/assets/images/products/` | A | 本地商品图片目录（~49 张图片） |
| `python/services/demo_users.py` | B | 预置用户数据 |
| `python/services/review_service.py` | D | 评价数据服务 |
| `python/services/order_service.py` | D | 订单模拟服务 |
| `python/frontend/cart.html` | C | 购物车页面 |
| `python/frontend/assets/cart.js` | C | 购物车交互逻辑 |
| `python/frontend/assets/order.js` | C | 订单流程逻辑 |

### 修改文件

| 文件 | 负责人 | 修改内容 |
|------|--------|---------|
| `python/repositories/in_memory_product_repository.py` | A + D | 精简至 22 款 + image_url + description/specs |
| `python/main.py` | B + D | 新增用户/评价/订单 API |
| `python/agents/user_profile_agent.py` | D | 预置用户画像直出 |
| `python/services/catalog_service.py` | D | 推荐理由、搜索筛选增强 |
| `python/frontend/home.html` | A + B + C | 图片渲染 + 用户身份 + 导航升级 + 页脚 |
| `python/frontend/assets/home.js` | A + B | 图片渲染 + 用户感知 |
| `python/frontend/assets/home.css` | C | 卡片图片样式 + 页脚 |
| `python/frontend/user.html` | B + C | 多用户切换 UI |
| `python/frontend/assets/user.js` | B + C | 用户切换交互 + 购买记录 |
| `python/frontend/product.html` | C | 详情页评价 Tab |
| `python/frontend/assets/product.js` | A + C | 图片渲染 + 评价对接 + 下单流程 |
| `python/frontend/category.html` | A | 分类页图片渲染 |
| `python/frontend/assets/category.js` | A | 分类页图片渲染逻辑 |
| `python/frontend/search.html` | A | 搜索页图片渲染 |
| `python/frontend/assets/search.js` | A | 搜索页图片渲染逻辑 |
| `python/frontend/assets/styles.css` | C | 导航栏/卡片/页脚全局样式 |
| `python/frontend/admin.html` | D | 管理端数据完善 |

---

## 9. 验收清单（答辩演示用）

### 演示脚本建议（3-5 分钟）

1. **开场（30s）**：打开首页，展示整体 UI，强调"多 Agent 协同的电商推荐系统"
2. **多用户体验（60s）**：个人中心切换用户 → 首页推荐变化 → 展示画像差异
3. **真实图片（30s）**：商品卡片真实产品图 + 详情页多图 gallery
4. **购物体验（60s）**：浏览 → 加入购物车 → 购物车页面 → 下单流程
5. **推荐引擎（60s）**：四个推荐楼层 + 搜索 + 推荐理由
6. **管理端（30s）**：A/B 实验数据 + 监控指标

### 最终验收标准

| 检查项 | 通过标准 |
|--------|---------|
| 商品图片 | 22 款商品显示本地真实产品图，失败有 fallback |
| 多用户 | 6 个预置用户，可切换，各有独立画像和推荐 |
| 购物车 | 可加购、改数量、删除、查看合计 |
| 订单 | 可下单、查看历史订单、订单状态 |
| 评价 | 每商品有评价数据，支持星级筛选 |
| 推荐差异化 | 不同用户推荐结果明显不同 |
| UI 真实感 | 导航栏角标、评分星星、电商页脚 |
| 移动端适配 | 375px 宽度下布局正常 |
