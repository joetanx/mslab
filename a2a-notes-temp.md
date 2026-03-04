> Prompt:
>
> delve into the communication details between agents via A2A protocol. what does the communication exchange look like? how does agents initialize and understand each others' capabilities? what does the called agents reply to let the calling agent know what parameters to provide to call a tool? details on the underlying HTTP methods GET, POST, what parameter or HTTP body data does the agents exchange? how does authentication for A2A work? is it OAuth? what about mutual authentication? if the agents are from different organizations with different IdP, how does identity federate between them for A2A to work?

## 1. Communication Exchange Overview

A2A uses **JSON-RPC 2.0 over HTTPS** as the primary binding, with alternative bindings for **gRPC** (Protocol Buffers over HTTP/2) and **HTTP+JSON/REST**. All data is exchanged as JSON (or protobuf for gRPC). Agents communicate as opaque peers — they never share internal memory, tools, or reasoning.

The fundamental interaction pattern is:

1. **Client agent** sends a `Message` (with `Parts` containing text, files, or structured data) to a **server agent**
2. Server agent returns either a **direct `Message`** response or a **`Task`** object that tracks asynchronous work
3. For long-running work, the client polls, streams (SSE), or receives webhooks for updates

---

## 2. Agent Discovery — How Agents Find & Understand Each Other

### The Agent Card

Every A2A server publishes an **Agent Card** — a JSON metadata document at a well-known URL:

```
GET https://{server_domain}/.well-known/agent-card.json
```

This is an **unauthenticated HTTP GET**. The response is a JSON object describing everything a client needs to know:

```json
{
  "name": "GeoSpatial Route Planner Agent",
  "description": "Provides route planning, traffic analysis...",
  "supportedInterfaces": [
    {"url": "https://georoute-agent.example.com/a2a/v1", "protocolBinding": "JSONRPC", "protocolVersion": "1.0"},
    {"url": "https://georoute-agent.example.com/a2a/grpc", "protocolBinding": "GRPC", "protocolVersion": "1.0"},
    {"url": "https://georoute-agent.example.com/a2a/json", "protocolBinding": "HTTP+JSON", "protocolVersion": "1.0"}
  ],
  "provider": {"organization": "Example Geo Services Inc.", "url": "https://www.examplegeoservices.com"},
  "version": "1.2.0",
  "capabilities": {
    "streaming": true,
    "pushNotifications": true,
    "extendedAgentCard": true
  },
  "securitySchemes": {
    "google": {
      "openIdConnectSecurityScheme": {
        "openIdConnectUrl": "https://accounts.google.com/.well-known/openid-configuration"
      }
    }
  },
  "security": [{"google": ["openid", "profile", "email"]}],
  "defaultInputModes": ["application/json", "text/plain"],
  "defaultOutputModes": ["application/json", "image/png"],
  "skills": [
    {
      "id": "route-optimizer-traffic",
      "name": "Traffic-Aware Route Optimizer",
      "description": "Calculates optimal driving routes with real-time traffic...",
      "tags": ["maps", "routing", "navigation"],
      "examples": ["Plan a route from Mountain View to SFO avoiding tolls"],
      "inputModes": ["application/json", "text/plain"],
      "outputModes": ["application/json", "application/vnd.geo+json", "text/html"]
    }
  ]
}
```

Key fields the calling agent reads:
- **`skills`**: What the agent can do (descriptions, tags, example prompts, input/output media types)
- **`capabilities`**: Whether streaming, push notifications, or extended cards are supported
- **`securitySchemes` + `security`**: How to authenticate
- **`supportedInterfaces`**: Which protocol bindings (JSON-RPC, gRPC, REST) and their endpoint URLs
- **`defaultInputModes` / `defaultOutputModes`**: Accepted MIME types

### Extended Agent Card (Authenticated)

If `capabilities.extendedAgentCard` is `true`, the client can authenticate and call:

```
GET /extendedAgentCard
Authorization: Bearer <token>
```

This returns a richer Agent Card with additional skills/capabilities visible only to authenticated clients.

### Discovery sources

Agent Cards can be found via:
- **Well-Known URI**: `/.well-known/agent-card.json`
- **Registries/Catalogs**: Curated directories
- **Direct Configuration**: Pre-configured by developers

---

## 3. How Agents Communicate — No "Tool Parameters" Concept

**A2A does NOT expose tool schemas or function-calling parameters.** This is a deliberate design choice — agents are *opaque*. Unlike MCP (Model Context Protocol) which exposes tool definitions with parameter schemas, A2A agents communicate through **natural language messages and structured data parts**.

The called agent tells the calling agent what it needs by:
- **Returning `TASK_STATE_INPUT_REQUIRED`** with a message explaining what's needed
- **Using structured data `Parts`** with JSON schemas in metadata to request specific formats

Example multi-turn exchange:

