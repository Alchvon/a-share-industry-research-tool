# A股产业链龙头分析器

MVP 原型当前包含：

- FastAPI 后端
- SQLite 本地数据库
- 多数据源封装：Sina、efinance、Baostock、AKShare、Tushare 可选接入
- OpenAI 兼容产业链拆解与分析代理，含常见平台预设
- AKShare 概念板块候选公司匹配，本地模板兜底
- 股票摘要、K线、财务指标接口与前端趋势图；摘要和K线优先使用当前网络下更稳定的新浪接口，估值/财务字段可由 efinance、Tushare 或本地快照补全
- 固定估值方法引擎：PE、PB、PS、PEG、股息率、PCF、EV/EBITDA、DCF、DDM、RIM、SOTP、可比交易法等
- 历史记录恢复与删除、候选公司表格导出、Markdown 报告导出、已保存报告回看
- 产业链节点与候选公司的手动增删改
- 候选公司评分来源与构成说明
- 本地行业知识库：覆盖 AI、半导体、新能源车、光伏、医药、消费电子、机器人、军工、食品饮料、游戏传媒、体育、固态电池、低空经济等常见主题
- 多数据源诊断入口、当前研究的 JSON 备份与导入恢复
- 无构建依赖的前端工作台

## 适合日常使用的启动方式

直接双击项目根目录的 `启动分析器.cmd`。它会自动检查本地服务、启动后端并打开网页；首次启动通常需要等待数秒。

## 手动启动后端

在 PowerShell 中运行：

```powershell
& "C:\Users\a1195\Documents\Codex\2026-06-16\new-chat\backend\run_stable.ps1"
```

开发时如果需要热重载，也可以运行 `backend\run.ps1`。

接口文档：

```text
http://127.0.0.1:8000/docs
```

## 打开前端

后端启动后，直接用浏览器打开：

```text
C:\Users\a1195\Documents\Codex\2026-06-16\new-chat\frontend\index.html
```

前端会调用：

```text
http://127.0.0.1:8000
```

## 当前流程

1. 输入行业关键词。搜索框会提示当前本地知识库支持的宽泛主题。
2. 创建分析任务。
3. 生成产业链子领域。
4. 匹配候选公司。后端会优先尝试 AKShare 概念板块检索，失败时回落到种子模板，并展示评分来源与构成。
5. 手动增删改产业链节点和候选公司。
6. 点击候选公司读取股票摘要。
7. 同步读取 K线和财务指标，并展示日线蜡烛图、净利润、ROE 趋势。
8. 在右侧生成 AI 分析。
9. 从历史记录恢复或删除分析，导出候选公司表格或 Markdown 分析报告。

## 当前接口

```http
GET  /health
POST /api/analysis
GET  /api/analysis/{analysis_id}
GET  /api/history
POST /api/industry/decompose
POST /api/industry/nodes
PATCH /api/industry/nodes/{node_id}
DELETE /api/analysis/{analysis_id}
DELETE /api/industry/nodes/{node_id}
POST /api/company/match
GET  /api/company
POST /api/company
PATCH /api/company/{candidate_id}
DELETE /api/company/{candidate_id}
GET  /api/stock/{code}/summary
GET  /api/stock/{code}/kline
GET  /api/stock/{code}/financial
POST /api/valuation/calculate
POST /api/llm/analyze
```

## 可选正式数据源

项目已预留 Tushare 接入。没有 Token 时会自动跳过，不影响本地试用；配置后会优先用于补充 PE/PB/PS、市值、行业、ROE、毛利率、资产负债率、营收和净利润等字段。

PowerShell 示例：

```powershell
$env:STOCK_CHAIN_TUSHARE_TOKEN="你的 Tushare Token"
& "C:\Users\a1195\Documents\Codex\2026-06-16\new-chat\backend\run_stable.ps1"
```

如果新环境尚未安装依赖，先在后端环境安装：

```powershell
& "C:\Users\a1195\Documents\Codex\2026-06-16\new-chat\work\.venv\Scripts\python.exe" -m pip install -r backend\requirements.txt
```
## AI 分析

右侧 AI 面板支持 OpenAI 兼容接口，这套配置会用于两处：

- 创建分析时的产业链拆解。
- 选择股票后的研究报告生成。

- 平台预设：OpenAI、DeepSeek、硅基流动、阿里云百炼、Z.ai / GLM、火山方舟，也可以选择自定义接口；模型名称可自由填写平台控制台里的 model id
- Endpoint，例如 `https://api.openai.com/v1`、`https://api.deepseek.com`、`https://api.siliconflow.cn/v1`、`https://dashscope.aliyuncs.com/compatible-mode/v1`
- API Key
- Model，例如 `gpt-4o`、`deepseek-chat`、`qwen-max`
- Temperature

API Key 不会写入后端数据库，也不会写入浏览器 localStorage。前端只会在点击分析按钮时把配置随请求发送给：

```http
POST /api/valuation/calculate
POST /api/llm/analyze
```

如果不填写 Endpoint/API Key/Model，后端会返回一份本地草稿分析，方便验证完整流程。

产业链拆解同样支持降级：如果没有填写 API 配置，或远程模型返回不可解析内容，后端会自动使用规则模板。

## 已知限制

- 产业链拆解已支持 OpenAI 兼容 LLM，失败时自动回落规则模板。
- 候选公司匹配已接 AKShare 概念板块检索，但当前网络/代理环境下可能超时；超时后会尽快回落到本地行业知识库。
- AKShare、Baostock、efinance 在当前代理/网络环境下可能超时，接口会返回结构化 `warnings`；当前摘要和K线已优先走新浪接口，前端“数据来源检查”按钮可查看各数据源状态。
- K线已接 Sina / efinance / Baostock / AKShare 多源回退；财务指标按 AKShare、Tushare、efinance、本地快照逐级回退，并在 `warnings` 中标明数据来源。
- AI 分析已支持 OpenAI 兼容代理；API Key 只随请求临时发送，不写入后端数据库。模型平台返回错误时，会显示 HTTP 状态码和平台返回正文，便于排查模型 ID、权限、余额或 endpoint 问题。












