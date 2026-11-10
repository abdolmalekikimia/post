# ⚙️ Configuration & Test Data

This section covers how environment settings are loaded, immutable data structures, and strategies for generating unique, isolated test data.

---

## 1. Managing environment variables with an immutable `Settings` (`config/settings.py`)

So tests run in different environments (Local, CI/CD, Staging, Mock Server) without code changes, all parameters are read from environment variables (`.env`).

### Key traits of `Settings`:
1. **Using `@dataclass(frozen=True)`:**
   The `Settings` class is defined as an Immutable object. This guarantees that no test can accidentally change a variable such as `base_url` in the middle of a run and affect other tests.
2. **Using `field(default_factory=...)`:**
   For values that must be random or computed on every test run (such as `test_run_id` or random destination codes), a factory is used:
   ```python
   test_run_id: str = field(
       default_factory=lambda: str(uuid4().int % 900_000 + 100_000)
   )
   ```
3. **Validation in `__post_init__`:**
   When the instance is first built, numeric values such as timeouts, stress repeat counts and delay times are validated, so configuration errors stop immediately with an explicit error:
   ```python
   if self.timeout_seconds <= 0:
       raise ValueError("TIMEOUT_SECONDS must be greater than zero")
   ```

---

## 2. Strategy for generating unique test data

In postal and warehouse system tests, barcodes and parcels must be unique to avoid collisions (Data Collision) and bugs caused by duplicate data when tests run at the same time.

In `utils/test_data.py`:
- The `unique_barcode(base_barcode, settings)` function: using the current run id (`test_run_id`) and a sequential counter, it generates a new barcode of a given length (for example the standard 24 digits).
- The `configured_or_random_exchange_center_code(code, excluded)` function in `utils/site_codes.py`: if no destination code is defined in the `.env` file, it picks a valid standard 5-digit exchange-center code at random and makes sure the origin and destination differ.

---

## 3. The test-specific settings template (`config/test.env.example`)

To set the project up in a new environment, there is a ready sample file named `config/test.env.example` with safe, dummy values (Dummy/Placeholders):
```ini
BASE_URL=https://api.example.invalid
WS_URL=wss://api.example.invalid
ADMIN_USERNAME=admin
ADMIN_PASSWORD=demo-password
DEVICE_ID=demo-device
DEVICE_TOKEN=demo-token
DEVICE_IP=127.0.0.1
BARCODE=123456789012345678901234
RUN_E2E=0
```
To run the tests, the user only has to copy this file as `config/test.env` and enter the addresses of their own mock or local server.
