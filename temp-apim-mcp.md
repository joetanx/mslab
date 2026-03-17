> Prompt:
>
> I want to convert Microsoft Graph API to MCP via Azure API management. the Graph APIs require OAuth token from Entra for authorization. The MCP server exposed by Azure APIM should also be integrated to Entra for OAuth authorization. I want to pass through the token from the MCP Server OAuth authorization to the backend Graph API

# Converting Microsoft Graph API to MCP via Azure API Management with OAuth Passthrough

This is a multi-layered integration involving:

1. **MCP Server** exposed via Azure APIM
2. **Entra ID (Azure AD) OAuth** for both the MCP client and the backend Graph API
3. **Token passthrough** from the MCP OAuth flow to Microsoft Graph

## Architecture Overview

```
MCP Client → (OAuth token) → Azure APIM (MCP Server) → (same/exchanged token) → Microsoft Graph API
                                    ↕
                              Azure Entra ID
```

## Step 1: Register App in Entra ID

Register a single app (or two apps) in Azure Entra ID that has **delegated permissions** for Microsoft Graph.

**Single App Registration approach (simplest for passthrough):**

- Go to **Azure Portal → Entra ID → App registrations → New registration**
- Set redirect URI for your MCP client
- Under **API permissions**, add the Microsoft Graph delegated permissions you need (e.g., `User.Read`, `Mail.Read`, etc.)
- Under **Expose an API**, define a scope (e.g., `api://<client-id>/MCP.Access`)
- Under **Certificates & secrets**, create a client secret
- Grant admin consent for the Graph permissions

## Step 2: Configure Azure APIM as MCP Server

### 2a. Enable MCP Server Protocol in APIM

Azure APIM supports exposing APIs as MCP servers. Define your MCP server specification:

````json
{
  "openapi": "3.0.1",
  "info": {
    "title": "Graph MCP Server",
    "version": "1.0.0"
  },
  "servers": [
    {
      "url": "https://<your-apim>.azure-api.net/graph-mcp"
    }
  ],
  "paths": {
    "/tools/list": {
      "post": {
        "operationId": "listTools",
        "summary": "List available Graph tools",
        "responses": {
          "200": {
            "description": "List of available MCP tools"
          }
        }
      }
    },
    "/tools/call": {
      "post": {
        "operationId": "callTool",
        "summary": "Call a Graph tool",
        "requestBody": {
          "required": true,
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/ToolCallRequest"
              }
            }
          }
        },
        "responses": {
          "200": {
            "description": "Tool execution result"
          }
        }
      }
    }
  },
  "components": {
    "schemas": {
      "ToolCallRequest": {
        "type": "object",
        "properties": {
          "name": { "type": "string" },
          "arguments": { "type": "object" }
        },
        "required": ["name"]
      }
    },
    "securitySchemes": {
      "oauth2": {
        "type": "oauth2",
        "flows": {
          "authorizationCode": {
            "authorizationUrl": "https://login.microsoftonline.com/<tenant-id>/oauth2/v2.0/authorize",
            "tokenUrl": "https://login.microsoftonline.com/<tenant-id>/oauth2/v2.0/token",
            "scopes": {
              "api://<client-id>/MCP.Access": "Access MCP Server"
            }
          }
        }
      }
    }
  },
  "security": [
    { "oauth2": ["api://<client-id>/MCP.Access"] }
  ]
}
````

### 2b. Configure APIM OAuth 2.0 Authorization Server

In Azure Portal → APIM → **OAuth 2.0 + OpenID Connect**:

````xml
<!--
  APIM Portal Configuration:
  - Authorization endpoint: https://login.microsoftonline.com/<tenant-id>/oauth2/v2.0/authorize
  - Token endpoint: https://login.microsoftonline.com/<tenant-id>/oauth2/v2.0/token
  - Client ID: <your-app-client-id>
  - Client Secret: <your-app-client-secret>
  - Default scope: api://<client-id>/MCP.Access openid profile
  - Authorization grant types: Authorization code
-->
````

## Step 3: Configure APIM Policies for Token Passthrough

This is the critical part. You need to **validate the incoming OAuth token** and then **pass it through (or exchange it) to Microsoft Graph**.

### Option A: Direct Token Passthrough (Same Audience)

If the MCP client requests a token with **Microsoft Graph scopes directly**, you can pass the token straight through:

