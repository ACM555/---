# 法学审校回归测试说明

本目录用于把法学同学 Day3 的审校要求固化为自动测试，避免后续开发中出现不合规表述。

## 测试文件

- `day3_samples.json`：法学同学提供的审校样本，包括必需措辞、禁止措辞、人工复核要求。
- `test_day3_legal_review.py`：自动读取样本并调用 `run_audit()` 执行审校。

## 覆盖内容

当前测试覆盖：

1. 必需措辞必须出现，例如：
   - `可能面临缺乏显著性的审查风险`
   - `重要冲突线索`
   - `视觉相似候选`
   - `不能提供注册成功率`

2. 禁止措辞不得出现，例如：
   - `纯汉字商标必然被驳回`
   - `名称相同已经构成侵权`
   - `图形相似度高，构成侵权`
   - `国际大牌享有全类别保护`
   - `预计成功率`

3. 人工复核状态必须符合样本要求。

4. 样本中的 `expected_rule_ids` 必须被命中。

## 运行方式

在后端目录执行：

```powershell
cd E:\codex项目\本地电脑\西南政法智能体大赛\outbound-guard-backend
$env:PYTHONPATH='.'
.\venv\Scripts\python.exe -m unittest tests.test_day3_legal_review
```

完整后端测试：

```powershell
$env:PYTHONPATH='.'
.\venv\Scripts\python.exe -m unittest tests.test_day3_legal_review tests.test_vision_agent tests.test_audit_engine
```

## 风险等级说明

Day3 样本中的 `review` 表示“需要人工复核”。当前后端接口风险等级只有：

- `high`
- `medium`
- `low`

因此自动测试将 `review` 映射为：

- `manualReviewRequired = true`
- `riskLevel` 为 `medium` 或 `high`

这能保留法学审校语义，同时不破坏前端现有字段契约。
