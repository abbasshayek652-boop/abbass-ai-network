# LinkedIn Agent

The LinkedIn Agent extends Mother AI with authenticated publishing and scheduling
capabilities for company pages or individual profiles. It follows a safe,
advice-first rollout path that mirrors the broader platform philosophy.

## Features

- OAuth 2.0 login flow with consent redirect and callback handling.
- Secure token storage in a local SQLite database (no secrets in logs).
- Text post publishing with visibility controls.
- Document carousel posts with offline-safe fallback to text mode.
- Scheduling queue with minute-level polling and jitter to respect rate limits.
- Daily quota guardrails plus health endpoint for operations.
- CLI helper for quick manual actions.

## Environment Variables

```
LI_CLIENT_ID=<LinkedIn app client id>
LI_CLIENT_SECRET=<LinkedIn app secret>
LI_REDIRECT_URI=http://localhost:8000/agents/linkedin/callback
```

Configure them via `.env` or your orchestration platform. Additional settings
include:

- `LI_DB_PATH` (optional) – location of the SQLite database, defaults to
  `linkedin_agent.db` in the working directory.
- `LI_DAILY_POST_LIMIT` (optional) – defaults to 50.

## OAuth Flow

1. Navigate to `/agents/linkedin/login`. The server returns a redirect to the
   LinkedIn authorization page.
2. Authenticate and approve the scopes (`openid profile email w_member_social`).
3. LinkedIn redirects to `/agents/linkedin/callback?code=...&state=...`.
4. Mother AI exchanges the code for tokens, stores them, and confirms the owner
   URN in the JSON response.

## REST Endpoints

| Route | Method | Description |
| ----- | ------ | ----------- |
| `/agents/linkedin/login` | GET | Redirects to LinkedIn consent. |
| `/agents/linkedin/callback` | GET | Finalise OAuth and persist tokens. |
| `/agents/linkedin/post/text` | POST | Publish an immediate text post. |
| `/agents/linkedin/post/document` | POST | Publish text + PDF (falls back to text offline). |
| `/agents/linkedin/schedule` | POST | Enqueue a scheduled post. |
| `/agents/linkedin/schedule` | GET | List pending jobs. |
| `/agents/linkedin/health` | GET | Lightweight health payload. |

### Payload Examples

Publish a text update:

```
curl -X POST http://localhost:8000/agents/linkedin/post/text \
  -H 'Content-Type: application/json' \
  -d '{"text": "Markets opened flat today", "visibility": "PUBLIC"}'
```

Schedule a document share:

```
curl -X POST http://localhost:8000/agents/linkedin/schedule \
  -H 'Content-Type: application/json' \
  -d '{
        "text": "Q4 Investor Deck",
        "doc_path": "assets/q4_deck.pdf",
        "doc_title": "Q4 2024 Investor Overview",
        "run_at": "2024-12-01T13:00:00"
      }'
```

## Scheduler

The lightweight scheduler polls once per minute (with jitter) for pending jobs.
Successful publications mark jobs as `completed`; failures capture the exception
message for later review. The scheduler starts automatically when the FastAPI
application boots and is accessible via `app.state.linkedin_scheduler`.

## CLI Helper

```
python tools/linkedin_cli.py login
python tools/linkedin_cli.py post --text "Hello LinkedIn"
python tools/linkedin_cli.py post-doc --file assets/playbook.pdf --title "Inventory Playbook" --text "Read the full guide."
```

Ensure the environment variables above are exported before running the CLI.

## Troubleshooting

- **Redirect URI mismatch** – confirm LinkedIn developer console matches
  `LI_REDIRECT_URI` exactly.
- **Insufficient permissions** – the configured scopes must be approved in your
  LinkedIn application settings.
- **HTTP 429** – the agent automatically backs off with jitter; consider raising
  `run_at` or reducing daily quota.
- **Token expired** – re-run the login flow to refresh credentials.

