# EPS-53

## هدف

بررسی `RegisterInbound`، سابقهٔ Core، وضعیت Returning/Rejected و discrepancy.

## وضعیت پوشش

- Positive: `Implemented`
- Negative: `Implemented`
- Stress: `Implemented`
- Protocol: `SignalR`
- Dependency: `Partial / External Dependency` — Core HistoryRecord برای بخشی از Caseها

## Success

```powershell
$env:RUN_E2E="1"
.venv\Scripts\python.exe -m pytest tests/success/test_task_success.py -m eps53_success -q -s
```

## Negative

```powershell
$env:RUN_E2E="1"
$env:RUN_EPS53_NEGATIVE="1"
.venv\Scripts\python.exe -m pytest tests/negative/test_eps53_negative.py -q -s
```

Caseهای قابل اجرا:

`invalid_barcode`، `invalid_barcode_length`، `negative_weight`،
`invalid_dimensions`، `core_rejected_with_destination`،
`core_rejected_without_destination`، `core_timeout`، `core_unavailable`،
`weight_discrepancy`، `dimensions_discrepancy`

Caseهای وابسته به Core باید با HistoryRecordهای مناسب در Mock آماده شوند.

## Stress

```powershell
$env:RUN_E2E="1"
$env:RUN_EPS53_STRESS="1"
.venv\Scripts\python.exe -m pytest tests/stress/test_eps53_stress.py -q -s
```

جزئیات: [EPS53.md](../EPS53.md)