````xml
<policies>
    <inbound>
        <base />

        <!-- Validate the JWT token from the MCP client -->
        <validate-jwt header-name="Authorization" failed-validation-httpcode="401"
                      failed-validation-error-message="Unauthorized. Invalid token.">
            <openid-config url="https://login.microsoftonline.com/<tenant-id>/v2.0/.well-known/openid-configuration" />
            <audiences>
                <!-- Accept tokens for both your app and Microsoft Graph -->
                <audience>api://<client-id></audience>
                <audience>https://graph.microsoft.com</audience>
            </audiences>
            <issuers>
                <issuer>https://login.microsoftonline.com/<tenant-id>/v2.0</issuer>
                <issuer>https://sts.windows.net/<tenant-id>/</issuer>
            </issuers>
        </validate-jwt>

        <!-- Extract the bearer token from the incoming request -->
        <set-variable name="bearerToken"
                      value="@(context.Request.Headers.GetValueOrDefault("Authorization", ""))" />

        <!-- Route MCP tool calls to the appropriate Graph endpoint -->
        <choose>
            <when condition="@(context.Request.Body.As<JObject>(preserveContent: true)["name"]?.ToString() == "get_user_profile")">
                <set-backend-service base-url="https://graph.microsoft.com/v1.0" />
                <rewrite-uri template="/me" />
                <set-method>GET</set-method>
            </when>
            <when condition="@(context.Request.Body.As<JObject>(preserveContent: true)["name"]?.ToString() == "list_messages")">
                <set-backend-service base-url="https://graph.microsoft.com/v1.0" />
                <rewrite-uri template="/me/messages" />
                <set-method>GET</set-method>
            </when>
            <when condition="@(context.Request.Body.As<JObject>(preserveContent: true)["name"]?.ToString() == "list_calendar_events")">
                <set-backend-service base-url="https://graph.microsoft.com/v1.0" />
                <rewrite-uri template="/me/events" />
                <set-method>GET</set-method>
            </when>
        </choose>

        <!-- Pass the original token to Graph API -->
        <set-header name="Authorization" exists-action="override">
            <value>@((string)context.Variables["bearerToken"])</value>
        </set-header>
    </inbound>

    <backend>
        <base />
    </backend>

    <outbound>
        <base />
        <!-- Transform Graph API response into MCP tool response format -->
        <set-body>@{
            var response = context.Response.Body.As<JObject>();
            var mcpResponse = new JObject
            {
                ["content"] = new JArray
                {
                    new JObject
                    {
                        ["type"] = "text",
                        ["text"] = response.ToString()
                    }
                }
            };
            return mcpResponse.ToString();
        }</set-body>
        <set-header name="Content-Type" exists-action="override">
            <value>application/json</value>
        </set-header>
    </outbound>

    <on-error>
        <base />
    </on-error>
</policies>
````

### Option B: On-Behalf-Of (OBO) Token Exchange (Recommended)

If the MCP client acquires a token scoped to **your app's API** (`api://<client-id>/MCP.Access`), you need to exchange it for a Graph token using the **OBO flow**:

