# Reverse Tunnel: Design

## Problem

The lidar service runs in hosted infrastructure and needs to load pages from the user's local dev server (e.g. `localhost:3000`). In local testing this works because everything is on the same machine, but in production the hosted service has no route to localhost.

Ngrok and similar tools solve this, but they're third-party dependencies, require setup, and expose the dev server on a public URL. We want something that:

1. Requires zero setup beyond plugin installation
2. Never exposes the dev server to the public internet
3. Only our lidar service can reach the tunnel

## Approach

Ship a lightweight, standalone MCP server (`subtext-tunnel`) as part of the plugin. On startup, it opens an outbound WebSocket to a relay endpoint in our infrastructure. The hosted lidar/devtools service sends HTTP requests through the relay, which forwards them over the WebSocket to the tunnel client, which proxies them to localhost and returns the response.

This is separate from the local `subtext-devtools` MCP server, which provides direct browser control via CDP. The tunnel serves the hosted path — the hosted infrastructure controls the browser and uses the tunnel to reach the user's local dev server. The local devtools server serves the local-only path. They coexist in the plugin but are independent.

```
User's machine                                Our infrastructure (lidar pod)
─────────────                                ─────────────────────────────

localhost:3000                                devtools MCP tools
      ↑                                            │
      │ fetch()                                    │ page.Goto(url)
      │                                            ▼
subtext-tunnel ──── WSS (outbound) ────→  TunnelRegistry ← ForwardProxy ← BrowserContext
 (MCP server)                             (relay endpoint)  (127.0.0.1:N)   (Proxy option)
```

All connections are outbound from the user's machine. The relay endpoint is internal to our infrastructure — no public URL is ever created for the user's dev server.

## Wire protocol

JSON messages over a single WebSocket connection. The relay sends request messages; the client sends response messages. A `requestId` correlates each pair.

### Messages

**`hello`** (client → relay, immediately after connect)
```json
{
  "type": "hello",
  "target": "http://localhost:3000"
}
```
Declares the local origin the client will proxy to. Sent once, after the WebSocket upgrade succeeds. The relay rejects the connection if this isn't received within 5 seconds.

**`ready`** (relay → client)
```json
{
  "type": "ready",
  "tunnelId": "t_a1b2c3d4"
}
```
Confirms the tunnel is registered and reachable by the lidar service. The `tunnelId` is opaque to the client.

**`request`** (relay → client)
```json
{
  "type": "request",
  "requestId": "r_abc123",
  "method": "GET",
  "url": "/dashboard?tab=settings",
  "headers": { "Accept": ["text/html"], "Cookie": ["session=abc", "theme=dark"] },
  "body": null
}
```
Headers use `map[string]string[]` to support multi-value headers (e.g. `Set-Cookie`).
`body` is base64-encoded when present, `null` otherwise. `url` is the path + query string (no origin — the client prepends its `target`).

**`response`** (client → relay)
```json
{
  "type": "response",
  "requestId": "r_abc123",
  "status": 200,
  "headers": { "Content-Type": ["text/html"], "Set-Cookie": ["session=abc", "theme=dark"] },
  "body": "PCFET0NUWVBFLi4u"
}
```
`body` is always base64-encoded (even for text) for simplicity. Empty responses use `null`.

**`error`** (client → relay, when the local request fails)
```json
{
  "type": "error",
  "requestId": "r_abc123",
  "message": "ECONNREFUSED 127.0.0.1:3000"
}
```
The relay translates this into a 502 for the lidar service caller.

**`ping` / `pong`** (bidirectional)
```json
{ "type": "ping" }
{ "type": "pong" }
```
Keepalive. The relay sends `ping` every 30s; the client must respond with `pong` within 10s or the tunnel is closed. The client may also initiate pings.

### Authentication

Auth happens at the WebSocket upgrade, not in the protocol. The client sends a bearer token in the `Authorization` header (or as `?token=` query param for environments where custom headers on WebSocket upgrades are awkward). The relay validates the token, extracts the user identity, and associates it with the tunnel.

## Plugin side (TypeScript)

