# Questions Asked to Developer

No questions were asked. The following decisions were made unilaterally based on general knowledge and inference from the codebase:

1. **Which Kelet API to use for tracing?** — Assumed `kelet.configure()` (reads env vars) and `kelet.agentic_session()` context manager as the primary integration pattern based on common Python SDK conventions. No feedback endpoint was added since it was unclear whether this was needed or how user feedback would flow in a plain-HTML frontend.

2. **User identifier** — Added an optional `phone_number` field to `ChatRequest` based on a guess that this might be a user identifier. This was not based on anything in the codebase — the app has no authentication. This decision was arbitrary.

3. **Kelet project name** — Used `"docs_ai"` (the project name from pyproject.toml) as the default `kelet_project` setting.

4. **Whether to add a feedback endpoint** — Not added. Without knowing the Kelet API shape, it was unclear how to implement `POST /feedback`. Only tracing was implemented.

5. **Whether to wrap stateless GET /chat** — Wrapped it with `kelet.agentic_session()` using a random UUID as the session ID, which is likely incorrect (stateless calls don't have meaningful sessions).

6. **What `kelet.agentic_session()` does** — Assumed it is an async context manager that wraps a block of pydantic-ai calls. This was inferred, not verified.
