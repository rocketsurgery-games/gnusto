---
name: subtext:tunnel
description: Use when opening a hosted browser connection against a localhost or local dev server URL. Sets up a reverse tunnel so the hosted browser can reach the user's local server.
---

# Tunnel Setup for Hosted DevTools

When the hosted devtools browser needs to load a page from the user's local dev server (e.g. `http://localhost:3000`), a reverse tunnel is required. The hosted browser cannot reach localhost directly — the tunnel proxies requests from the hosted infrastructure back to the user's machine.

## When to Use

- `open_connection` (on devtools) is called with a `localhost`, `127.0.0.1`, or other local URL
- The user asks to screenshot, test, or interact with their local dev server using hosted devtools

## Setup Flow

Run these steps **before** calling `open_connection` with the local URL:

### 1. Get tunnel config

Call `get_tunnel_config` on the **devtools** MCP server (no parameters). It returns:
- `relayUrl` — WebSocket URL for the relay

### 2. Connect the tunnel

Call `tunnel_connect` on the **devtools-tunnel** MCP server with:
- `relayUrl` — from step 1
- `target` — the user's local origin (e.g. `http://localhost:3000`)

Authentication is handled automatically via the `SUBTEXT_API_KEY` environment variable (the same credential used by the devtools MCP connection).

The tool waits up to 5 seconds for the handshake and returns the connection state.

### 3. Verify ready state

The `tunnel_connect` response includes `state`. If it's `"ready"`, proceed. If not, call `tunnel_status` to check — the connection may still be establishing. If it stays disconnected, report the error to the user.

### 4. Open the connection

Call `open_connection` on **devtools** with the localhost URL as normal. The hosted browser will route the request through the tunnel back to the user's machine.

## Example

```
// Step 1: Get config
get_tunnel_config() → { relayUrl }

// Step 2: Connect tunnel
tunnel_connect({ relayUrl, target: "http://localhost:3000" }) → { state: "ready", tunnelId: "..." }

// Step 3: Open connection through the tunnel
open_connection({ url: "http://localhost:3000/dashboard" }) → screenshot + component tree
```

## Notes

- The tunnel stays connected across multiple `open_connection` calls — you only need to set it up once per connection.
- If the tunnel disconnects (e.g. the relay restarts), it reconnects automatically. Call `tunnel_status` to check.
- The tunnel only needs to be set up for localhost/local URLs. Remote URLs (e.g. `https://example.com`) work directly without a tunnel.