The tunnel client is a standalone MCP server at `tunnel/` in the plugin repo. It has no dependency on the devtools MCP server — no CDP, no puppeteer, no browser interaction. Its only job is to proxy HTTP requests from the relay to localhost.

### Directory structure

```
tunnel/
  src/
    main.ts          — MCP server entry point, CLI arg parsing, tunnel lifecycle
    client.ts        — TunnelClient class (WebSocket + HTTP proxy logic)
    types.ts         — Wire protocol message types
  docs/
    design.md        — This file
  package.json
  tsconfig.json
```

### TunnelClient

```
class TunnelClient
  - constructor(relayUrl, target, token, logger)
  - connect(): void
  - disconnect(): void
  - isConnected: boolean
  - tunnelId: string | undefined

  Private:
  - #ws: WebSocket | null
  - #target: string                          // "http://localhost:3000"
  - #inflight: Map<requestId, AbortController>
  - #handleMessage(msg): dispatch on msg.type
  - #handleRequest(msg): fetch(target + url), send response
  - #reconnect(): exponential backoff (1s, 2s, 4s, ... max 30s)
  - #keepalive(): respond to pings, detect dead connections
```

The proxy logic is straightforward: receive a `request` message, make the equivalent `fetch()` call against `this.#target`, and send the `response` back. Requests are tracked in `#inflight` so they can be aborted on disconnect.

### MCP server (`main.ts`)

Minimal MCP server over stdio. Starts the tunnel on launch, tears it down on exit.

Configuration via CLI args and/or environment variables:
- `--relay <url>` / `SUBTEXT_TUNNEL_RELAY` — relay WebSocket URL (e.g. `wss://relay.lidar.fullstory.com/tunnel`)
- `--target <origin>` / `SUBTEXT_TUNNEL_TARGET` — local origin to expose (e.g. `http://localhost:3000`)
- `--token <token>` / `SUBTEXT_TUNNEL_TOKEN` — auth token

Exposes one optional tool for debugging:
- `tunnel_status` — returns connection state, tunnel ID, target, and uptime

### Plugin configuration

`.mcp.json` gains a third server entry:

```json
{
  "mcpServers": {
    "session-review": { "..." : "..." },
    "subtext-devtools": { "..." : "..." },
    "subtext-tunnel": {
      "command": "node",
      "args": [
        "${CLAUDE_PLUGIN_ROOT}/tunnel/build/main.js",
        "--target", "http://localhost:3000"
      ],
      "env": {
        "SUBTEXT_TUNNEL_RELAY": "wss://relay.lidar.fullstory.com/tunnel",
        "SUBTEXT_TUNNEL_TOKEN": "..."
      }
    }
  }
}
```

### Design notes

- **Standalone.** No dependency on devtools MCP server. Can be developed, tested, and deployed independently.
- **Non-fatal.** If the tunnel fails to connect or disconnects, the MCP server stays running. Tunnel errors are logged but don't crash the process. The tunnel reconnects automatically with exponential backoff.
- **Minimal surface.** One optional MCP tool (`tunnel_status`). The tunnel is otherwise invisible to the agent.
- **Body encoding.** Base64 is simple and handles binary assets (images, fonts, wasm). The ~33% overhead is irrelevant for dev server traffic. A future optimization could use binary WebSocket frames.

## Infrastructure side (Go)

All of this can live in the existing lidar service — no new binary or sidecar.

### Tunnel registry

In-memory map of active tunnels, keyed by tunnel ID.

```
TunnelRegistry
  mu      sync.RWMutex
  byID    map[string]*Tunnel      // tunnelId → Tunnel
  byUser  map[string][]*Tunnel    // userId → user's active tunnels

Tunnel
  ID       string                 // random, e.g. UUID
  UserID   string                 // from auth token
  Target   string                 // declared in "hello"
  conn     *websocket.Conn
  pending  map[string]chan *Response  // requestId → response channel
  created  time.Time
```

The registry handles registration, deregistration, and lookup. The `byUser` index lets the lidar service find a user's tunnel without knowing the tunnel ID.

