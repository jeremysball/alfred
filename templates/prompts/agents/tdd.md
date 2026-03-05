## Test-Driven Development

This rule is absolute. No exceptions.

Before writing implementation code:

1. Create `tests/test_<module>.py`
2. Write the test—define expected behavior first
3. Run the test and see it fail—confirms the test is valid
4. Implement minimum code to pass
5. Refactor—clean up while tests protect you

### Forbidden: Ad-Hoc Testing

Never use `python -c` for testing:

```bash
# Wrong—not repeatable, not versioned, no regression protection
python -c "from mymodule import func; assert func(1) == 2"
```

### Required: Write Test Files

```bash
# Create test file first
touch tests/test_mymodule.py

# Write the test
def test_func_returns_double():
    from mymodule import func
    assert func(1) == 2

# Run with pytest
uv run pytest tests/test_mymodule.py -v
```

### When python -c Is Acceptable

- **Exploring**—Understanding how a library works
- **Debugging**—Quick inspection of state/values
- **One-off scripts**—Never for verifying code correctness

### The Red-Green-Refactor Cycle

| Phase | Action |
|-------|--------|
| **Red** | Write a failing test that describes desired behavior |
| **Green** | Write minimum code to make the test pass |
| **Refactor** | Clean up while tests protect you |

### Test Coverage Requirements

| Category | Examples |
|----------|----------|
| Happy path | Normal inputs, expected outputs |
| Edge cases | Empty, null, boundary values, off-by-one |
| Error cases | Invalid input, missing files, network errors |
| Type safety | Wrong types, None values |
