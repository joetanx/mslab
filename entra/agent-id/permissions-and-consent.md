## 0. Prerequisites

References:
- [Create agent blueprint, agent blueprint principal, configure credentials for agent blueprint](https://learn.microsoft.com/en-us/entra/agent-id/identity-platform/create-blueprint)
- [Create agent identities](https://learn.microsoft.com/en-us/entra/agent-id/identity-platform/create-delete-agent-identities)

### 0.1. Provisioning application

The procedures writen below uses an application with the necessary [permissions required](/entra/agent-id#2-apis-and-permissions-requried-to-provision-entra-agent-identity-objects) to perform the provisioning

![](https://github.com/user-attachments/assets/6fb98a54-e699-4921-bcb1-0c21349113a6)

### 0.2. Staging the provisioning application

|Parameter|Value|
|---|---|
|`<tenant-id>`|Entra tenant ID|
|`<provisioning-app-id>`|App ID of the provisioning application|
|`<provisioning-app-secret>`|Client secret of provisioning application|

Get access token for the provisioning application with client credential flow and put it in `$header`

```pwsh
$tenant = '<tenant-id>'
$clientid = '<provisioning-app-id>'
$clientsecret = '<provisioning-app-secret>'
$token_endpoint = "https://login.microsoftonline.com/$tenant/oauth2/v2.0/token"
$body=@{
  client_id = $clientid
  client_secret = $clientsecret
  grant_type = 'client_credentials'
  scope = 'https://graph.microsoft.com/.default'
}
Invoke-RestMethod $token_endpoint -Method Post -Body $body | Tee-Object -Variable token
$headers = @{ Authorization='Bearer '+$token.access_token }
```

## 1. Agent blueprint inheritable permissions [ᵈᵒᶜ](https://learn.microsoft.com/en-us/entra/agent-id/identity-professional/configure-inheritable-permissions-blueprints)

> To be eligible for inheritance, the agent blueprint service principal must already hold OAuth2PermissionGrants for those scopes to the target resource app.

### 1.1. Get Graph API service principal ID and delegated permission ID

Using `SecurityIncident.Read.All` as example delegated permission to be granted

```pwsh
$endpointuri = "https://graph.microsoft.com/v1.0/servicePrincipals(appId='00000003-0000-0000-c000-000000000000')"
Invoke-RestMethod $endpointuri -Headers $headers | Tee-Object -Variable GraphSP
$role = 'SecurityIncident.Read.All'
$DelegatedRole = $GraphSP.oauth2PermissionScopes | ? { $_.value -eq $role }
```

### 1.2. Grant delegated permission to agent blueprint

#### 1.2.A. Separate permission grant and admin consent

##### 1.2.A.1. Grant delegated permissions [ᵈᵒᶜ](https://learn.microsoft.com/en-us/graph/api/application-update)

```pwsh
$endpointuri = "https://graph.microsoft.com/beta/applications/$($AgentIdBp.id)"
$body = @{
  requiredResourceAccess = @(
    @{
      resourceAppId = '00000003-0000-0000-c000-000000000000'
      resourceAccess = @(
        @{
          id = $DelegatedRole.id
          type = 'Scope'
        }
      )
    }
  )
}
Invoke-RestMethod $endpointuri -Method Patch -Headers $headers -Body $($body | ConvertTo-Json -Depth 4) -ContentType 'application/json'
```

##### 1.2.A.2. Request authorization from a tenant administrator [ᵈᵒᶜ](https://learn.microsoft.com/en-us/entra/agent-id/identity-platform/autonomous-agent-request-authorization-entra-admin?tabs=microsoft-graph-api)

Prepare the consent URL and use `Start-Process` to launch in browser:

```pwsh
$state = [guid]::NewGuid().ToString()
$consent_url = "https://login.microsoftonline.com/$tenant/v2.0/adminconsent" +
  "?client_id=$($AgentIdBp.id)" +
  "&role=https://graph.microsoft.com/$role" +
  '&redirect_uri=https://entra.microsoft.com/TokenAuthorize' +
  "&state=$State"
Start-Process $consent_url
```

Sign in as tenant administrator to approve:

![](https://github.com/user-attachments/assets/a3291e0d-397a-4a59-a10f-737df34221f4)

#### 1.2.B. Grant to agent blueprint principal with `DelegatedPermissionGrant.ReadWrite.All` permission



## 1.2. Configure inheritable permissions on agent blueprint [ᵈᵒᶜ](https://learn.microsoft.com/en-us/graph/api/agentidentityblueprint-post-inheritablepermissions)

> [!Note]
>
> Although doc says that `AgentIdentityBlueprint.Create` is the minimum permission, it seems like `AgentIdentityBlueprint.ReadWrite.All` is required to configure inheritable permissions

```pwsh
$endpointuri = "https://graph.microsoft.com/beta/applications/$($AgentIdBp.id)/microsoft.graph.agentIdentityBlueprint/inheritablePermissions"
$body=@{
  resourceAppId = '00000003-0000-0000-c000-000000000000'
  inheritableScopes = @{
    '@odata.type' = 'microsoft.graph.enumeratedScopes'
    scopes = @(
      $role
    )
  }
}
Invoke-RestMethod $endpointuri -Method Post -Headers $headers -Body $($body | ConvertTo-Json) -ContentType 'application/json'
```

## 1.3. List inheritable permissions [ᵈᵒᶜ](https://learn.microsoft.com/en-us/graph/api/agentidentityblueprint-list-inheritablepermissions)

```pwsh
$endpointuri = "https://graph.microsoft.com/beta/applications/$($AgentIdBp.id)/microsoft.graph.agentIdentityBlueprint/inheritablePermissions"
Invoke-RestMethod $endpointuri -Headers $headers
```

### X.X. Get Graph API service principal ID and application permission ID

Using `SecurityIncident.Read.All` as example application permission to be granted

```pwsh
$endpointuri = "https://graph.microsoft.com/v1.0/servicePrincipals(appId='00000003-0000-0000-c000-000000000000')"
Invoke-RestMethod $endpointuri -Headers $headers | Tee-Object -Variable GraphSP
$role = 'SecurityIncident.Read.All'
$AppRole = $GraphSP.appRoles | ? { $_.value -eq $role }





