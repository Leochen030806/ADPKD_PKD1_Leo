# PKD1 PGT-M STR Panel · 项目备份与平台复现包

本目录是 PKD1（ADPKD）PGT-M STR 连锁 panel 研发项目的知识备份，也是平台复现包，供同事共享背景、在其他电脑或其他 Claude 账号上复现整个平台。
内容整理自与 Claude 的历次对话、Claude Code 会话、已发布的页面（artifact）和 5 个 PGT-M skill。数据截至 2026-11-19。

## 从哪里开始读

| 你想… | 看这里 |
|---|---|
| 了解生物医学背景（ADPKD、连锁分析、通用尾、12-plex panel、CE 结果） | [`docs/01_生物医学背景与项目知识.md`](docs/01_生物医学背景与项目知识.md) |
| 在自己电脑上跑起平台、装 skill、生成下单表 | [`docs/02_平台架构与复现指南.md`](docs/02_平台架构与复现指南.md) |
| 查找所有资料的原始链接，以及还缺什么 | [`docs/03_资料索引与缺失清单.md`](docs/03_资料索引与缺失清单.md) |

## 目录结构

```
PGTM_PKD1_backup/
├── README.md                     本文件
├── requirements.txt              Python 依赖
├── docs/                         三份说明文档（背景 / 复现 / 索引）
├── skills/                       5 个流程 skill 的完整源码，可直接装进 Claude
│   ├── pgtm-str-panel-design/      基因名 → 候选 STR → 颜色×长度网格 → Primer3
│   ├── pgtm-str-panel-order/       保留/重设计 → 通用尾 → QC → 下单表.xlsx
│   ├── pgtm-gel-titration-report/  胶图 → 标准报告 PPT
│   ├── pgtm-ce-report-slides/      GeneMapper 截图 → CE 报告 PPT + 汇总表维护
│   └── str-csv-allele-report/      SeqStudio CSV → LIZ-500 校准 → 等位基因判读
├── platform/panel_studio/        平台前端 PGT-M Panel Studio（源码 + PKD1/PKD2 run 数据 + 13 个 marker 的 CE 数据）
├── slides/                       平台立项组会 slides，共 14 页（HTML，含演讲备注）
├── artifacts_html/               11 个独立网页工具和文档（浏览器直接打开）
└── tools/
    ├── install_skills.sh / .ps1    把 skill 安装到 Claude Code，或打包成 zip 上传到 claude.ai
    └── export_local_claude_sessions.py   从本地 Claude Code 记录或 claude.ai 数据导出中提取相关对话
```

## 三分钟快速体验

```bash
pip install -r requirements.txt
```

```bash
cd skills && python3 pgtm-str-panel-order/scripts/build_order_list.py pgtm-str-panel-order/examples/pkd1_records.json -o 下单表.xlsx
```

```bash
cd platform/panel_studio && python3 -m http.server 8000
```

第三条命令运行后，用浏览器打开 http://localhost:8000 就能看到 Panel Studio。

## 重要提示

- **备份还不完整**：平台后端（`trexplorer_str.py` 和本地 MCP 服务）、`ce_sheet.py`，以及实验室电脑 Desktop 上的原始数据表和截图，只存在于那台 Windows 电脑上。补齐方法见 03 号文档的 D 节。
- **涉及临床数据**：本仓库只包含 Coriell 参考样本的数据。真实病例或家系数据**不要**提交到这里。
- 平台的边界是交付 multiplex panel 为止：不做家系单倍型分析，不判读胚胎结果，不出临床报告。
