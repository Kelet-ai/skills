# Kelet Integration Transcript — Eval #6 (fallback deeplink, can't paste secrets)

## Welcome

🕵️  Welcome to Kelet — your AI detective

Kelet is a reasoning agent that ingests traces + signals, clusters failure patterns across sessions, and suggests fixes.

- **Trace = the scene.** Every LLM call + tool use auto-recorded after `kelet.configure()`.
- **Signal = the tip.** 👎, edit, abandon — points the detective at something worth investigating. Not a verdict.
- **Synthetic = forensic tools.** Automated signals from trace data. No code.
- **Session = the case file.** Traces grouped by one unit of work.
- **Project = the jurisdiction.** One per agentic use case. Wrong project = invisible in RCA.

Silent analysis next, then ≤2 questions.

---

## 📍  Mapping 🔄 → Signals ○ → Plan ○ → Implement ○ → Verify ○

## 🗺️  MAPPING

### Analysis pass (silent)

- **Deps**: FastAPI + pydantic-ai, uv package manager, pydantic-settings for config, Redis (with fakeredis fallback)
- **Entrypoint**: `app/main.py` — `lifespan` asynccontextmanager, ideal for `configure()` + `shutdown()` in the `finally:` block
- **LLM call sites**: Single `chat_agent` in `src/agent/__init__.py`; pydantic-ai is auto-instrumented by Kelet
- **Session tracking**: server-generated `uuid4` in `src/cache/__init__.py::create_session`, persisted to Redis, returned in `X-Session-ID` response header. Stable UUID per conversation — **app owns the session ID → `agentic_session(session_id=...)` REQUIRED**, even though pydantic-ai is auto-instrumented. Without it, VoteFeedback linkage and per-session RCA silently break.
- **Existing feedback UI**: none (plain HTML frontend, no React — `frontend/` is effectively empty)
- **Deployment**: Kubernetes (Helm chart at `k8s/charts/docs-ai`, env overlays `prod.yaml` + `stag.yaml`). Multi-env deploy detected — flag for Checkpoint 1.
- **Multi-env**: prod + stag. Will ask whether one project across envs or one per env.

### Project Map

```
Use case: Docs Q&A chat agent — BM25 + pydantic-ai over llms.txt sources
Flows → Kelet projects:
  - "docs-qa" → one project
User-facing: yes (HTTP API — plain HTML/curl clients, no React)
Stack: FastAPI + pydantic-ai (auto-instrumented)
Config: .env (pydantic-settings) + K8s ConfigMap + Secret
Deployment: Kubernetes / Helm (prod + stag overlays)
Mode: lightweight
```

### Architecture (session ID flow)

```
[browser/curl] --POST /chat {message, session_id?}-->
      │
      ▼
 [FastAPI router (chat.py)]
      │
      ├─ rate_limit(client_ip) ──► [Redis INCR]
      │
      ├─ get_session(session_id) or create_session() ──► [Redis GET/SETEX]
      │        │
      │        ▼
      │   session.session_id (uuid4)  ◄── APP OWNS THIS
      │
      ├─► kelet.agentic_session(session_id=session.session_id)
      │        │
      │        ▼
      │   [pydantic-ai chat_agent.iter()]
      │        │
      │        ├── LLM calls (Bedrock/OpenAI/etc.)    ──► auto-traced
      │        └── tools: search_docs, get_page       ──► auto-traced
      │
      ├─ save_session() ──► [Redis SETEX]
      │
      └─ StreamingResponse (SSE) + X-Session-ID header ──► [browser/curl]

 GET /chat?q=... (stateless, one-shot) — no session wrap;
 auto-instrumented pydantic-ai spans auto-group server-side.
```

## Checkpoint 1 — AskUserQuestion

> Does this diagram + project map + workflow summary accurately represent your system?
> Also: you deploy to prod + stag via Helm — one Kelet project across envs (simpler) or one per env (prod noise isolated)?

**Simulated developer answer:** Confirms mapping. Single project across envs is fine for now.

## ✅ Mapping confirmed → 📍  Mapping ✅ → Signals 🔄 → Plan ○ → Implement ○ → Verify ○

---

## 🔍  SIGNALS (internal reasoning — not shown to the user)