### WebSocket endpoint: `GET /tunnel`

Public-facing (the tunnel client connects to it).

1. Validate bearer token → extract user identity
2. Upgrade to WebSocket (`gorilla/websocket` or `nhooyr.io/websocket`)
3. Wait for `hello` (5s timeout) → extract `target`
4. Generate tunnel ID, register in `TunnelRegistry`
5. Send `ready` with tunnel ID
6. Enter read loop:
   - `response` or `error` messages → dispatch to the corresponding pending channel
   - `pong` → update last-seen timestamp
   - anything else → log and ignore
7. On disconnect → deregister, close all pending channels (callers get 502)

A write goroutine handles outbound messages (requests + pings) via a channel, so the WebSocket connection is only written to from a single goroutine.

### Browser integration

Rather than exposing a separate HTTP endpoint for proxy requests, v1 uses an **in-process forward proxy** per devtools connection. Each connection starts a lightweight HTTP proxy on `127.0.0.1:0` (OS-assigned port), and the Playwright BrowserContext is configured with `Proxy: {Server: "http://127.0.0.1:<port>"}`.

The forward proxy selectively tunnels requests:
- **HTTP to localhost/127.0.0.1** → looked up via `registry.FindTunnel(orgID, targetOrigin)` → `tunnel.ProxyRequest()` → response returned to browser
- **HTTP to anything else** → `http.DefaultTransport.RoundTrip()` → forwarded directly
- **CONNECT to non-localhost** → hijack + bidirectional pipe (standard HTTPS proxy)
- **CONNECT to localhost** → 502 + warning (WebSocket/HTTPS tunneling not supported in v1)

This approach positions us for WebSocket/stream support in v2 (unlike Playwright's `route()` which cannot intercept WebSocket upgrades). The proxy looks up the tunnel fresh for each request, so tunnel reconnects are handled transparently.

A future v2 could also expose an internal HTTP endpoint (`POST /internal/tunnel/proxy`) for cross-service tunnel access.

### Keepalive

A goroutine per tunnel sends `ping` every 30s. If no `pong` is received within 10s, close the WebSocket and deregister. This doubles as liveness detection: the lidar service can check tunnel existence before attempting a proxy request.

### Cleanup

Tunnels are cleaned up on:
- WebSocket disconnect (immediate)
- Missed pong (within 40s)
- Server shutdown (close all WebSockets gracefully)

No persistent storage needed — tunnels are ephemeral and re-established on reconnect.

### Sizing estimate

~400-500 lines of Go:
- ~100 for the registry
- ~150 for the WebSocket handler + read/write loops
- ~100 for the proxy endpoint
- ~50-100 for keepalive, auth plumbing, and error handling

### Security

- **Auth:** Bearer token on WebSocket upgrade, tied to the user's account. The relay knows who owns each tunnel.
- **No public URLs:** The proxy endpoint is internal-only. Tunnel IDs are UUIDs but unguessable regardless since the endpoint isn't publicly routable.
- **Target pinning:** The tunnel only proxies to the `target` origin declared in `hello`. The relay enforces this — there's no mechanism for the lidar service to override the target.
- **Limits:** Max in-flight requests per tunnel (e.g. 20), max response body size (e.g. 50MB), request timeout (30s). These prevent a misbehaving client from consuming relay resources.

## Future considerations

- **Binary frames:** Switch from base64 JSON to binary WebSocket frames for bodies to eliminate encoding overhead. Only worth doing if we tunnel large assets.
- **Streaming:** Support chunked/streaming responses for SSE or large payloads. Would add `stream_open`, `stream_data`, and `stream_close` message types. Not needed for v1 — dev server responses are small. This is the main gap for HMR (hot module replacement) which relies on WebSocket or EventSource connections to localhost.
- **Multi-port:** Allow a single tunnel client to expose multiple local ports (e.g. frontend on 3000, API on 8080). Would extend `hello` to declare multiple targets.
- **Metrics:** Track tunnel latency, throughput, and error rates per user. Useful for debugging and capacity planning.
