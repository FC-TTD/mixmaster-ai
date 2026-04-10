# Run tests

## What this command does
Runs the full test suite and reports results.

## Steps to execute
1. Activate venv: venv\Scripts\activate
2. Run: python -m pytest tests/ -v --tb=short
3. Report which tests passed and which failed
4. For any failure, show the exact assertion that failed
5. Suggest a fix for each failure — do not auto-fix without confirmation

## Rules
- Never modify test files to make tests pass
- Never skip tests with pytest.mark.skip without explicit permission
- If a test is failing due to a real bug, report it to the user before fixing