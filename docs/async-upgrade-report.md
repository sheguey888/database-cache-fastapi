# Async upgrade report

## Updated endpoint and flow

`POST /conversations/{conversation_id}/messages` is now `async def` because it
awaits the asynchronous AI service in `app/ai_service.py`. The endpoint:

1. Checks conversation ownership.
2. Calls `await asyncio.wait_for(ai_service.generate_text(...), timeout=5)`.
3. Saves the user prompt and final assistant response only after the AI call
   succeeds.
4. Returns the concrete response text, not a coroutine object.

For compatibility, callers may still provide `assistant_response`; that bypasses
the fake AI call and saves the supplied response.

## Timeout and error handling

An AI timeout returns HTTP 504 with a friendly retry message. A
`TemporaryAIError` returns HTTP 503, and unexpected provider failures return HTTP
500 without exposing internal exception details. The timeout behavior is covered
by `test_message_ai_timeout_returns_friendly_error`.

## Sequential versus concurrent study packs

`POST /study-pack` generates a summary, quiz, and flashcards. A sequential
implementation would await each AI call one after another, so three calls of
about 50 ms would take about 150 ms. The endpoint instead uses
`asyncio.gather` to start all three independent calls together, so the total
time is close to the slowest single call (about 50 ms in the test).

Concurrency helps when work is independent and spends time waiting on I/O, such
as network calls to an AI provider. It does not make CPU-heavy Python work
faster, and it is not useful when the second operation depends on the first.
