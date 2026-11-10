# ✅ Assertions & Contract Testing

This section shows how reply validation (Assertions) is implemented in this project, and why separating this layer matters for test stability.

---

## 1. Why should raw Asserts not be scattered across tests?

In the traditional approach, every test file contains statements like this:
```python
# traditional, unsuitable approach:
assert response.status_code == 200
assert response.json()["status"] == "SUCCESS"
assert response.json()["payload"]["data"]["sessionId"] != ""
```
**Problems of the traditional approach:**
1. If the field name changes from `sessionId` to `session_id` in the future, you have to edit hundreds of test files.
2. When a bug appears, Python's default error messages do not give enough information about the full server reply.
3. It makes no difference between a structural error (Malformed JSON) and a business logic error.

---

## 2. Modular design of the Assertions layer in this project

In this project all checks are centralized in the `assertions/` folder:
- `assertions/http_assertions.py`: checks HTTP status codes
- `assertions/signalr_assertions.py`: checks SignalR standard formats, result fields, success and failure
- `assertions/bag_assertions.py`: checks that closing bags and containers is correct
- `assertions/negative_scenario_assertions.py`: checks the expected error codes in negative tests

### Example of validating a successful SignalR reply (`assertions/signalr_assertions.py`):
```python
def assert_success_response(response: dict[str, Any], action_name: str) -> None:
    assert isinstance(response, dict), f"Expected dict response for {action_name}, got {type(response)}"
    # check that base fields such as success or status exist
    status = response.get("status") or response.get("isSuccess")
    assert status in (True, "SUCCESS", "OK", "Success", 200), (
        f"{action_name} failed. Expected success status, but got response: {response}"
    )
```

---

## 3. What is Contract Testing?

A contract test checks that:
1. Are all required fields present in the reply?
2. Is the data type of every field (String, Integer, Boolean, Array) correct?
3. Do identifier fields such as `correlationId`, `sessionId` and `timestamp` match valid patterns?

### Practical example:
In the close-bag scenario (`flows/bag/container_response_contract_flow.py`):
- It is checked that the received reply contains `sealNumber`, `totalCount`, `destinationCenterCode` and the final status.
- If the server drops any of these keys, the test fails at once with a clear message, which prevents hidden errors in Production.
