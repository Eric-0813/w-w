# Research skills

这个仓库包含两个可独立使用的 skill：

| Skill | 用途 | 入口 |
| --- | --- | --- |
| `finance` | 有来源的证券研究、新闻影响分析，以及持仓 CSV 的市值与权重计算 | [SKILL.md](skills/finance/SKILL.md) |
| `github-workbench` | 调研 GitHub 项目、核对仓库访问、整理并发布项目变更 | [SKILL.md](skills/github-workbench/SKILL.md) |

`github-workbench` 中的 [金融接入检查清单](skills/github-workbench/references/finance-integrations.md) 用于评价金融软件；[手机触觉反馈](skills/github-workbench/references/native-haptics.md) 已独立。实际证券和持仓分析使用 `finance`。

## 使用 finance

将完整的 `skills/finance` 文件夹放进目标项目的 `.agents/skills/`，或使用 skill-installer 从本仓库安装指定目录。目录约定见 [OpenAI 官方 skills 文档](https://learn.chatgpt.com/docs/build-skills)。本仓库的 `skills/` 是分发目录，仅下载仓库并不等于已安装。

安装后可这样请求：

- `使用 $finance 分析某公司的最新财报，列出来源、主要变化和仍未验证的假设。`
- `使用 $finance 检查这份持仓 CSV，按 USD 计算市值和集中度，指出过期数据。`
- `使用 $finance 分析这条新闻可能影响哪些持仓，区分直接证据和推测。`

研究流程需要可用的搜索或数据工具，或由用户提供来源材料。随附的计算脚本仅使用本地 CSV，不联网、不需要 API key，也不连接券商。

## 运行持仓示例

需要 Python 3.9 或更新版本，无第三方依赖。在仓库根目录运行：

```bash
python3 skills/finance/scripts/portfolio_snapshot.py \
  skills/finance/assets/portfolio.example.csv \
  --base-currency USD \
  --as-of 2026-11-12T00:00:00Z
```

示例标的是虚构的，报价和汇率仅供验证计算。预期总市值为 `100 USD`，两项权重为 `40%`、`60%`，并提示汇率时间未经核实。真实输入可放在忽略提交的 `data/` 目录，输出可保存到 `reports/`；提交前仍需检查实际文件清单。

CSV 必须包含 `symbol,quantity,price,currency,price_as_of,fx_to_base`。字段规则和结果解释见 [输入说明](skills/finance/references/portfolio-input.md)。输出为 JSON；金额和权重用十进制字符串表示，避免 JSON 浮点转换造成精度丢失。

脚本计算 `数量 × 单价 × 换算汇率` 及其占比。汇率方向是每 1 单位报价币种对应的基准币种金额。输入校验失败会返回非零退出码；过期报价等限制会出现在输出的警告中。

此版本只支持多头现货持仓快照。不计算收益率、成本、税费或衍生品风险，也不把用户提供的报价当作已验证实时行情。报价币种占比不等于企业实际汇率风险；汇率时间需要另行记录与核实。

## 检查代码

```bash
python3 -m unittest discover -s tests -v
```

测试覆盖跨币种计算、数据校验、时间处理和命令行行为。研究报告可参考 [输出模板](skills/finance/assets/research-report-template.md)，按问题保留必要部分。