```
Client → Server:  "Book me a flight"
Server → Client:  Task{state: INPUT_REQUIRED, message: "Where from and to?"}
Client → Server:  "From San Francisco to New York"  (same taskId)
Server → Client:  Task{state: COMPLETED, artifacts: [...]}
```

---

## 4. HTTP Methods & Body Data — The Wire Protocol

### HTTP+JSON/REST Binding

| Operation | HTTP Method | URL Pattern | Body |
|---|---|---|---|
| Send message | **POST** | `/message:send` | `SendMessageRequest` JSON |
| Stream message | **POST** | `/message:stream` | `SendMessageRequest` JSON → SSE response |
| Get task | **GET** | `/tasks/{id}` | None (query params) |
| List tasks | **GET** | `/tasks` | None (query params) |
| Cancel task | **POST** | `/tasks/{id}:cancel` | Optional metadata |
| Subscribe to task | **POST** | `/tasks/{id}:subscribe` | None → SSE response |
| Create push config | **POST** | `/tasks/{id}/pushNotificationConfigs` | `PushNotificationConfig` JSON |
| Get push config | **GET** | `/tasks/{id}/pushNotificationConfigs/{configId}` | None |
| Delete push config | **DELETE** | `/tasks/{id}/pushNotificationConfigs/{configId}` | None |
| Extended agent card | **GET** | `/extendedAgentCard` | None |

### Example: Sending a message (POST /message:send)

**Request:**
```http
POST /message:send HTTP/1.1
Host: agent.example.com
Content-Type: application/a2a+json
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
A2A-Version: 1.0

{
  "message": {
    "role": "ROLE_USER",
    "parts": [{"text": "What is the weather today?"}],
    "messageId": "msg-uuid"
  },
  "configuration": {
    "acceptedOutputModes": ["text/plain"],
    "blocking": true
  }
}
```

**Response:**
```http
HTTP/1.1 200 OK
Content-Type: application/a2a+json

{
  "task": {
    "id": "task-uuid",
    "contextId": "context-uuid",
    "status": {"state": "TASK_STATE_COMPLETED"},
    "artifacts": [{
      "artifactId": "artifact-uuid",
      "name": "Weather Report",
      "parts": [{"text": "Today will be sunny with a high of 75°F"}]
    }]
  }
}
```

### JSON-RPC Binding

All operations go to a single endpoint via **POST**, differentiated by the `method` field:

```http
POST /rpc HTTP/1.1
Content-Type: application/json
Authorization: Bearer token
A2A-Version: 1.0

{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "SendMessage",
  "params": {
    "message": {
      "role": "ROLE_USER",
      "parts": [{"text": "Hello"}],
      "messageId": "msg-uuid"
    }
  }
}
```

### Streaming (SSE)

For `POST /message:stream` (REST) or `SendStreamingMessage` (JSON-RPC), the response is `Content-Type: text/event-stream`:

```
data: {"task": {"id": "task-uuid", "status": {"state": "TASK_STATE_WORKING"}}}

data: {"artifactUpdate": {"taskId": "task-uuid", "artifact": {"parts": [{"text": "# Report\n\n"}]}}}

data: {"statusUpdate": {"taskId": "task-uuid", "status": {"state": "TASK_STATE_COMPLETED"}}}
```

### Service Parameters (Custom HTTP Headers)

- **`A2A-Version: 1.0`** — Protocol version (required)
- **`A2A-Extensions: https://example.com/ext/geo/v1,...`** — Opt-in extensions

---

## 5. Authentication

A2A is **flexible and scheme-agnostic** — it doesn't mandate a single auth mechanism. The Agent Card declares what's required, and the client obtains credentials **out-of-band**.

### Supported Security Schemes (declared in Agent Card `securitySchemes`)

| Scheme | Description |
|---|---|
| **`apiKeySecurityScheme`** | API key in header, query, or cookie |
| **`httpAuthSecurityScheme`** | HTTP auth (Bearer, Basic, etc.) |
| **`oauth2SecurityScheme`** | OAuth 2.0 with flows: Authorization Code (+PKCE), Client Credentials, Device Code |
| **`openIdConnectSecurityScheme`** | OpenID Connect (provides discovery URL) |
| **`mtlsSecurityScheme`** | Mutual TLS |

### Authentication Flow

```
1. Client fetches Agent Card (GET /.well-known/agent-card.json)
   → reads securitySchemes and security fields
   
2. Client obtains credentials OUT-OF-BAND
   (e.g., runs OAuth 2.0 flow against the declared authorization server)
   
3. Client includes credentials in every A2A request
   (Authorization: Bearer <token>, API key header, client cert, etc.)
   
4. Server validates credentials on every request
```

### Yes, OAuth 2.0 is Supported

The Agent Card can declare OAuth 2.0 with full flow configuration:

