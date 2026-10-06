# Public CI checks

The public pipeline verifies offline tests and code correctness. It does not
verify the private postal system, live SignalR integration or production readiness.
Live tests require a separately configured service and are skipped by default.

## Commands

```sh
python -m pip install -r requirements.txt -r requirements-dev.txt
python -m pytest tests/unit -q
python -m pytest -q
pylint $(git ls-files '*.py')
```

Pytest keeps short tracebacks so a collection or assertion failure is visible.
The Pylint configuration enables every fatal/error diagnostic and selected
correctness warnings (including duplicate keys, unreachable code and constant
conditions). Optional API and broker dependencies are installed for analysis.

Formatting, documentation, complexity, duplication and synchronous loop callback
warnings remain a separate review backlog; passing this gate does not mean all
Pylint style/refactoring diagnostics have been resolved. To inspect that backlog:

```sh
pylint --disable= --enable=all $(git ls-files '*.py')
```
