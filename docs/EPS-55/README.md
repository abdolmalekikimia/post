# EPS-55

## هدف

بررسی ثبت مرسوله، polling و رفتارهای Postal در مسیر inbound.

## وضعیت پوشش

- Positive: `Missing`
- Negative: `Implemented`
- Stress: `Implemented`
- Protocol: `SignalR`
- Dependency: `Blocked / External Dependency` — Postal Mock profile و barcode fixture

## Negative

```powershell
$env:RUN_E2E="1"
$env:RUN_EPS55_NEGATIVE="1"
.venv\Scripts\python.exe -m pytest tests/negative/test_eps55_negative.py -q -s
```

Caseهای قابل اجرا:

`mismatching_24_digit_barcodes`، `mixed_14_and_24_digit_barcodes`،
`mismatching_14_digit_barcodes`، `mismatching_24_prefix_in_37_digit_barcode`،
`postal_rejected`، `postal_timeout`، `postal_unavailable`، `postal_pending`،
`destination_rejected`، `destination_timeout`، `destination_unavailable`،
`merge_rejected`، `returning`

## Stress

```powershell
$env:RUN_E2E="1"
$env:RUN_EPS55_STRESS="1"
.venv\Scripts\python.exe -m pytest tests/stress/test_eps55_stress.py -q -s
```

سناریوهای Postal به fixtureهای barcode و یک Mock scenario فعال نیاز دارند.
