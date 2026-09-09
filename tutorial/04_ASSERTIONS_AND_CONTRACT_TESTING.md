# ✅ اعتبارسنجی‌ها و تست قرارداد (Assertions & Contract Testing)

در این بخش بررسی می‌کنیم که چگونه اعتبارسنجی پاسخ‌ها (Assertions) در این پروژه پیاده‌سازی شده و چرا تفکیک این لایه اهمیت زیادی در پایداری تست‌ها دارد.

---

## ۱. چرا نباید Assert های خام را در تست‌ها پخش کرد؟

در روش سنتی، در هر فایل تست عباراتی شبیه به این نوشته می‌شود:
```python
# روش سنتی و نامناسب:
assert response.status_code == 200
assert response.json()["status"] == "SUCCESS"
assert response.json()["payload"]["data"]["sessionId"] != ""
```
**مشکلات روش سنتی:**
1. اگر نام فیلد در آینده از `sessionId` به `session_id` تغییر کند، باید صدها فایل تست را دستکاری کنید.
2. پیام‌های خطای پیش‌فرض پایتون در صورت بروز باگ، اطلاعات کافی از پاسخ کامل سرور نمی‌دهند.
3. تفاوتی بین خطای ساختاری (Malformed JSON) و خطای منطقی بیزنس قائل نمی‌شود.

---

## ۲. طراحی ماژولار لایه Assertions در این پروژه

در این پروژه، تمام بررسی‌ها در پوشه `assertions/` متمرکز شده‌اند:
- `assertions/http_assertions.py`: بررسی کدهای وضعیت HTTP
- `assertions/signalr_assertions.py`: بررسی فرمت استانداردهای SignalR، فیلدهای نتیجه، موفقیت و شکست
- `assertions/bag_assertions.py`: بررسی صحت بستن کیسه و کانتینر
- `assertions/negative_scenario_assertions.py`: بررسی کدهای خطای مورد انتظار در تست‌های منفی

### نمونه اعتبارسنجی پاسخ موفق SignalR (`assertions/signalr_assertions.py`):
```python
def assert_success_response(response: dict[str, Any], action_name: str) -> None:
    assert isinstance(response, dict), f"Expected dict response for {action_name}, got {type(response)}"
    # بررسی وجود فیلدهای پایه مانند success یا status
    status = response.get("status") or response.get("isSuccess")
    assert status in (True, "SUCCESS", "OK", "Success", 200), (
        f"{action_name} failed. Expected success status, but got response: {response}"
    )
```

---

## ۳. تست قرارداد (Contract Testing) چیست؟

تست قرارداد بررسی می‌کند که:
1. آیا تمام فیلدهای الزامی در پاسخ حضور دارند؟
2. آیا نوع داده‌های هر فیلد (String, Integer, Boolean, Array) درست است؟
3. آیا فیلدهای شناسه مانند `correlationId` و `sessionId` و `timestamp` با الگوهای معتبر همخوانی دارند؟

### مثال کاربردی:
در سناریوی بستن کیسه (`flows/bag/container_response_contract_flow.py`):
- بررسی می‌شود که پاسخ دریافتی شامل `sealNumber`، `totalCount`، `destinationCenterCode` و وضعیت نهایی باشد.
- در صورتی که سرور هر یک از این کلیدها را حذف کند، تست با یک پیام شفاف بلافاصله شکست می‌خورد و از بروز خطاهای پنهان در محیط Production جلوگیری می‌شود.