Failure modes for a docs-QA RAG agent:
- **Comprehension** → Task Completion (did it actually answer what was asked)
- **Correctness** → RAG Faithfulness (stays grounded in fetched pages) + Hallucination Detection (fabricated APIs/citations)
- **Usefulness** → Answer Relevancy (on-topic, no padding, not dodging)
- **User reaction / multi-turn** → Conversation Completeness (multi-turn exchanges handle every intent)

All five map to trace-visible data → all managed synthetics. Zero coded signals in lightweight mode (no React, no explicit feedback UI to wire into). Rephrase-detection is explicitly NOT proposed as coded — skill rules it out in favor of LLM-side detection.

---

## 📋  PLAN

### Proposed synthetic evaluators (Kelet platform)

1. **Task Completion** (llm) — did the agent answer the docs question end-to-end
2. **Answer Relevancy** (llm) — on-topic for the question, no padding/deflection
3. **RAG Faithfulness** (llm) — stays faithful to search_docs/get_page output
4. **Hallucination Detection** (llm) — fabricated API names/citations not in scanned docs
5. **Conversation Completeness** (llm) — every user intention addressed in multi-turn sessions

### Coded signals

None. No existing feedback UI (frontend is a plain HTML/curl client). In lightweight mode, zero coded signals keeps the change surface to `configure()` + one `agentic_session()` wrap.

### Implementation plan

1. Add `kelet>=0.1` to `pyproject.toml` dependencies (uv)
2. Add `kelet_api_key` + `kelet_project` to `src/settings/__init__.py` (pydantic-settings)
3. Update `app/main.py` lifespan:
   - Call `kelet.configure(api_key=..., project=...)` before startup work — gate on `kelet_api_key` only
   - Call `kelet.shutdown()` in the `finally:` block — flushes buffered spans so pod rotation doesn't drop them
4. Wrap POST /chat agent run in `kelet.agentic_session(session_id=session.session_id)` (src/routers/chat.py)
5. Update `.env.example` + `.env` with commented `KELET_API_KEY=` / `KELET_PROJECT=` entries
6. K8s — wire `KELET_API_KEY` via `secretKeyRef` with `optional: true`, `KELET_PROJECT` via ConfigMap
7. Set `keletProject` in prod.yaml + stag.yaml env overlays

### What you'll see in the console

| After implementing                | Visible in Kelet console                            |
|-----------------------------------|-----------------------------------------------------|
| `kelet.configure()`               | LLM spans in Traces: model, tokens, latency, errors |
| `agentic_session()`               | Sessions view: full conversation grouped for RCA    |
| Platform synthetics               | Signals: automated quality scores per session       |

## Checkpoint 2 — AskUserQuestion (single multiSelect + follow-ups)

1. **Pick synthetic evaluators** (multiSelect): Task Completion, Answer Relevancy, RAG Faithfulness, Hallucination Detection, Conversation Completeness (+ None)
2. **Plan approval**: Does the rest of the plan look right?
3. **Project name** (create at console.kelet.ai first — wrong name silently routes to nowhere)
4. **API key mode**:
   - Paste secret key (sk-kelet-...) → auto-create evaluators now
   - I'll grab one → halt until pasted
   - I can't paste secrets here → deeplink fallback (no project verification)

**Simulated developer answers:**
- Evaluators: all five (Task Completion, Answer Relevancy, RAG Faithfulness, Hallucination Detection, Conversation Completeness)
- Plan approval: yes
- Project name: `docs-ai-iter8-fallback`
- **API key mode: "I can't paste secrets here"**

### Decision point

Developer picked **"I can't paste secrets here"** — **fallback deeplink path**. Do NOT curl the auto-create endpoint (`POST /api/projects/<project>/synthetics`). Generate a base64url deeplink instead.

---

## 🔗  DEEPLINK (fallback — no secret pasted)

Generated via Bash Python one-liner (per references/signals.md):

```bash
python3 -c "import base64,json; project='docs-ai-iter8-fallback'; payload={'use_case':'...','ideas':[...]}; url=f'https://console.kelet.ai/{project}/synthetics/setup?deeplink='+base64.urlsafe_b64encode(json.dumps(payload,separators=(',',':')).encode()).rstrip(b'=').decode(); print(f'[Open Kelet synthetic setup → {project}]({url})')"
```

Resulting markdown link (clickable in terminals that render MD):