```json
"securitySchemes": {
  "myOAuth": {
    "oauth2SecurityScheme": {
      "flows": {
        "clientCredentials": {
          "tokenUrl": "https://auth.example.com/token",
          "scopes": {"agent:read": "Read access", "agent:write": "Write access"}
        }
      },
      "oauth2MetadataUrl": "https://auth.example.com/.well-known/oauth-authorization-server"
    }
  }
}
```

Supported OAuth 2.0 flows:
- **Authorization Code** (with optional PKCE)
- **Client Credentials** (machine-to-machine, most common for agent-to-agent)
- **Device Code** (for constrained devices/CLIs)
- Implicit and Password are deprecated

---

## 6. Mutual Authentication (mTLS)

**Yes, A2A explicitly supports mutual TLS.** The `MutualTlsSecurityScheme` is a first-class security scheme:

```json
"securitySchemes": {
  "mtls": {
    "mtlsSecurityScheme": {
      "description": "Client must present valid X.509 certificate"
    }
  }
}
```

With mTLS:
- The **server verifies the client's TLS certificate** during the TLS handshake
- The **client verifies the server's TLS certificate** (standard TLS)
- Both parties authenticate each other at the transport layer
- No Bearer tokens needed — identity is established via certificates

This is particularly relevant for high-security enterprise and cross-organization scenarios.

---

## 7. Cross-Organization Identity Federation

This is where it gets nuanced. The A2A spec is **deliberately agnostic** about how identity federation works between organizations with different Identity Providers (IdPs). Here's what it provides and what you need to architect:

### What A2A Specifies

1. **The Agent Card declares the auth requirements** — including OpenID Connect discovery URLs or OAuth 2.0 metadata URLs
2. **Credential acquisition is explicitly out-of-band** — the spec says the client obtains credentials "through an out-of-band process specific to the required authentication scheme"
3. **In-task auth escalation** — if an agent needs secondary credentials mid-task, it sets `TASK_STATE_AUTH_REQUIRED` and the client obtains them separately

### How Federation Works in Practice

For agents from **different organizations with different IdPs**, these standard patterns apply:

#### Pattern 1: OAuth 2.0 Token Exchange (RFC 8693)
- Org A's agent has a token from IdP-A
- Org A's agent exchanges that token at Org B's authorization server for a token Org B's agent trusts
- The Agent Card's `tokenUrl` tells the client where to exchange

#### Pattern 2: OpenID Connect Federation
- Org B's agent declares an OIDC discovery URL in its Agent Card
- Org A's agent authenticates against Org B's IdP (or a federated IdP that Org B trusts)
- Works when both orgs participate in a trust framework (e.g., SAML federation, shared OIDC trust)

#### Pattern 3: Client Credentials with Pre-Registration
- Org A pre-registers as an OAuth 2.0 client with Org B's authorization server
- Org A's agent uses `client_credentials` grant to get tokens for Org B's agent
- Most straightforward for B2B machine-to-machine scenarios

#### Pattern 4: Mutual TLS with Cross-Signed Certificates
- Both organizations use a shared CA or cross-sign certificates
- mTLS establishes identity without any token exchange
- Agent Card declares `mtlsSecurityScheme`

#### Pattern 5: External Trust Broker
- A third-party trust framework (e.g., GAIA-X, industry consortium) acts as a broker
- Agents use tokens from this broker that both organizations trust

### What A2A Does NOT Specify

- No built-in SAML support (use OIDC or token exchange instead)
- No specific federation protocol — it relies on the OpenID/OAuth ecosystem for this
- No agent identity standard — agents are treated as "standard enterprise applications" and use existing enterprise identity infrastructure
- Authorization is entirely implementation-specific — each agent defines its own policies based on the authenticated identity

---

## Summary

| Aspect | A2A Approach |
|---|---|
| **Wire protocol** | JSON-RPC 2.0 / gRPC / HTTP+JSON over HTTPS |
| **Discovery** | Agent Card at `/.well-known/agent-card.json` (HTTP GET) |
| **Capability advertising** | Skills, input/output modes, capabilities in Agent Card |
| **Parameter exchange** | No tool schemas — agents use messages, multi-turn `INPUT_REQUIRED`, and structured data parts |
| **Primary HTTP methods** | POST (send/stream/cancel), GET (tasks/agent card), DELETE (push configs) |
| **Content type** | `application/a2a+json` or `application/json` |
| **Auth mechanisms** | API Key, HTTP Bearer, OAuth 2.0, OpenID Connect, mTLS — declared in Agent Card |
| **Mutual auth** | Supported via `mtlsSecurityScheme` |
| **Cross-org federation** | Out-of-band via standard OAuth 2.0/OIDC federation, token exchange (RFC 8693), or mTLS with shared CAs | 

Completed: *Synthesize comprehensive answer* (5/5)
