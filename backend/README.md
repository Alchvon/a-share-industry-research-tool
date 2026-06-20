# A股产业链龙头分析器 Backend

MVP 后端骨架，当前包含：

- FastAPI 应用入口
- SQLite 表初始化
- AKShare 数据 provider 封装
- 股票摘要服务
- 缓存层
- 健康检查接口

## 本地运行

```powershell
& "C:\Users\a1195\Documents\Codex\2026-06-16\new-chat\backend\run_stable.ps1"
```

接口文档：

```text
http://127.0.0.1:8000/docs
```

## 当前接口

```http
GET /health
GET /api/data-source/diagnostics
POST /api/analysis
GET /api/analysis/{analysis_id}
DELETE /api/analysis/{analysis_id}
GET /api/history
POST /api/industry/decompose
POST /api/industry/nodes
PATCH /api/industry/nodes/{node_id}
DELETE /api/industry/nodes/{node_id}
GET /api/company
POST /api/company
PATCH /api/company/{candidate_id}
DELETE /api/company/{candidate_id}
POST /api/company/match
POST /api/valuation/calculate
POST /api/llm/analyze
GET /api/stock/{code}/summary
GET /api/stock/{code}/kline
GET /api/stock/{code}/financial
```

## 数据源说明

当前 provider 采用多源策略：摘要和K线优先使用 Sina，K线继续回退 efinance、Baostock、AKShare；估值和财务字段按 AKShare、Tushare、efinance、本地快照逐级补全。

本机验证结果显示，AKShare 包可以安装，但东方财富相关接口在当前代理/网络环境下可能返回 `ProxyError` 或超时。因此服务层已经做了集中封装：

- API 层不直接调用 AKShare。
- `stock_data_service.py` 统一处理缓存和 provider 错误。
- provider 异常时返回结构化响应，并把错误放入 `warnings`。
- `/api/data-source/diagnostics` 可主动检查 AKShare、Baostock、efinance、Sina、Tushare 可选源的安装与远程接口状态。
- `local_knowledge.py` 提供本地行业拆分和候选公司兜底，`/api/knowledge/topics` 返回当前覆盖主题。
- `valuation_service.py` 提供固定估值方法计算，`/api/valuation/calculate` 返回估值方法表和 Markdown。

Tushare 为可选正式数据源：设置环境变量 `STOCK_CHAIN_TUSHARE_TOKEN` 后会自动参与摘要和财务补全；未配置时会静默跳过。后续还可以继续增加聚宽、东方财富正式接口或自建缓存数据。







