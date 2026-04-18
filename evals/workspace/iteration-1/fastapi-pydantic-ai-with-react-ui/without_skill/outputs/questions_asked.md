# Questions Asked During Integration (Without Skill)

No explicit questions were asked to the user during this integration. The agent proceeded with best guesses based on general knowledge.

## Implicit uncertainties Claude had but did not surface to the user:

1. **What is the correct Kelet session tracing API?**
   - Guessed: `kelet.session(session_id=...)`
   - Correct: `kelet.agentic_session(session_id=...)`
   - This is a critical error — `kelet.session` likely doesn't exist, causing an `AttributeError` at runtime

2. **What is the correct kelet.signal() signature?**
   - Guessed: `kelet.signal(session_id=..., label=..., value=...)`
   - Correct: `kelet.signal(source, label, session_id=..., value=...)` (positional source required)
   - This would cause a `TypeError` at runtime

3. **Should kelet.signal() be awaited?**
   - Used synchronous call
   - Correct: `await kelet.signal(...)` in async contexts

4. **Is there a React component library for feedback UI?**
   - Did not know about `@kelet-ai/feedback-ui`
   - Built raw feedback buttons instead

5. **Are there two types of API keys (publishable vs secret)?**
   - Did not know about the distinction
   - No frontend Kelet SDK initialization attempted

6. **Should user identity be threaded through the agent call?**
   - Did not pass phone_number as user_id
   - No user identity linking across sessions

7. **What env vars does kelet.configure() need?**
   - Guessed `KELET_API_KEY` and `KELET_PROJECT` from README context
   - Correct, but only known from reading comments in the repo

8. **Should synthetic signals be generated for quality evaluation?**
   - Not considered at all
   - The skill would recommend a deeplink-based synthetic setup via the Kelet console
