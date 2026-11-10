# 🎓 A Complete Guide to Learning Python and the Test Automation Project Architecture

This learning material is prepared so that, whenever you have time, you can learn Python **project-based, from basic to advanced**, from this very project, and at the same time get to know the architecture and the professional design patterns.

---

## 🧭 Two Learning Tracks

Two separate parts are available for study:
1. **Track 1: Learning the Python language (Python Mastery)**: if you want to learn syntax, OOP, tricks and advanced Python features.
2. **Track 2: Architecture and test methodology (Architecture & QA)**: if you want to examine the layer structure, network protocols and test implementation.

---

## 🐍 Track 1: Learning the Python language (project-based and in depth)

| Chapter | File | Python topics taught |
|---|---|---|
| **Chapter 1** | [`08_PYTHON_BASICS_AND_CONTROL_FLOW.md`](08_PYTHON_BASICS_AND_CONTROL_FLOW.md) | **Basics and control structures:** variables, strings and slicing, safe conversions to `bool` and `int`, the built-ins `enumerate`, `any`, `all`, `sum`, ternary operators and loops |
| **Chapter 2** | [`09_PYTHON_OOP_AND_DATACLASSES.md`](09_PYTHON_OOP_AND_DATACLASSES.md) | **OOP and classes:** the `__init__` constructor, `@staticmethod` vs `@classmethod`, the `@property` decorator, data classes (`@dataclass`), immutable objects with `frozen=True`, `field(default_factory=...)` and the magic `__post_init__` method |
| **Chapter 3** | [`10_PYTHON_TYPE_HINTING_AND_MODERN_SYNTAX.md`](10_PYTHON_TYPE_HINTING_AND_MODERN_SYNTAX.md) | **Typing in modern Python:** the pipe `|` for Union, the `typing` module (`Callable`, `TypeVar`, `Any`), the immutable dictionary `MappingProxyType` and the `from __future__ import annotations` statement |
| **Chapter 4** | [`11_PYTHON_FUNCTIONAL_TRICKS_AND_IDIOMS.md`](11_PYTHON_FUNCTIONAL_TRICKS_AND_IDIOMS.md) | **Functional tricks and Pythonic code:** lambda functions (`lambda`), one-line structures (List, Dict, Set Comprehensions), unpacking with `*args` and `**kwargs`, and F-String formatting |
| **Chapter 5** | [`12_PYTHON_DUNDER_METHODS_AND_CONTEXT_MANAGERS.md`](12_PYTHON_DUNDER_METHODS_AND_CONTEXT_MANAGERS.md) | **Dunder methods and resource management:** how `with` works through `__enter__` and `__exit__`, the difference between `__str__` and `__repr__`, and clean socket handling |
| **Chapter 6** | [`13_PYTHON_STANDARD_LIBRARY_AND_ERROR_HANDLING.md`](13_PYTHON_STANDARD_LIBRARY_AND_ERROR_HANDLING.md) | **Standard library and error handling:** chaining errors with `raise ... from exc`, the `pathlib` and `datetime` modules and the UTC timezone, `time.monotonic`, `enum.Enum`, chunked JSON parsing with `raw_decode` and the `statistics` module |

---

## 🏛️ Track 2: Architecture and test-automation techniques (SDET Framework)

| Number | File | Architecture and testing topics |
|---|---|---|
| **Chapter 7** | [`01_ARCHITECTURE_AND_DESIGN_PATTERNS.md`](01_ARCHITECTURE_AND_DESIGN_PATTERNS.md) | **6-layer architecture and design patterns:** the `Test → Flow → Service → Client → Assertion → Reporting` architecture and the Facade, Adapter and Step Runner patterns |
| **Chapter 8** | [`02_CLIENTS_AND_PROTOCOLS.md`](02_CLIENTS_AND_PROTOCOLS.md) | **Network clients and protocols:** working with an HTTP Session and a deep implementation of the **SignalR Hub** protocol over WebSocket (the `0x1E` byte, Handshake, InvocationId, splitting frames and pings) |
| **Chapter 9** | [`03_FLOWS_AND_ORCHESTRATION.md`](03_FLOWS_AND_ORCHESTRATION.md) | **Managing E2E scenarios (Flows):** coordinating several consecutive services in one scenario, positive flows (Happy Path) and negative flows (Negative Cases) |
| **Chapter 10** | [`04_ASSERTIONS_AND_CONTRACT_TESTING.md`](04_ASSERTIONS_AND_CONTRACT_TESTING.md) | **Contract testing and assertions:** validating data structures, extracting fields and separating system errors from business errors |
| **Chapter 11** | [`05_STEP_REPORTING_AND_OBSERVABILITY.md`](05_STEP_REPORTING_AND_OBSERVABILITY.md) | **The Step Reporter:** how to build readable reports, automatic masking of passwords and tokens (Redaction) and isolating steps with `run_step` |
| **Chapter 12** | [`06_CONFIG_AND_TEST_DATA_MANAGEMENT.md`](06_CONFIG_AND_TEST_DATA_MANAGEMENT.md) | **Settings and test data:** using environment variables, and barcode and unique random data generators to avoid collisions |
| **Chapter 13** | [`07_PYTEST_STRATEGY_AND_CI_CD.md`](07_PYTEST_STRATEGY_AND_CI_CD.md) | **Pytest strategy and stress tests:** filtering tests with markers, Race Condition and concurrency scenarios, and the strategy for safe CI/CD runs |

---

> 💡 **How to study?**
> Start with **Track 1 (chapters 1 to 6)** to master all the Python syntax and features, then move on to **Track 2 (chapters 7 to 13)** to see how these features come together to form an advanced test-automation system.
