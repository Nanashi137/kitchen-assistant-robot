# Clear-path robot action (PerformActionNode)

When the user message is **not** ambiguous, the tree runs `PerformActionNode` instead of an LLM answer.

## Default

- **PlainMessageActionExecutor** — fills `ACTION_MESSAGE_TEMPLATE` (default: `I performed the {user_request}`).
- `{user_request}` is the **standalone_question** (rewritten user message).

Set in `.env`:

```env
ACTION_MESSAGE_TEMPLATE=I performed the {user_request}
```

## Custom executor (e.g. Gazebo later)

Pass a callable `client -> str` to `build_tree(..., action_executor=your_executor)` in `api/app.py`, or implement `ActionExecutor`:

```python
from nodes.action_executor import ActionExecutor

class MyGazeboExecutor:
    def __call__(self, client) -> str:
        sq = getattr(client, "standalone_question", "") or ""
        # TODO: send sq to Gazebo / sim, wait for result
        return f"I performed the {sq.strip()}"

# lifespan:
tree = build_tree(bb=bb, llm=llm, vecdb=vecdb, action_executor=MyGazeboExecutor())
```

The blackboard **client** exposes any keys your nodes register (e.g. future `environment`, `tool_pose`). Extend `Blackboard` when you add new state.

## Legacy

- **AnswerNode** remains in the codebase for notebooks/tests; the main API tree no longer uses it on the clear path.
- **Vector search** is still used on the **ambiguous** path (optional entities for repair).
