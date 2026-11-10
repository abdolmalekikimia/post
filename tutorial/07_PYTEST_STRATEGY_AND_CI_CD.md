# 🚀 Pytest Strategy, Stress Tests and CI/CD

This section shows the methodology used to categorize and run tests in Pytest, and how high-volume, concurrency and Race Condition tests are managed.

---

## 1. Categorizing tests with Pytest markers (`pytest.ini`)

Several markers are defined in `pytest.ini` to separate the test types precisely:
- `unit`: unit tests that check components, assertions, clients and helper methods in complete isolation and fast (no network needed).
- `success`: successful scenario tests (Happy Path).
- `negative`: negative scenarios and error validation.
- `stress`: high-volume, stability, concurrency and Race Condition tests.
- `e2e`: end-to-end tests that need a running server.

### Benefit of markers:
Targeted runs with the `-m` switch:
```powershell
# unit tests only
pytest tests/unit -q

# success tests only
pytest -m "success" -q

# all end-to-end tests except stress
pytest -m "e2e and not stress" -q
```

---

## 2. Designing Stress and Race Condition tests

Sensitive scenarios such as Race Conditions are tested in the `tests/stress/` folder.

### Example: the Race Condition scenario in a destination update (`tests/stress/test_destination_update_stress.py`)
- **Real-world problem:** if an operator presses the close-bag button (`container.close`) and, in the very same millisecond, the device assigns a parcel to the same bag (`route.assign`), how does the system behave?
- **How the test is implemented:**
  Using `ThreadPoolExecutor` or parallel execution in `utils/stress.py`, two simultaneous requests are sent from two independent connections, and then it is checked that the system never records an Inconsistent State: it either rejects the second request with a suitable error or the bag counter stays exact.

---

## 3. Safe execution in CI/CD with the `RUN_E2E` Guard

Since this repository is public on GitHub and is not connected to a real production server:
- A Guard is placed at the start of all integration tests:
  ```python
  if os.getenv("RUN_E2E", "0") != "1":
      pytest.skip("Set RUN_E2E=1 to run against the local demo service")
  ```
- The GitHub Actions pipeline (`.github/workflows/qa.yml`) runs unit tests, source security checks and syntax validation successfully without a mock server.
- Whenever a developer or tester wants to test locally against a mock server, they set the environment variable:
  ```powershell
  $env:RUN_E2E="1"
  pytest tests/success -q -s
  ```

---

## 4. Summary of frequently used commands

| Command | Use |
|---|---|
| `.venv\Scripts\python.exe -m pytest tests/unit -q` | Run all unit tests offline |
| `.venv\Scripts\python.exe -m pytest -q` | Run the default safe suite |
| `$env:RUN_E2E="1"; .venv\Scripts\python.exe -m pytest tests/success -q -s` | Run the end-to-end success scenarios |
| `$env:RUN_E2E="1"; .venv\Scripts\python.exe -m pytest tests/negative -q -s` | Run the negative scenarios |
| `$env:RUN_E2E="1"; .venv\Scripts\python.exe -m pytest tests/stress -q -s -o addopts=""` | Run the stress and concurrency tests |
| `.venv\Scripts\python.exe -m scripts.run_scenarios --list` | List the matrix of all covered scenarios |
