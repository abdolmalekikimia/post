# EPS Coverage Matrix

مرجع وضعیت پوشش، پروتکل، وابستگی و نوع تست هر EPS. منبع metadata این جدول در
`config/eps_catalog.py` نگهداری می‌شود.

| EPS | Protocol | Positive | Negative | Stress | Dependency status | Main dependency |
|---|---|---|---|---|---|---|
| EPS-40 | Mixed | Implemented | Implemented | نیاز ندارد | Blocked / External Dependency | Core ConfigSnapshot و Restart |
| EPS-46 | Mixed | Implemented | Implemented | نیاز ندارد | Blocked / External Dependency | ConfigVersion و Policy snapshot |
| EPS-49 | Mixed | Implemented | Implemented | نیاز ندارد | Ready | Admin API و SignalR fixture |
| EPS-53 | SignalR | Implemented | Implemented | Implemented | Partial / External Dependency | Core HistoryRecord fixtures |
| EPS-55 | SignalR | Implemented | Implemented | Implemented | Blocked / External Dependency | Postal Mock profile و barcode fixture |
| EPS-60 | SignalR | Implemented | Implemented | Planned | Blocked / External Dependency | Global Postal Mock scenario |
| EPS-64 | SignalR | Implemented | Implemented | Planned | Partial / External Dependency | Lazy worker log/SQLite evidence |
| EPS-66 | SignalR | Partial / External Dependency | Partial / External Dependency | Planned | Partial / External Dependency | Core HistoryRecord و EdgeParcel/BagCloseAttempt state |
| EPS-68 | SignalR | Missing | Implemented | نیاز ندارد | Blocked / External Dependency | Core HistoryRecord fixtures |
| EPS-71 | SignalR | Implemented | Implemented | Planned | Partial / External Dependency | Destination و Bag fixture |
| EPS-73 | SignalR | Implemented | Implemented | Implemented | Ready | Bag و Destination fixture |
| EPS-76 | SignalR | Implemented | Implemented | Planned | Partial / External Dependency | Packing parcel fixture |
| EPS-79 | SignalR | Implemented | Implemented | Planned | Blocked / External Dependency | Postal export و parcel fixture |
| EPS-83 | SignalR | Implemented | Implemented | نیاز ندارد | Partial / External Dependency | Bag و Destination fixtures؛ Mock Postal scenario |
| EPS-87 | SignalR | Implemented | Implemented | نیاز ندارد | Partial / External Dependency | ParcelErrorOverrides |
| EPS-89 | SignalR | Implemented | Implemented | نیاز ندارد | Partial / External Dependency | Audit log/queue/database evidence |
| EPS-113 | SignalR | Implemented | Implemented | نیاز ندارد | Partial / External Dependency | Central Event Service و چرخه رویدادهای ارتباطی |

## وضعیت‌ها

- `Implemented`: تست اجرایی وجود دارد.
- `Missing`: تست موردنیاز هنوز وجود ندارد.
- `Planned`: طراحی تست مشخص است اما هنوز فعال نشده.
- `نیاز ندارد`: Stress مستقل برای ریسک فعلی EPS ارزش ندارد.
- `Blocked / External Dependency`: اجرای کامل به سرویس، Mock، Fixture یا شواهد
  خارجی وابسته است.
- `Partial / External Dependency`: بخشی از تست قابل اجراست و بخشی وابستگی خارجی
  دارد.

## تست‌های غیر EPS

- `tests/success/test_base_success.py`: Smoke عمومی مسیر Login، Auth و
  RegisterInbound؛ با Markerهای `smoke` و `mixed`.
- `tests/success/test_websocket_success.py`: Smoke عمومی SignalR/WebSocket؛ با
  Markerهای `smoke` و `signalr`.
- `tests/unit/`: تست Client، Service، Assertion، Settings و ابزارهای مشترک.
- `tests/stress/`: Stressهای منتسب به EPS-53، EPS-55 و EPS-73.
- تست‌های catalog: بررسی فهرست Caseها بدون اجرای E2E.
- Packing: قرارداد مشترک `bag.close` برای EPS-76/79/87/89، نه چهار اجرای
  تکراری مستقل.

جزئیات سیاست پوشش در [TEST_COVERAGE_POLICY.md](TEST_COVERAGE_POLICY.md) و
جزئیات هر EPS در README همان EPS قرار دارد.
