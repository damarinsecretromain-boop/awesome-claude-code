# MCP servers for this repository

`.mcp.json` registers three project-scoped MCP servers for Claude Code:

| Server | Transport | Package / endpoint | Required env |
|---|---|---|---|
| `firecrawl` | stdio | `firecrawl-mcp@3.38.0` | `FIRECRAWL_API_KEY` |
| `playwright` | stdio | `@playwright/mcp@0.0.84` (headless) | — |
| `composio` | http | Composio session MCP URL | `COMPOSIO_MCP_URL`, `COMPOSIO_API_KEY` |

## Setup

1. Requirements: Node.js 18+ (`npx`).
2. Copy `.env.example` and fill in the keys, then export them in the shell
   that launches Claude Code (Claude Code expands `${VAR}` from the environment):
   ```bash
   cp .env.example .env   # .env is git-ignored
   set -a && source .env && set +a
   claude
   ```
3. On first launch, approve the project MCP servers when prompted, then run
   `/mcp` to check they are all connected.
4. Playwright: if no browser is installed locally, run
   `npx playwright install chromium` once.

## Composio

Composio serves MCP over HTTP with a per-user session URL. Create an API key on
https://platform.composio.dev, then generate the URL either from the dashboard or with the SDK:

```ts
import { Composio } from '@composio/core';
const composio = new Composio({ apiKey: process.env.COMPOSIO_API_KEY });
const session = await composio.create('my-user-id', { toolkits: ['github', 'gmail'] });
console.log(session.mcp.url); // -> COMPOSIO_MCP_URL
```

Never commit real keys: only `.env.example` is tracked.