````xml
<policies>
    <inbound>
        <base />

        <!-- Validate the incoming MCP OAuth token -->
        <validate-jwt header-name="Authorization" failed-validation-httpcode="401"
                      failed-validation-error-message="Unauthorized. Invalid token."
                      output-token-variable-name="jwt">
            <openid-config url="https://login.microsoftonline.com/<tenant-id>/v2.0/.well-known/openid-configuration" />
            <audiences>
                <audience>api://<client-id></audience>
            </audiences>
            <issuers>
                <issuer>https://login.microsoftonline.com/<tenant-id>/v2.0</issuer>
            </issuers>
            <required-claims>
                <claim name="scp" match="any">
                    <value>MCP.Access</value>
                </claim>
            </required-claims>
        </validate-jwt>

        <!-- Extract the raw bearer token (without "Bearer " prefix) -->
        <set-variable name="incomingToken"
                      value="@(context.Request.Headers.GetValueOrDefault("Authorization", "").Replace("Bearer ", ""))" />

        <!-- Exchange the token using OBO flow -->
        <send-request mode="new" response-variable-name="oboResponse" timeout="20" ignore-error="false">
            <set-url>https://login.microsoftonline.com/<tenant-id>/oauth2/v2.0/token</set-url>
            <set-method>POST</set-method>
            <set-header name="Content-Type" exists-action="override">
                <value>application/x-www-form-urlencoded</value>
            </set-header>
            <set-body>@{
                return String.Format(
                    "grant_type=urn:ietf:params:oauth:grant-type:jwt-bearer" +
                    "&client_id=<client-id>" +
                    "&client_secret=<client-secret-from-named-value>" +
                    "&assertion={0}" +
                    "&scope=https://graph.microsoft.com/.default" +
                    "&requested_token_use=on_behalf_of",
                    (string)context.Variables["incomingToken"]
                );
            }</set-body>
        </send-request>

        <!-- Extract the Graph token from OBO response -->
        <set-variable name="graphToken"
                      value="@{
                          var response = ((IResponse)context.Variables["oboResponse"]).Body.As<JObject>();
                          return (string)response["access_token"];
                      }" />

        <!-- Check if token exchange succeeded -->
        <choose>
            <when condition="@(context.Variables.GetValueOrDefault<string>("graphToken") == null)">
                <return-response>
                    <set-status code="403" reason="Token exchange failed" />
                    <set-body>@{
                        return new JObject
                        {
                            ["error"] = "Failed to exchange token for Microsoft Graph access"
                        }.ToString();
                    }</set-body>
                </return-response>
            </when>
        </choose>

        <!-- Parse the MCP tool call and route to Graph -->
        <set-variable name="mcpRequest"
                      value="@(context.Request.Body.As<JObject>(preserveContent: true))" />

        <choose>
            <when condition="@(((JObject)context.Variables["mcpRequest"])["name"]?.ToString() == "get_user_profile")">
                <set-backend-service base-url="https://graph.microsoft.com/v1.0" />
                <rewrite-uri template="/me" />
                <set-method>GET</set-method>
            </when>
            <when condition="@(((JObject)context.Variables["mcpRequest"])["name"]?.ToString() == "list_messages")">
                <set-backend-service base-url="https://graph.microsoft.com/v1.0" />
                <rewrite-uri template="@{
                    var args = ((JObject)context.Variables["mcpRequest"])["arguments"];
                    var top = args?["top"]?.ToString() ?? "10";
                    return "/me/messages?$top=" + top;
                }" />
                <set-method>GET</set-method>
            </when>
            <when condition="@(((JObject)context.Variables["mcpRequest"])["name"]?.ToString() == "list_calendar_events")">
                <set-backend-service base-url="https://graph.microsoft.com/v1.0" />
                <rewrite-uri template="/me/events" />
                <set-method>GET</set-method>
            </when>
            <when condition="@(((JObject)context.Variables["mcpRequest"])["name"]?.ToString() == "search_users")">
                <set-backend-service base-url="https://graph.microsoft.com/v1.0" />
                <rewrite-uri template="@{
                    var args = ((JObject)context.Variables["mcpRequest"])["arguments"];
                    var query = args?["query"]?.ToString() ?? "";
                    return "/users?$filter=startswith(displayName,'" + Uri.EscapeDataString(query) + "')";
                }" />
                <set-method>GET</set-method>
            </when>
            <otherwise>
                <return-response>
                    <set-status code="400" reason="Unknown tool" />
                    <set-body>@{
                        return new JObject
                        {
                            ["content"] = new JArray {
                                new JObject {
                                    ["type"] = "text",
                                    ["text"] = "Unknown tool: " + ((JObject)context.Variables["mcpRequest"])["name"]?.ToString()
                                }
                            },
                            ["isError"] = true
                        }.ToString();
                    }</set-body>
                </return-response>
            </otherwise>
        </choose>

        <!-- Set the Graph token for the backend call -->
        <set-header name="Authorization" exists-action="override">
            <value>@("Bearer " + (string)context.Variables["graphToken"])</value>
        </set-header>
    </inbound>

    <backend>
        <base />
    </backend>

    <outbound>
        <base />
        <!-- Transform Graph response to MCP format -->
        <set-body>@{
            var graphResponse = context.Response.Body.As<string>();
            var mcpResponse = new JObject
            {
                ["content"] = new JArray
                {
                    new JObject
                    {
                        ["type"] = "text",
                        ["text"] = graphResponse
                    }
                }
            };
            return mcpResponse.ToString();
        }</set-body>
    </outbound>

    <on-error>
        <base />
        <set-body>@{
            return new JObject
            {
                ["content"] = new JArray
                {
                    new JObject
                    {
                        ["type"] = "text",
                        ["text"] = "Error: " + context.LastError.Message
                    }
                },
                ["isError"] = true
            }.ToString();
        }</set-body>
    </on-error>
</policies>
````

## Step 4: Store Secrets Using APIM Named Values

Never hardcode secrets in policies. Use **Named Values** backed by **Key Vault**:

