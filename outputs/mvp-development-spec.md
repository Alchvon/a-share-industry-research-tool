# A股产业链龙头分析器 MVP 开发规格

生成日期：2026-06-16

## 1. MVP 定位

第一版目标不是做完整金融终端，而是验证核心闭环：

用户输入行业关键词 -> AI 拆解产业链 -> 匹配 A 股候选公司 -> 展示股票基础分析 -> 用户调用自有大模型生成研究结论。

第一版产品表述建议使用“候选龙头”或“重点公司”，避免直接宣称某公司就是绝对龙头。

## 2. MVP 功能范围

### 2.1 首页

功能：
- 输入行业/领域关键词。
- 创建分析任务。
- 展示最近分析记录。

核心接口：

```http
POST /api/analysis
GET /api/history
```

### 2.2 分析工作台

三栏布局：

- 左栏：产业链子领域列表。
- 中栏：候选公司表格 + 股票详情。
- 右栏：AI 分析面板。

第一版使用树形列表或分组列表，不做 D3 力导向图。

### 2.3 产业链拆解

输入：行业关键词。

输出：5-8 个适合 A 股研究的子领域，每个子领域包含：

- name
- level
- description
- match_keywords

LLM 只负责产业链语义拆解，不直接推荐股票。

### 2.4 候选公司匹配

匹配流程：

```text
子领域关键词
-> 概念板块/行业板块检索
-> 候选股票池
-> 基于市值、营收、ROE、相关性评分排序
-> 返回每个子领域前 3-5 家公司
```

评分初版：

```text
score =
  market_cap_rank_score * 0.35
+ revenue_rank_score * 0.25
+ roe_rank_score * 0.20
+ relevance_score * 0.20
```

用户必须可以手动删除、添加、调整候选公司。

### 2.5 股票基础分析

第一版字段：

- 股票代码
- 股票名称
- 所属行业
- 最新价
- 涨跌幅
- PE TTM
- PB
- PS
- 总市值
- 流通市值
- 近 5 年营业收入
- 近 5 年归母净利润
- ROE
- 毛利率
- 资产负债率
- 日 K 数据

第一版暂缓：

- 研报
- 新闻舆情
- 北向资金
- 融资融券
- 估值分位
- PDF 报告导出

### 2.6 AI 分析

用户配置：

- Endpoint
- API Key
- Model
- Temperature

后端仅做透明代理，不落库保存 API Key。

预设分析维度：

- 估值合理性
- 财务健康度
- 行业地位
- 主要风险

输出 Markdown。

## 3. 数据源验证结果

已安装并尝试 AKShare `1.18.64`。

验证脚本：

```text
work/akshare_probe.py
```

验证接口：

- `stock_zh_a_spot_em`
- `stock_individual_info_em`
- `stock_zh_a_hist`
- `stock_financial_analysis_indicator`
- `stock_board_concept_name_em`
- `stock_board_concept_cons_em`

当前环境结果：

- 包安装成功。
- 沙箱内访问被系统网络权限拦截。
- 放行网络权限后，东方财富相关接口通过代理返回 `ProxyError: Remote end closed connection without response`。
- 清理代理变量后直连超时。
- 新浪财务指标接口未报网络错误时返回空 DataFrame，需要继续验证替代接口。

结论：

AKShare 可以作为 MVP 主数据源，但不能假设所有部署环境都稳定可达。数据服务层必须具备以下能力：

- 单接口超时控制。
- 错误重试。
- 结果缓存。
- 数据源降级。
- 接口可替换。

建议第一版数据层不要把 AKShare 调用散落在业务代码里，必须集中封装。

## 4. 后端架构

推荐目录：

```text
backend/
  app/
    main.py
    api/
      analysis.py
      industry.py
      stock.py
      llm.py
    services/
      industry_service.py
      company_match_service.py
      stock_data_service.py
      akshare_provider.py
      llm_service.py
      cache_service.py
    models/
      analysis.py
      industry_node.py
      company_candidate.py
      stock_snapshot.py
      llm_report.py
    db.py
```

核心原则：

- `akshare_provider.py` 只负责原始数据获取。
- `stock_data_service.py` 负责字段归一化。
- `company_match_service.py` 负责候选公司评分。
- API 层不直接调用 AKShare。

## 5. API 规格

```http
POST /api/analysis
GET /api/analysis/{analysis_id}
POST /api/industry/decompose
POST /api/company/match
GET /api/stock/{code}/summary
GET /api/stock/{code}/financial
GET /api/stock/{code}/kline
POST /api/llm/analyze
```

### 5.1 创建分析

