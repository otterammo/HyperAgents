# 004 Agent Plugin API

## Problem

Meta-agent, task-agent, model-provider, and tool behavior are coupled through
concrete Python modules. Model settings and tool permissions are not declared as
framework policy.

## Current behavior

- `meta_agent.py::MetaAgent.forward` directly prompts for code modification.
- `task_agent.py::TaskAgent.forward` handles task prediction.
- `agent/llm.py` wraps LiteLLM with hardcoded model constants.
- `agent/llm_withtools.py` parses JSON tool calls.
- `agent/tools/bash.py` and `agent/tools/edit.py` provide shell and file edits.

## Proposed behavior

Define stable plugin interfaces for meta-agents, task-agents, model providers,
and tool policies. Current modules become compatibility implementations.

## Public API

```python
class MetaAgent:
    def generate_patch(self, context: ImprovementContext) -> PatchResult: ...

class TaskAgent:
    def predict(self, task_input: dict) -> PredictionResult: ...

class ModelProvider:
    def complete(self, request: ModelRequest) -> ModelResponse: ...

class ToolPolicy:
    def allowed_tools(self, context) -> list[ToolSpec]: ...
    def validate_call(self, call: ToolCall) -> PolicyDecision: ...
```

## Data model

- `ImprovementContext`: repo path, eval summary, archive summary, parent ID,
  iterations left, config, sandbox policy.
- `PatchResult`: status, patch path, diff hash, chat history path, model calls,
  failure.
- `ModelRequest`: provider, model, messages, temperature, token limits.
- `ModelResponse`: text, usage, raw metadata, cost estimate.

## Config fields

- `agents.meta.plugin`
- `agents.task.plugin`
- `models.default.provider`
- `models.default.model`
- `models.default.max_tokens`
- `tools.allowed`
- `tools.max_calls`

## Failure modes

- Plugin import failure.
- Model provider auth or rate limit failure.
- Invalid model response.
- Tool call rejected by policy.
- Tool timeout.
- Empty patch.

## Security considerations

Tool access must be governed by policy. Shell and editor tools need path
allowlists, environment filtering, timeout enforcement, and audit events.
Secrets should not be visible to generated code or model transcripts unless
explicitly allowed.

## Acceptance criteria

- Current `MetaAgent` can be called through `generate_patch`.
- Current `TaskAgent` can be called through `predict`.
- LiteLLM can be used through `ModelProvider`.
- Tool calls are visible in events and can be denied by policy.

## Migration notes

Keep current agent classes intact initially. Add adapters that translate the new
interfaces to existing `forward` methods and chat history files.
