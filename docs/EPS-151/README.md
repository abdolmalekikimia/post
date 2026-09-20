# EPS-151: Chaos/Crash در مقیاس بار تولیدی

> **تیم:** B  |  **اولویت:** Medium  |  **نوع:** Task  |  **اپیک:** (Edge) یکپارچه‌سازی واقعی پست، سخت‌سازی QA استقرار پایلوت

---

## 🎯 هدف و شرح تسک

گسترش تست پایه G2-08 (تست کرش ساده) به **تست Chaos Injection در مقیاس بار تولیدی (500+ درخواست همزمان)**. پس از تزریق خطا (Crash، خرابی Storage، Partition شبکه)، با استفاده از Snapshot های SQLite/Queue تایید می‌کنیم که **هیچ داده‌ای از بین نمی‌رود (Zero Data Loss)**.

---

## 📋 ماتریس سناریوهای BDD و ۴ پیشنهاد تکمیلی

| شناسه | عنوان سناریو | هدف آزمون | اعتبارسنجی‌های جدید (۴ پیشنهاد) |
|-------|-------------|-----------|--------------------------------|
| **TC-01** | کرش سرویس در بار تولیدی با ریکاوری بدون از دست رفتن داده | تزریق Crash تحت 50+ درخواست همزمان و تایید Zero Data Loss | ✅ اندازه‌گیری زنده Latency (`time.perf_counter`)<br>✅ چرخه‌های تکراری Chaos (۳ بار متوالی)<br>✅ ثبت تایم‌لاین رویدادها و محاسبه RTO |
| **TC-02** | خرابی SQLite Queue با State قابل بازپخش | تایید ساختار Snapshot و بازیابی پس از تخریب | ✅ بازیابی مکانیزم Queue |
| **TC-03** | Partition شبکه با Pool سالم | تایید سلامت اتصالات پس از قطع شبکه | ✅ بررسی Active/Idle اتصالات |
| **TC-04** | مقیاس کم با حفظ یکپارچگی | تایید یکپارچگی داده و Latency Slips | ✅ اندازه‌گیری زنده Latency Samples |
| **TC-05** | مقیاس متوسط با فراتر رفتن از آستانه‌ها | تایید p50/p95/p99 Latency Slips | ✅ نمونه‌برداری زنده همزمان |

---

## 🚀 ۴ پیشنهاد پیاده‌سازی‌شده

### پیشنهاد ۱: اندازه‌گیری زنده Latency (Live Latency Measurement)
- هر درخواست با `time.perf_counter()` زمان‌سنجی دقیق انجام می‌شود
- محاسبه واقعی p50/p95/p99 به جای مقادیر هاردکد
- اعتبارسنجی تعداد نمونه‌ها و مقدار Latency هر نمونه

### پیشنهاد ۲: تزریق Chaos چند استراتژی (Multi-Strategy Chaos Injection)
- استراتژی `mock`: استثنای شبیه‌سازی‌شده برای تست‌های روتین
- استراتژی `process`: ارسال سیگنال SIGTERM به پروسه Core (فقط با متغیر محیطی `USE_REAL_CHAOS=1`)

### پیشنهاد ۳: چرخه‌های تکراری Chaos (Repeated Chaos Cycles)
- TC-01 به صورت پیش‌فرض ۳ بار متوالی Crash → Recover را تکرار می‌کند
- هر چرخه: تزریق Crash → بررسی Manifest → ریکاوری → تایید Zero Data Loss
- اعتبارسنجی نهایی: تایید عدم تخریب تجمعی (No Cumulative Degradation)

### پیشنهاد ۴: ثبت تایم‌لاین رویدادها و محاسبه RTO
- ثبت دقیق لحظه هر مرحله (CHAOS_INJECTED → CRASH_DETECTED → RECOVERY_STARTED → RECOVERY_VERIFIED)
- محاسبه RTO (Recovery Time Objective) = زمان بین CRASH_DETECTED و RECOVERY_VERIFIED
- اعتبارسنجی RTO < SLA (پیش‌فرض: ۵ ثانیه)

---

## 🗂️ ساختار فایل‌ها

```
post/
├── assertions/
│   └── eps151_chaos_assertions.py       # الگوریتم‌های اعتبارسنجی (شامل ۴ پیشنهاد)
├── flows/
│   └── chaos/
│       └── eps151_chaos_flow.py         # فلوی اجرایی BDD با ExecutionReport
├── tests/
│   ├── unit/
│   │   └── test_eps151_core.py          # ۳۸ تست یونیت
│   └── stress/
│       └── test_eps151_chaos.py         # ۶ تست استرس/کاوز گیت‌شده
└── docs/
    └── EPS-151/
        └── README.md                    # همین فایل
```

---

## 🚀 راهنمای اجرای آزمون

### ۱. اجرای تست‌های یونیت
```powershell
python -m pytest tests/unit/test_eps151_core.py -v
```

### ۲. اجرای تست‌های استرس/کاوز (گیت‌شده)
```powershell
$env:RUN_EPS151="1"
python -m pytest tests/stress/test_eps151_chaos.py -v -s
```

### ۳. اجرای کامل با تزریق واقعی Chaos
```powershell
$env:RUN_EPS151="1"
$env:USE_REAL_CHAOS="1"
python -m pytest tests/stress/test_eps151_chaos.py -v -s
```

---

## 📊 خروجی نمونه

```
Execution report: EPS-151/TC-01: Service crash under production load recovers with zero data loss
01. [PASS] apply_production_load_live
    responseReceived: "Applied 5 concurrent requests with live latency"
02. [PASS] record_event_timeline_and_rto
    responseReceived: "Event timeline logged & RTO verified within SLA"
03. [PASS] execute_repeated_chaos_cycles
    responseReceived: "Completed 3 consecutive chaos cycles with zero cumulative degradation"
04. [PASS] verify_zero_data_loss
    responseReceived: "Zero data loss confirmed across all 3 cycles (5/5)"
Result: PASS=4, FAIL=0, NOT_CHECKED=0
```
