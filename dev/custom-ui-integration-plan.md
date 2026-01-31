# Custom UI Integration Plan

## Overview

This document outlines the plan for integrating custom UI clients (like Yukie MVP Blueprint) with the OpenClaw Gateway via the WebSocket protocol.

## Current Architecture

### Gateway WebSocket Server
- **Port**: Default `18789` (configurable via `gateway.port`)
- **Protocol**: JSON-RPC-like over WebSocket
- **Authentication**: Token, password, or device identity
- **Protocol Version**: Currently v3

### Built-in Control UI
- **Location**: `/ui` directory
- **Technology**: Vite + Lit
- **Client Class**: `GatewayBrowserClient` (`ui/src/ui/gateway.ts`)
- **Served From**: `dist/control-ui` (built via `pnpm ui:build`)

## Integration Approach

### Phase 1: Protocol Documentation
- [x] Document WebSocket protocol structure
- [x] Document connection handshake flow
- [x] Document key RPC methods (chat, sessions, config, etc.)
- [x] Document event streaming mechanism

### Phase 2: Reference Client Implementation
- [ ] Create standalone TypeScript client library
- [ ] Extract `GatewayBrowserClient` logic into reusable package
- [ ] Add TypeScript types for protocol messages
- [ ] Include examples for common use cases

### Phase 3: Integration Guide
- [ ] Create step-by-step integration guide
- [ ] Provide code examples for popular frameworks (Vue, React, etc.)
- [ ] Document authentication options
- [ ] Document connection options (local, SSH tunnel, Tailscale)

### Phase 4: Testing & Validation
- [ ] Create test client implementation
- [ ] Validate against Gateway protocol
- [ ] Test with remote Gateway setups
- [ ] Document common issues and solutions

## Protocol Details

### Connection Handshake

```typescript
// Connect request
{
  type: "req",
  id: "uuid",
  method: "connect",
  params: {
    minProtocol: 3,
    maxProtocol: 3,
    client: {
      id: "client-name",
      version: "1.0.0",
      platform: "web",
      mode: "webchat"
    },
    role: "operator",
    scopes: ["operator.admin"],
    auth: {
      token: "gateway-token" // or password
    }
  }
}

// Connect response (hello-ok)
{
  type: "res",
  id: "uuid",
  ok: true,
  payload: {
    type: "hello-ok",
    protocol: 3,
    features: {
      methods: ["chat.send", "chat.history", ...],
      events: ["chat", "tick", ...]
    },
    snapshot: { ... }
  }
}
```

### Key RPC Methods

#### Chat Methods
- **`chat.send`**: Send message to agent
  - Params: `{ sessionKey, message, deliver?, attachments?, idempotencyKey, thinking?, timeoutMs? }`
  - Returns: `{ runId, status: "started" | "in_flight" | "ok" }`
  
- **`chat.history`**: Get conversation history
  - Params: `{ sessionKey, limit? }`
  - Returns: `{ messages: [...], thinkingLevel? }`
  
- **`chat.abort`**: Stop running chat
  - Params: `{ sessionKey, runId? }`
  - Returns: `{ ok: true }`
  
- **`chat.inject`**: Inject assistant message (UI-only)
  - Params: `{ sessionKey, message, label? }`
  - Returns: `{ ok: true, messageId }`

#### Session Methods
- **`sessions.list`**: List available sessions
- **`sessions.patch`**: Update session settings
- **`sessions.preview`**: Preview session state

#### Status Methods
- **`status`**: Get gateway status
- **`health`**: Health check
- **`models.list`**: List available models

#### Config Methods
- **`config.get`**: Get configuration
- **`config.set`**: Set configuration value
- **`config.patch`**: Patch configuration
- **`config.schema`**: Get config schema

### Event Streaming

Events are pushed from Gateway to client:

```typescript
{
  type: "event",
  event: "chat",
  payload: {
    runId: "uuid",
    sessionKey: "main",
    seq: 1,
    state: "delta" | "final" | "aborted" | "error",
    message?: { ... },
    errorMessage?: string,
    usage?: { ... },
    stopReason?: string
  },
  seq: 123
}
```

**Chat Event States:**
- `delta`: Streaming update (partial response)
- `final`: Complete response
- `aborted`: Run was aborted
- `error`: Error occurred

## Implementation Steps for Custom UI