```http
POST /api/analysis
Content-Type: application/json

{
  "keyword": "人工智能"
}
```

返回：

```json
{
  "analysis_id": "uuid",
  "keyword": "人工智能",
  "status": "created"
}
```

### 5.2 产业链拆解

```http
POST /api/industry/decompose
Content-Type: application/json

{
  "analysis_id": "uuid",
  "keyword": "人工智能"
}
```

返回：

```json
{
  "nodes": [
    {
      "id": "uuid",
      "name": "AI芯片",
      "level": 1,
      "description": "提供模型训练和推理所需的算力芯片。",
      "match_keywords": ["AI芯片", "GPU", "算力芯片", "半导体"]
    }
  ]
}
```

### 5.3 股票摘要

```http
GET /api/stock/688256/summary
```

返回：

```json
{
  "code": "688256",
  "name": "寒武纪",
  "industry": "半导体",
  "latest_price": 0,
  "change_pct": 0,
  "pe_ttm": null,
  "pb": null,
  "ps": null,
  "market_cap": null,
  "float_market_cap": null,
  "data_time": "2026-06-16T15:00:00+08:00"
}
```

## 6. 数据库模型

```sql
CREATE TABLE analysis (
  id TEXT PRIMARY KEY,
  keyword TEXT NOT NULL,
  status TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE industry_node (
  id TEXT PRIMARY KEY,
  analysis_id TEXT NOT NULL,
  parent_id TEXT,
  name TEXT NOT NULL,
  level INTEGER NOT NULL,
  description TEXT,
  match_keywords TEXT NOT NULL,
  sort_order INTEGER NOT NULL
);

CREATE TABLE company_candidate (
  id TEXT PRIMARY KEY,
  analysis_id TEXT NOT NULL,
  industry_node_id TEXT NOT NULL,
  stock_code TEXT NOT NULL,
  stock_name TEXT NOT NULL,
  reason TEXT,
  market_cap REAL,
  revenue REAL,
  roe REAL,
  score REAL,
  is_user_selected INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE stock_snapshot (
  stock_code TEXT PRIMARY KEY,
  payload TEXT NOT NULL,
  fetched_at TEXT NOT NULL,
  expires_at TEXT NOT NULL
);

CREATE TABLE llm_report (
  id TEXT PRIMARY KEY,
  analysis_id TEXT NOT NULL,
  stock_code TEXT NOT NULL,
  report_type TEXT NOT NULL,
  markdown TEXT NOT NULL,
  created_at TEXT NOT NULL
);
```

## 7. Prompt 初版

### 7.1 产业链拆解

```text
你是A股产业链研究助手。
请将用户输入的行业主题拆解为适合A股公司研究的产业链子领域。

要求：
1. 输出 5-8 个子领域
2. 每个子领域给出简短说明
3. 每个子领域给出 3-5 个用于匹配A股概念板块或行业板块的关键词
4. 不要直接推荐股票
5. 只输出 JSON，不要输出解释文字

用户输入：{keyword}
```

### 7.2 股票研究

```text
你是A股股票研究助手。
请基于以下结构化数据，对公司进行研究分析。

要求：
1. 不得给出买入、卖出、持有等投资建议
2. 明确区分事实、推断和风险
3. 输出 Markdown

分析维度：
1. 公司在产业链中的位置
2. 估值水平
3. 财务质量
4. 成长逻辑
5. 主要风险

股票数据：
{stock_data}

产业链上下文：
{industry_context}
```

## 8. 开发顺序

### Phase 1：后端骨架与数据层

- FastAPI 项目初始化。
- SQLite 初始化。
- AKShare Provider 封装。
- 超时、缓存、错误降级。
- 股票摘要接口。

### Phase 2：产业链与候选公司

- LLM 产业链拆解。
- 概念/行业板块匹配。
- 候选公司评分。
- 人工调整接口。

### Phase 3：前端工作台

- React + Vite 初始化。
- 三栏布局。
- 首页输入。
- 产业链列表。
- 候选公司表格。
- 股票详情。

### Phase 4：AI 分析

- API 设置。
- LLM 代理。
- Markdown 渲染。
- 报告保存。

## 9. 第一版验收标准

输入“人工智能”后：

1. 能拆出 5-8 个合理子领域。
2. 每个子领域能展示 3-5 家候选 A 股公司。
3. 点击公司能看到基础行情、估值、财务和 K线。
4. 用户配置大模型 API 后能生成结构化研究分析。
5. 数据接口异常时，页面能展示明确错误，不影响其他模块。
6. 页面显著展示“仅供研究参考，不构成投资建议”。

