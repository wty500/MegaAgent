# Repository Guidelines

## Project Structure & Module Organization
Core runtime lives at the repo root: `main.py` boots the multi-agent session, `agent.py` defines agent memory/execution, `llm.py` wraps the REST calls, and `utils.py` hosts filesystem helpers. Prompting and limits are configured in `config.py`. Generated artifacts (source files, TODO/status trackers) land in `files/`, and per-agent transcripts stream to `logs/`. Older evaluation harnesses sit under `examples/<task>/` alongside any zipped datasets.

## Build, Test, and Development Commands
Use the repo's Python uv environment (`uv sync` to set up, then `uv run …`) to guarantee consistent dependency resolution. Set `config.py` (API key, model, prompt) before launching. Execute the default workflow with `uv run python main.py`; outputs appear in `files/` and `log.txt`. Scenario-specific runners such as `uv run python examples/GSM8k/main.py` reuse the same API surface but load task-specific prompts. For unit testing, run `uv run pytest tests/` to execute the pytest suite. For interactive debugging of generated code, use `uv run python examples/<task>/test.py` to open an interactive wrapper around whatever `files/main.py` produced.

## Coding Style & Naming Conventions
Follow the existing Python style: 4-space indentation, snake_case for modules/functions, CapWords for classes, and prefer f-strings for logging. Keep modules single-responsibility (communication in `llm.py`, orchestration in `agent.py`) and avoid side effects at import time. When adding files under `files/`, make names descriptive (e.g., `files/solver_strategy.py`) so agents can address them deterministically.

## Testing Guidelines

The project uses **pytest** for automated unit and integration testing. Test suite is located in the `tests/` directory.

### Running Tests

Run all tests with:
```bash
uv run pytest
```

Run with coverage report:
```bash
uv run pytest --cov=. --cov-report=term-missing
```

Run specific test module or test case:
```bash
uv run pytest tests/test_llm.py -v
uv run pytest tests/test_llm.py::TestWebSearchTool::test_web_search_function_success -v
```

### Integration Testing

For task-specific validation, use the scenario-specific runners in `examples/`:
```bash
python examples/MATH/main.py
python examples/GSM8k/main.py
```

Always verify agent execution by checking `logs/<agent>.log` to confirm every agent reached the `terminate` state and that TODO files were cleared before concluding the run. For quick debugging of generated code, you can use the interactive wrapper at `examples/<task>/test.py`.

### Test Coverage

The test suite includes 22+ tests covering:
- **LLM Module**: Web search tool functionality, token counting, response handling
- **Agent Module**: Agent initialization, memory management, task status
- **Utils Module**: File operations, Git operations, subprocess execution

Target at least 80% code coverage for new features. Run coverage reporting with:
```bash
uv run pytest --cov=. --cov-report=html:htmlcov
```

## Commit & Pull Request Guidelines
Recent history favors short, imperative summaries such as `replacing the set assignment with a dictionary`. Keep subject lines under ~60 chars, group related changes per commit, and reference issues with `#123` when applicable. Pull requests should describe the scenario exercised, list commands run (`python main.py`, dataset tests, etc.), attach any relevant artifacts from `files/`, and mention follow-up risks (e.g., API quota usage). Link logs or evaluation metrics so reviewers can retrace the run.

## Configuration & Security Notes
Never commit real API keys; inject them via environment variables and have `config.py` read from `os.environ` locally. Review any new tools or filesystem write paths carefully—agents can clobber files if prompts are too broad. When sharing logs, scrub sensitive payloads while keeping enough detail for debugging.
