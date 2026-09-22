# LLM Architecture Rule

All LLM-backed features in SkillMatch must obtain their model from
`src.core.llm.get_llm()`:

```python
from src.core.llm import get_llm

llm = get_llm()
```

Feature code must not instantiate provider SDKs, read provider API keys from
`os.getenv()`, hardcode model names, or create another LLM service abstraction.
Provider selection, credentials, timeout/retry policy, and model settings are
owned by the central `LLMSettings` configuration. The runtime contract is:

```text
.env (LLM_PROVIDER, LLM_MODEL, LLM_API_KEY, ...)
  -> Settings.llm / LLMSettings
  -> get_llm()
  -> LangChain init_chat_model()
  -> the selected provider integration
```

Model IDs are opaque provider-specific values. The runtime does not infer a
provider from a model-name substring, and it does not create a second adapter
or service layer. New code must use `get_llm()` directly and must not create
another service abstraction.
The future AI Mentor must use the same `get_llm()` path.
