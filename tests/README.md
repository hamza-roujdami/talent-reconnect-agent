# Tests

```bash
# Demo (5-step hiring workflow)
python tests/test_demo.py

# Unit tests (agents, workflow)
pytest tests/test_agents.py -v

# Search integration (requires Azure)
pytest tests/test_search.py -v

# API tests (requires server running)
pytest tests/test_api.py -v

# All tests
pytest tests/ -v
```

| File | What it does |
|------|--------------|
| `test_demo.py` | Full 5-step hiring demo (profile → search → feedback → email) |
| `test_agents.py` | Agent creation, config, tools, handoffs |
| `test_search.py` | Azure AI Search providers (skipped without config) |
| `test_api.py` | HTTP endpoints: health, sessions, chat stream |
| `utils/debug_tools.py` | Inspect registered tools on agents |