### Step 1: Create WebSocket Client

```typescript
class OpenClawGatewayClient {
  private ws: WebSocket | null = null;
  private pending = new Map<string, Pending>();
  
  async connect(url: string, auth: { token?: string; password?: string }): Promise<void> {
    // Implement connection handshake
  }
  
  async request(method: string, params?: unknown): Promise<any> {
    // Implement RPC request/response
  }
  
  onEvent(callback: (event: EventFrame) => void): void {
    // Set up event listener
  }
}
```

### Step 2: Implement Chat Methods

```typescript
// Send message
const result = await client.request("chat.send", {
  sessionKey: "main",
  message: "Hello",
  deliver: false,
  idempotencyKey: crypto.randomUUID()
});

// Listen for events
client.onEvent((event) => {
  if (event.event === "chat") {
    const payload = event.payload as ChatEventPayload;
    if (payload.state === "delta") {
      // Update streaming response
    } else if (payload.state === "final") {
      // Complete response
    }
  }
});
```

### Step 3: Handle Authentication

**Option 1: Token (Recommended)**
```typescript
const token = await getGatewayToken(); // From config or user input
await client.connect("ws://localhost:18789", { token });
```

**Option 2: Password**
```typescript
await client.connect("ws://localhost:18789", { password: "user-password" });
```

**Option 3: Device Identity** (Advanced)
- Requires WebCrypto API (HTTPS or localhost)
- See `ui/src/ui/device-identity.ts` for implementation

### Step 4: Connection Options

**Local Gateway:**
```typescript
await client.connect("ws://127.0.0.1:18789", { token });
```

**Remote via SSH Tunnel:**
```bash
ssh -N -L 18789:127.0.0.1:18789 user@gateway-host
```
Then connect to `ws://127.0.0.1:18789`

**Remote via Tailscale:**
```typescript
await client.connect("wss://your-magicdns:443", { token });
```

## Reference Files

### OpenClaw Codebase
- **Client Implementation**: `ui/src/ui/gateway.ts` - `GatewayBrowserClient` class
- **Chat Controller**: `ui/src/ui/controllers/chat.ts` - Usage examples
- **Protocol Schema**: `src/gateway/protocol/schema/` - Type definitions
- **Server Handlers**: `src/gateway/server-methods/chat.ts` - Server implementation
- **Protocol Index**: `src/gateway/protocol/index.ts` - Validation functions

### Documentation
- **Web Overview**: `docs/web/index.md`
- **Control UI**: `docs/web/control-ui.md`
- **Remote Access**: `docs/gateway/remote.md`
- **Security**: `docs/gateway/security.md`

## Example: Yukie MVP Blueprint Integration

### Current Yukie API
- Location: `apps/chatbox/src/lib/api.ts`
- Uses HTTP REST API
- Methods: `sendChatMessage()`, `transcribeAudio()`, `getInbox()`

### Integration Approach
1. Create `OpenClawGatewayClient` class
2. Add initialization function to connect to Gateway
3. Replace or augment HTTP calls with WebSocket RPC
4. Handle streaming events for real-time updates
5. Maintain backward compatibility with existing API

### Code Structure
```
yukie-mvp-blueprint/
  apps/
    chatbox/
      src/
        lib/
          openclaw-client.ts      # New: Gateway WebSocket client
          api.ts                   # Modified: Add OpenClaw option
          api-openclaw.ts          # New: OpenClaw-specific methods
```

## Next Steps

1. **Create standalone client library** (Phase 2)
   - Extract reusable client code
   - Publish as npm package or include in repo
   - Add comprehensive TypeScript types

2. **Write integration guide** (Phase 3)
   - Step-by-step instructions
   - Framework-specific examples
   - Troubleshooting section

3. **Test with real implementations** (Phase 4)
   - Test with Yukie MVP Blueprint
   - Test with other potential clients
   - Document edge cases

## Questions to Resolve

- [ ] Should we create a separate npm package for the client?
- [ ] Should we support HTTP fallback for non-WebSocket environments?
- [ ] How to handle reconnection logic and backoff?
- [ ] Should we provide React/Vue hooks for easier integration?
- [ ] How to handle device identity for secure contexts?

## Related Issues/PRs

- TBD: Create GitHub issues for each phase
- TBD: Link to any existing discussions about custom UI support
