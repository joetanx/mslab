# AutoSOC autonomous incident triage

AutoSOC receives a Microsoft Defender incident ID from a Sentinel Logic App,
acknowledges it immediately, and completes triage in an in-process LangGraph
workflow on Azure Container Apps.

## Workflow

1. `POST /api/triage` validates the Logic App managed-identity access token.
2. The service returns `202 Accepted` and owns the work as an asyncio task.
3. LangGraph loads the incident and associated alerts, then extracts a bounded
	incident overview and entity set with structured model output.
4. An orchestrator selects eligible hunts from a fixed catalog. It cannot emit
	executable KQL.
5. Selected hunts run in parallel and return projected, bounded evidence.
6. A structured assessment classifies the incident as false positive, benign
	true positive, true positive, or suspicious.
7. A deterministic node writes one consolidated comment and updates the
	incident status, classification, determination, and assignee.

The initial catalog includes related alerts, threat intelligence, Windows
sign-in failures, Linux SSH failures, and Entra sign-in failures. Every query
has explicit projections and a 100-row bound. Entity values are JSON-encoded
inside KQL `dynamic` literals rather than inserted as query structure.

## HTTP API

Send a bearer token and JSON body:

```http
POST /api/triage HTTP/1.1
Authorization: Bearer <access-token>
Content-Type: application/json

{"incidentId":"12345"}
```

The response is returned before model or Graph work starts:

```json
{
  "status": "accepted",
  "incidentId": "12345",
  "correlationId": "d26f4c21-2264-4f20-bb3e-e60ff15bdbb5"
}
```

Submitting the same incident while it is active returns `202` with
`status: "already_accepted"` and the original correlation ID. `GET
/api/health` does not require authentication.

## Entra configuration

Expose an API scope or application ID URI for AutoSOC, for example
`api://<autosoc-app-client-id>`. Set that value as `AUTOSOC_API_AUDIENCE`.
Configure the Logic App HTTP action to request a managed-identity token for
that audience.

AutoSOC validates all of the following before accepting a request:

- Microsoft signature using the tenant OpenID signing keys
- token expiry and issued-at time
- issuer and `tid` against `ENTRA_TENANT_ID`
- `aud` against `AUTOSOC_API_AUDIENCE`

The Container App user-assigned managed identity federates to the Agent 365
blueprint. Microsoft Graph calls then use an exchanged agent-user token. Grant
the Defender roles/Graph permissions required for triage to that agent user,
including:

- `ThreatHunting.Read.All`
- `SecurityIncident.Read.All`
- `SecurityIncident.ReadWrite.All`
- `SecurityAlert.Read.All`

The Container App managed identity separately needs access to the configured
Azure AI Foundry project and model deployment.

## Configuration

Required environment variables:

| Variable | Purpose |
| --- | --- |
| `ENTRA_TENANT_ID` | Tenant allowed to call the webhook |
| `AUTOSOC_API_AUDIENCE` | Required bearer-token audience |
| `UAMI_CLIENT_ID` | Container App user-assigned managed identity |
| `FOUNDRY_PROJECT_ENDPOINT` | Azure AI Foundry project endpoint |
| `FOUNDRY_MODEL` | Deployed chat model name |
| `ASSIGNEE_IN_PROGRESS` | Analyst or queue assigned to suspicious/true-positive incidents |
| `ASSIGNEE_RESOLVED` | Analyst or queue assigned to resolved incidents |

Agentic authentication also requires the `CONNECTIONS__SERVICE_CONNECTION__*`,
`AGENTIC_INSTANCE_ID`, and `AGENTIC_USER_ID` settings shown in
`containerapp.yaml`. The service connection exchanges and caches the agent-user
token, refreshing it before expiry.

Execution controls have defaults and can be overridden:

| Variable | Default |
| --- | ---: |
| `MAX_CONCURRENT_TRIAGE` | `2` |
| `MAX_HUNTS_PER_INCIDENT` | `5` |
| `TRIAGE_TIMEOUT_SECONDS` | `300` |
| `TRIAGE_SHUTDOWN_TIMEOUT_SECONDS` | `60` |
| `GRAPH_REQUEST_TIMEOUT_SECONDS` | `60` |
| `GRAPH_MAX_ATTEMPTS` | `4` |
| `MAX_REQUEST_BYTES` | `16384` |

## Run and test

```powershell
python -m pip install -e ".[test]"
python -m pytest -q
$env:ENTRA_TENANT_ID = "<tenant-id>"
$env:AUTOSOC_API_AUDIENCE = "api://<autosoc-app-client-id>"
$env:UAMI_CLIENT_ID = "<managed-identity-client-id>"
$env:FOUNDRY_PROJECT_ENDPOINT = "<project-endpoint>"
$env:FOUNDRY_MODEL = "<model-deployment>"
python app/server.py
```

Build the dependency-only deployment image from this directory:

```powershell
docker build -t autosoc:latest .
```

The image does not contain the application source. The supplied
`containerapp.yaml` mounts the `${APP_NAME}` Azure Files volume at `/app`, and
the container starts the mounted `server.py`. It intentionally fixes the
deployment at one replica because accepted tasks, duplicate suppression, and
LangGraph checkpoints are process-local.

## Delivery semantics and operations

`202 Accepted` means that the current process accepted the task. It does not
mean durable delivery. A process failure, forced revision replacement, or
node loss can abandon active work. The service drains tasks for
`TRIAGE_SHUTDOWN_TIMEOUT_SECONDS` during an orderly shutdown, but it does not
provide a queue, status endpoint, or durable checkpoint store.

Use the response correlation ID to trace the incident lifecycle in Container
Apps application logs. Successful runs also leave the consolidated evidence
and assessment on the Defender incident. Failed runs attempt to leave a short
failure comment containing the correlation ID.