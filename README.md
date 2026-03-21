# Auto Data Analyst Agent

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![CI](https://github.com/zyf1517142363-cpu/Auto-Data-Analyst-Agent/actions/workflows/ci.yml/badge.svg)](https://github.com/zyf1517142363-cpu/Auto-Data-Analyst-Agent/actions/workflows/ci.yml)

一个基于 LangChain + FastAPI 的数据分析智能体。用户上传 CSV 后，系统会自动完成基础清洗、特征分析、可视化、简单建模，并生成可下载的 PDF 报告。前端页面内输入你的 API Key 即可运行，服务端不会保存 Key。

## 功能概览
- CSV 上传与自动清洗（去重、空值处理、列名规范）
- 数值/类别特征统计与样例预览
- 可视化（分布图、相关性热力图、目标关系图）
- 简单建模（分类/回归或无监督聚类）
- 自动生成 PDF 分析报告
- FastAPI + 前端页面一体化运行
- Docker 封装一键部署

## 目录结构
```
.
├── app
│   ├── main.py            # FastAPI 服务入口
│   ├── pipeline.py        # 数据清洗、分析、建模与可视化
│   ├── reporting.py       # PDF 报告生成
│   ├── llm.py             # LLM 摘要生成
│   ├── reports/           # 报告输出目录
│   ├── tmp/               # 临时文件
│   └── static/            # 前端页面
├── main.py                # 启动入口
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── .dockerignore
```

## 运行要求
- Python 3.10+
- 需要用户自备 LLM API Key（在前端表单中输入）

## 本地运行
```bash
pip install -r requirements.txt
python main.py
```
浏览器访问：
```
http://127.0.0.1:8000
```

## Docker 运行
```bash
docker compose up --build
```
浏览器访问：
```
http://127.0.0.1:8000
```

## 使用说明
1. 打开首页，上传 CSV 文件  
2. 输入你的 API Key  
3. 可选填写目标列与任务类型（分类/回归），留空则自动判断  
4. 点击开始分析，生成结果与 PDF 报告  

## 网页 Demo
首页点击“运行网页演示”，将使用内置示例数据生成报告，不需要 API Key。示例 CSV 可在页面下载。

## API
### POST `/analyze`
表单字段：
- `file`: CSV 文件
- `api_key`: 用户 API Key（必填）
- `target`: 目标列名（可选）
- `task_type`: `classification` 或 `regression`（可选）

返回示例：
```json
{
  "run_id": "c5b0...",
  "report_url": "/reports/c5b0.../report.pdf",
  "summary": "...",
  "overview": {...},
  "modeling": {...},
  "warnings": []
}
```

### GET `/reports/{run_id}/report.pdf`
下载报告 PDF。

## 注意事项
- CSV 过大可能导致生成时间较长
- 模型与可视化为自动化简版流程，适合快速探索与初步分析

## 许可
本项目采用 [MIT License](./LICENSE)。
