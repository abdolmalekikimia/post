# EPS-73

## هدف

بررسی تغییر مقصد و chute قبل از بستن کیسه، تخصیص تکراری و حفظ state.

## معماری و دامنه

- **دامنه:** بخش ۳ — تصمیم‌گیری و تخصیص مقصد و شوتر (`tests/3_destination/`)
- **ماژول تست:** `tests/3_destination/test_destination_and_chute_assignment.py`

## وضعیت پوشش

- Positive: `Implemented`
- Negative: `Implemented`
- Stress: `Implemented`
- Protocol: `SignalR`
- Dependency: `Ready` — Bag و Destination fixture

## نحوهٔ اجرا

### تست‌های Success (TC-01 تا TC-04)
```powershell
$env:RUN_E2E="1"
.venv\Scripts\python.exe -m pytest tests/3_destination -m eps73_success -q -s
```

### تست‌های Negative (TC-05)
```powershell
$env:RUN_E2E="1"
$env:RUN_EPS73_NEGATIVE="1"
$env:EPS73_CASE="all"
.venv\Scripts\python.exe -m pytest tests/3_destination -m eps73_negative -q -s
```

### Stress (TC-06)
```powershell
$env:RUN_E2E="1"
$env:RUN_EPS73_STRESS="1"
.venv\Scripts\python.exe -m pytest tests/stress/test_eps73_stress.py -q -s
```

### اجرای کلی EPS-73
```powershell
$env:RUN_E2E="1"
$env:RUN_EPS73_NEGATIVE="1"
$env:RUN_EPS73_STRESS="1"
.venv\Scripts\python.exe -m pytest tests/3_destination tests/stress/test_eps73_stress.py -m "eps73_success or eps73_negative" -q -s
```

جزئیات: [EPS73.md](../EPS73.md)