````powershell
# Store client secret in Key Vault and reference from APIM
az keyvault secret set --vault-name <keyvault-name> --name "graph-client-secret" --value "<client-secret>"

# Create Named Value in APIM referencing Key Vault
az apim nv create --resource-group <rg> --service-name <apim-name> \
    --named-value-id graph-client-secret \
    --display-name "graph-client-secret" \
    --secret true \
    --key-vault "https://<keyvault-name>.vault.azure.net/secrets/graph-client-secret"
````

Then reference it in the policy:

````xml
<!-- Replace hardcoded client_secret with -->
<set-variable name="clientSecret" value="{{graph-client-secret}}" />
````

## Step 5: MCP Tools List Endpoint

Add a separate policy for the `/tools/list` endpoint:

````xml
<policies>
    <inbound>
        <base />
        <validate-jwt header-name="Authorization" failed-validation-httpcode="401"
                      failed-validation-error-message="Unauthorized">
            <openid-config url="https://login.microsoftonline.com/<tenant-id>/v2.0/.well-known/openid-configuration" />
            <audiences>
                <audience>api://<client-id></audience>
            </audiences>
        </validate-jwt>
        <return-response>
            <set-status code="200" />
            <set-header name="Content-Type" exists-action="override">
                <value>application/json</value>
            </set-header>
            <set-body>@{
                var tools = new JObject
                {
                    ["tools"] = new JArray
                    {
                        new JObject
                        {
                            ["name"] = "get_user_profile",
                            ["description"] = "Get the authenticated user's profile from Microsoft Graph",
                            ["inputSchema"] = new JObject
                            {
                                ["type"] = "object",
                                ["properties"] = new JObject(),
                                ["required"] = new JArray()
                            }
                        },
                        new JObject
                        {
                            ["name"] = "list_messages",
                            ["description"] = "List the user's email messages",
                            ["inputSchema"] = new JObject
                            {
                                ["type"] = "object",
                                ["properties"] = new JObject
                                {
                                    ["top"] = new JObject
                                    {
                                        ["type"] = "integer",
                                        ["description"] = "Number of messages to return (default 10)"
                                    }
                                }
                            }
                        },
                        new JObject
                        {
                            ["name"] = "list_calendar_events",
                            ["description"] = "List the user's calendar events",
                            ["inputSchema"] = new JObject
                            {
                                ["type"] = "object",
                                ["properties"] = new JObject(),
                                ["required"] = new JArray()
                            }
                        },
                        new JObject
                        {
                            ["name"] = "search_users",
                            ["description"] = "Search for users in the directory",
                            ["inputSchema"] = new JObject
                            {
                                ["type"] = "object",
                                ["properties"] = new JObject
                                {
                                    ["query"] = new JObject
                                    {
                                        ["type"] = "string",
                                        ["description"] = "Search query for user display name"
                                    }
                                },
                                ["required"] = new JArray { "query" }
                            }
                        }
                    }
                };
                return tools.ToString();
            }</set-body>
        </return-response>
    </inbound>
</policies>
````

## Step 6: MCP Client Configuration

Configure the MCP client (e.g., VS Code, Claude Desktop) to connect:

````json
{
  "mcpServers": {
    "microsoft-graph": {
      "url": "https://<your-apim>.azure-api.net/graph-mcp",
      "transport": "streamable-http",
      "auth": {
        "type": "oauth2",
        "authorizationUrl": "https://login.microsoftonline.com/<tenant-id>/oauth2/v2.0/authorize",
        "tokenUrl": "https://login.microsoftonline.com/<tenant-id>/oauth2/v2.0/token",
        "clientId": "<client-id>",
        "scopes": ["api://<client-id>/MCP.Access"],
        "redirectUri": "http://localhost:3000/callback"
      }
    }
  }
}
````

## Summary: Decision Matrix

| Approach | When to Use | Complexity |
|----------|-------------|------------|
| **Direct Passthrough** (Option A) | MCP client can request Graph-scoped tokens directly | Low |
| **OBO Exchange** (Option B) | MCP client gets token for your API; backend needs Graph token | Medium (recommended) |

## Key Points

- **Option B (OBO) is recommended** because it maintains proper audience separation — the MCP client authenticates to *your API*, and APIM handles the token exchange to Graph
- Use **APIM Named Values + Key Vault** for all secrets
- Ensure the Entra app registration has `api://<client-id>/MCP.Access` scope exposed and Graph API delegated permissions with **admin consent**
- The OBO flow preserves the **user's identity**, so Graph API calls are made in the context of the authenticated user

Similar code found with 2 license types