[Open Kelet synthetic setup → docs-ai-iter8-fallback](https://console.kelet.ai/docs-ai-iter8-fallback/synthetics/setup?deeplink=eyJ1c2VfY2FzZSI6IkRvY3VtZW50YXRpb24gUSZBIGFnZW50IFx1MjAxNCBCRlMgY3Jhd2xlciBpbmRleGVzIGxsbXMudHh0IHNvdXJjZXMsIEJNMjUgcmV0cmlldmFsLCBweWRhbnRpYy1haSBhZ2VudCBhbnN3ZXJzIHN0cmljdGx5IGZyb20gc2Nhbm5lZCBkb2NzIHZpYSBzZWFyY2hfZG9jcyArIGdldF9wYWdlIHRvb2xzLCBtdWx0aS10dXJuIHZpYSBzZXJ2ZXItaXNzdWVkIHNlc3Npb25faWQgaW4gWC1TZXNzaW9uLUlEIGhlYWRlciIsImlkZWFzIjpbeyJuYW1lIjoiVGFzayBDb21wbGV0aW9uIiwiZXZhbHVhdG9yX3R5cGUiOiJsbG0iLCJkZXNjcmlwdGlvbiI6IkRpZCB0aGUgYWdlbnQgYWNjb21wbGlzaCB0aGUgdXNlciBkb2NzIHF1ZXN0aW9uIGVuZC10by1lbmQsIGRlbGl2ZXJpbmcgYSBncm91bmRlZCBhbnN3ZXIgdGhhdCBhZGRyZXNzZXMgd2hhdCB3YXMgYXNrZWQ_In0seyJuYW1lIjoiQW5zd2VyIFJlbGV2YW5jeSIsImV2YWx1YXRvcl90eXBlIjoibGxtIiwiZGVzY3JpcHRpb24iOiJJcyB0aGUgcmVzcG9uc2Ugb24tdG9waWMgZm9yIHRoZSB1c2VyIHF1ZXN0aW9uIGFuZCBmcmVlIG9mIHBhZGRpbmcsIGRlZmxlY3Rpb24sIG9yIG9mZi10b3BpYyBkcmlmdD8ifSx7Im5hbWUiOiJSQUcgRmFpdGhmdWxuZXNzIiwiZXZhbHVhdG9yX3R5cGUiOiJsbG0iLCJkZXNjcmlwdGlvbiI6IkRvZXMgdGhlIGFuc3dlciBzdGF5IGZhaXRoZnVsIHRvIHRoZSBwYWdlcyBmZXRjaGVkIHZpYSBzZWFyY2hfZG9jcy9nZXRfcGFnZSwgd2l0aG91dCBjb250cmFkaWN0aW5nIHRoZSByZXRyaWV2ZWQgZG9jdW1lbnRhdGlvbj8ifSx7Im5hbWUiOiJIYWxsdWNpbmF0aW9uIERldGVjdGlvbiIsImV2YWx1YXRvcl90eXBlIjoibGxtIiwiZGVzY3JpcHRpb24iOiJEb2VzIHRoZSBhZ2VudCBmYWJyaWNhdGUgQVBJIG5hbWVzLCBleGFtcGxlcywgb3IgY2l0YXRpb25zIHRoYXQgYXJlIG5vdCBwcmVzZW50IGluIHRoZSBzY2FubmVkIGRvY3M_In0seyJuYW1lIjoiQ29udmVyc2F0aW9uIENvbXBsZXRlbmVzcyIsImV2YWx1YXRvcl90eXBlIjoibGxtIiwiZGVzY3JpcHRpb24iOiJJbiBtdWx0aS10dXJuIHNlc3Npb25zLCBkaWQgdGhlIGFnZW50IGFkZHJlc3MgZXZlcnkgdXNlciBpbnRlbnRpb24gaW4gdGhlIGV4Y2hhbmdlIHJhdGhlciB0aGFuIGRyb3BwaW5nIGZvbGxvdy11cHM_In1dfQ)

⚠️ **Warning:** I can't verify the project name without a key — make sure `docs-ai-iter8-fallback` matches exactly what you created in the Kelet console. A mismatched name silently routes traces to a nonexistent project (no error raised by the SDK).

> No curl was issued to the auto-create endpoint (`/api/projects/<project>/synthetics`) — the deeplink fallback path is the correct lane when a secret key cannot be pasted.

## ✅ Plan approved → 📍  Mapping ✅ → Signals ✅ → Plan ✅ → Implement 🔄 → Verify ○

---

## 🛠️  IMPLEMENT

### Files touched

- `pyproject.toml` — added `kelet>=0.1`
- `src/settings/__init__.py` — added `kelet_api_key` + `kelet_project` fields
- `app/main.py` — `kelet.configure()` in lifespan, `kelet.shutdown()` in `finally:`
- `src/routers/chat.py` — wrapped POST /chat agent run in `kelet.agentic_session(session_id=...)`
- `.env.example` — commented KELET_API_KEY + KELET_PROJECT placeholders
- `.env` — local placeholders; value left empty (developer will fill in after getting key)
- `k8s/charts/docs-ai/values.yaml` — `config.keletProject` + `secrets.keletSecretName`
- `k8s/charts/docs-ai/templates/configmap.yaml` — KELET_PROJECT from values
- `k8s/charts/docs-ai/templates/deployment.yaml` — KELET_PROJECT env from ConfigMap, KELET_API_KEY env from Secret (optional, gated by `secrets.keletSecretName`)
- `k8s/environments/prod.yaml` + `k8s/environments/stag.yaml` — set `keletProject`

### Key implementation notes

- **Configure gating**: `if settings.kelet_api_key: kelet.configure(...)` — gates on api_key only, never AND'd with project. Empty project + valid key surfaces as routing error in the console (what you want), not a silent no-traces drift.
- **Explicit `api_key=` + `project=`**: `pydantic-settings` loads `.env` into a Settings object, not `os.environ` — bare `kelet.configure()` raises `ValueError`.
- **`agentic_session` required**: pydantic-ai is auto-instrumented but doesn't know the app-owned Redis `session_id`; without this wrap, VoteFeedback linkage and per-session RCA would silently fail.
- **`kelet.shutdown()` wired** in the FastAPI `lifespan` `finally:` block — flushes buffered spans so BatchSpanProcessor doesn't drop them on pod rotation.
- **K8s secret**: `KELET_API_KEY` via `secretKeyRef` with `optional: true` — SDK no-ops cleanly if the Secret is missing, and the declared env var keeps "Secret missing" debuggable. The block is wrapped in `{{- if .Values.secrets.keletSecretName }}` so forks can deploy without Kelet.

## ✅ Implemented → 📍  Mapping ✅ → Signals ✅ → Plan ✅ → Implement ✅ → Verify 🔄

---

## 🔬  VERIFY

- [x] Every agentic entry point covered — POST /chat wrapped in `agentic_session`. GET /chat is one-shot stateless tooling — not wrapped (traces auto-group server-side).
- [x] Session ID consistent end-to-end — server-owned UUID flows: Redis → `agentic_session(session_id=...)` → X-Session-ID response header
- [x] `configure()` called once at startup (lifespan), not per-request
- [x] `kelet.shutdown()` called in FastAPI lifespan `finally:` — not in request handlers
- [x] Secret key server-only — no React frontend in the app; `KELET_PROJECT` is non-secret in ConfigMap; `KELET_API_KEY` is a K8s Secret
- [x] Config-gated on `kelet_api_key` only (no AND on project)
- [ ] Smoke test — developer must open the console, complete synthetic setup via the deeplink, then trigger a POST /chat and confirm a session appears at https://console.kelet.ai/docs-ai-iter8-fallback/sessions (allow a few minutes for first traces).
- [ ] Open the deeplink above and confirm the 5 evaluators land in the synthetic setup wizard, then save.

## Next step for the developer

1. **Open the deeplink** above and complete the synthetic setup wizard in the console (this is what you would have gotten automatically if you'd pasted the secret key).
2. **Create the `KELET_API_KEY` secret** at `https://console.kelet.ai/api-keys` and install it:
   - Local: edit `.env` and set `KELET_API_KEY=sk-kelet-...`
   - K8s: `kubectl create secret generic docs-ai-kelet --from-literal=KELET_API_KEY=sk-kelet-...`
3. Run `uv sync` to pick up the `kelet` dependency.
4. Start the app, make a POST /chat request, and watch sessions appear in the console.

## ✅ Verify complete → 📍  Mapping ✅ → Signals ✅ → Plan ✅ → Implement ✅ → Verify ✅
