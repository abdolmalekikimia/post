# Contributing

This repository is a public QA/SDET portfolio project. Contributions should
preserve the existing test architecture and public-sanitization boundary.

## Before opening a change

1. Do not add real credentials, tokens, cookies, JWTs, internal URLs, private
   IP addresses, company identifiers, or production payloads.
2. Keep test logic and business assertions focused on the documented scenario.
3. Add or update unit coverage when changing reusable utilities or metadata.
4. Run the safe local suite:

   ```powershell
   .venv\Scripts\python.exe -m pytest -q
   ```

5. Review `git diff` and Git history for accidental sensitive content.

End-to-end and stress tests should only be run against an explicitly prepared
local mock or demo service.
