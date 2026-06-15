# Testing notes — pytest + unittest.mock (for future me)

A decoder for the testing stack used in this project. The *concepts* (setup/teardown,
fakes, assertions) are the same as any test framework — this is just the Python/pytest
vocabulary for them. Anchored to `backend/test_api.py`.

## Two libraries in play

- **pytest** — the test *runner* + the **fixture** system (setup/teardown + dependency injection).
- **unittest.mock** — the *faking* toolkit (`patch`, `MagicMock`).

### Where these come from (vs the Java world)

The surprise coming from Java: **Python bundles its mocking library in the standard
library.** There's no separate "Mockito" to add — `unittest.mock` ships with Python
(since 3.3).

| Java | Python | Ships with Python? |
|---|---|---|
| **JUnit** (runner/framework) | **`unittest`** (stdlib) *or* **pytest** (3rd-party) | `unittest` yes; pytest no |
| **Mockito** (mocking) | **`unittest.mock`** → `MagicMock`, `patch` | **Yes — stdlib** |
| Hamcrest / AssertJ (matchers) | plain `assert` (pytest rewrites it for nice output) | n/a |

- `unittest` is Python's built-in JUnit-equivalent; **pytest** is the popular third-party
  runner most projects prefer (nicer fixtures, plain `assert`). pytest can run
  `unittest`-style tests and uses `unittest.mock` happily — they **compose**. pytest does
  NOT ship its own mocking system.
- This project = **pytest (runner + fixtures) + stdlib `unittest.mock` (fakes)**. The
  standard idiomatic combo.
- **`pytest-mock`** IS a real third-party add-on, but it's just thin sugar — it wraps
  `unittest.mock` and exposes it as a `mocker` fixture so you skip managing `with patch(...)`.
  Same `MagicMock` underneath. This project uses raw `unittest.mock`, so you see the
  unwrapped version.

## The one mental model

A `MagicMock` **records how it's called and replies with whatever you program**.
`patch` **swaps a real object for a mock just for the duration of a test, then restores
the real one.** Fixtures are where you do shared swap-in / swap-out. That's ~90% of it.

## Decoder table

| What you see | What it means |
|---|---|
| `def test_foo(...)` | pytest auto-discovers any `test_*` function and runs it. No registration. |
| `assert x == y` | Plain Python `assert`. False (or any raised exception) = test fails. That's the whole assertion mechanism. |
| `@pytest.fixture` | Marks a function as reusable **setup/teardown** (a `@Before`/`@After` that can also hand back a value). |
| a test param like `mock_agent` | pytest **injects by name** — matches the parameter to a fixture or a `patch` arg and passes it in. DI via the argument list. |
| `autouse=True` | Run this fixture for *every* test, even if no test names it. (Used for `reset_state`, `bypass_auth`, `mock_retriever`.) |
| `yield` inside a fixture | Before `yield` = setup; after = teardown. The test runs "at" the yield. The fixture's `try/finally`. |
| `patch.object(mod, "name")` | Temporarily replace `mod.name` with a fake, then restore it. Decorator → injects the fake as a param. `with` → scoped to the block. |
| `MagicMock()` | A fake that records calls and auto-creates any attribute/method you touch. The stunt double. |
| `m.invoke.return_value = x` | "When `m.invoke(...)` is called, return `x`." Programming the fake's output. |
| `m.invoke.side_effect = Exception(...)` | "When called, **raise** this instead." (side_effect can also be a function, or a list to iterate over.) |
| `m.invoke.assert_called_once_with(...)` | Verify it was called exactly once, with exactly these args. Tests the **interaction/contract**, not a return value. |
| `m.return_value.retrieve.return_value` | Chain: `get_retriever()` → `.return_value` (fake instance); `.retrieve()` on that → *its* `.return_value`. Two calls = two `.return_value` hops. |

## Fixtures (the pytest part)

```python
@pytest.fixture(autouse=True)
def reset_state():
    question_counts.clear()   # setup
    yield                     # <- test runs here
    # (teardown would go here, after the yield)
```

- **Get a fixture** by naming it as a test parameter: `def test_x(mock_retriever): ...`.
- **autouse** = applied to every test in scope without being named.
- **yield** splits setup (above) from teardown (below). Teardown runs even if the test fails.
- Fixtures can use `patch` as a context manager so the patch is auto-undone at teardown:

```python
@pytest.fixture(autouse=True)
def mock_retriever():
    with patch.object(chat_service, "get_retriever") as mock_get:
        mock_get.return_value.retrieve.return_value = ("CTX", [])
        yield mock_get        # patch active during the test; undone after
```

## Mocking (the unittest.mock part)

**`patch` two ways:**

```python
# (1) as a DECORATOR — injects the mock as an argument
@patch.object(chat_service, "agent")
def test_x(mock_agent):
    mock_agent.invoke.return_value = ...

# (2) as a CONTEXT MANAGER — scoped to the block (used inside fixtures)
with patch.object(chat_service, "get_retriever") as mock_get:
    ...
```

**Stacked decorators inject bottom-up.** The decorator nearest the `def` is the FIRST
parameter:

```python
@patch.object(chat_service, "get_retriever")   # top    -> LAST arg
@patch.object(chat_service, "agent")           # bottom -> FIRST arg
def test_x(mock_agent, mock_get_retriever):     # order matches inside-out
    ...
```

**Program a fake's behavior:**
- `.return_value = x` → what it returns when called.
- `.side_effect = Exception(...)` → raise instead of return.
- `.side_effect = [a, b, c]` → return a, then b, then c on successive calls.

**Assert on how it was called:**
- `.assert_called_once_with(args...)` → exactly once, exactly these args.
- `.assert_called_with(args...)` → the most recent call matched.
- `.call_count`, `.call_args`, `.assert_not_called()`.

## FastAPI-specific bits (not general testing knowledge)

- **`TestClient(app)`** — runs the real app in-process (routing, middleware, validation,
  dependencies) with no network. `client.post("/chat", json=...)` returns a response with
  `.status_code` and `.json()`.
- **`app.dependency_overrides[dep] = fn`** — FastAPI's official test seam to swap a
  `Depends(...)` for the duration of tests. Used to bypass Clerk auth:
  ```python
  app.dependency_overrides[verify_clerk_user] = lambda: "test-user-id"
  ```
  Production wiring is untouched; only the test app swaps the dependency.

## Why this project's modules need lazy construction to be testable

`from api import app` transitively imports `chat_service`, which used to run
`retriever = Retriever()` and `clerk = Clerk(...)` **at module top-level** — constructing
real OpenAI / Pinecone / Clerk clients and reading secrets *just to import the module*.
In tests, `conftest.py` stubs heavy deps and `dotenv` (so `.env` does NOT load), so those
constructions crashed at **collection time** (`KeyError`, `OpenAIError`) before any test
ran. Fix: build lazily (`@functools.cache` factory `get_retriever()` / `get_clerk()`), so
importing the module has no side effects and the clients are built only on first real use
(or never, when mocked). Bonus: the app is importable in any context without a full `.env`.

## Running tests

```
python -m pytest -v                      # whole suite
python -m pytest test_api.py -q          # one file, quiet
python -m pytest test_api.py -x          # stop at first failure
python -m pytest test_api.py::test_chat_returns_reply   # one test
```

Tests need the pytest **runner** — `python -m some.module` only *imports* a file, it does
not run its tests.