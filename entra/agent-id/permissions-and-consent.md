## 0. Prerequisites

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

## 1. Grant delegated permission to agent blueprint

[Delegated permissions](https://learn.microsoft.com/en-us/graph/permissions-overview#delegated-permissions), also called _scopes_, requires **interactive** user sign-in

The application acts **on behalf of** a signed-in user; access is scoped to the signed-in user's privileges

The application **cannot** access anything the signed-in user couldn't access

### 1.1. Get Graph API service principal ID and delegated permission ID

Using `SecurityIncident.Read.All` as example delegated permission to be granted

```pwsh
$endpointuri = "https://graph.microsoft.com/v1.0/servicePrincipals(appId='00000003-0000-0000-c000-000000000000')"
Invoke-RestMethod $endpointuri -Headers $headers | Tee-Object -Variable GraphSP
$PermissionName = 'SecurityIncident.Read.All'
$DelegatedRole = $GraphSP.oauth2PermissionScopes | ? { $_.value -eq $PermissionName }
```

### 1.2A. Grant permission to _application_, then get admin consent from a tenant administrator

#### 1.2A.1. Grant permission to _application_ [ᵈᵒᶜ](https://learn.microsoft.com/en-us/graph/api/application-update)

> [!Note]
>
> Use `type`: `Scope` when granting delegated permission

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

#### 1.2A.2. Request authorization from a tenant administrator [ᵈᵒᶜ](https://learn.microsoft.com/en-us/entra/agent-id/identity-platform/autonomous-agent-request-authorization-entra-admin?tabs=microsoft-graph-api)

Prepare the consent URL and use `Start-Process` to launch in browser:

> [!Note]
>
> Use `scope`: `https://graph.microsoft.com/$PermissionName` when granting delegated permission

```pwsh
$state = [guid]::NewGuid().ToString()
$consent_url = "https://login.microsoftonline.com/$tenant/v2.0/adminconsent" +
  "?client_id=$($AgentIdBp.id)" +
  "&scope=https://graph.microsoft.com/$PermissionName" +
  '&redirect_uri=https://entra.microsoft.com/TokenAuthorize' +
  "&state=$State"
Start-Process $consent_url
```

Sign in as tenant administrator to approve:

![](https://github.com/user-attachments/assets/eabc4076-ad72-46ef-a28f-17440f5d1744)

### 1.2B. Grant permission to _service principal_ with `DelegatedPermissionGrant.ReadWrite.All` permission [ᵈᵒᶜ](https://learn.microsoft.com/en-us/graph/api/oauth2permissiongrant-post)

> [!Warning]
>
> `DelegatedPermissionGrant.ReadWrite.All` allows a principal to grant admin consent for `Delegated` permissions

```pwsh
$endpointuri = "https://graph.microsoft.com/v1.0/oauth2PermissionGrants"
$body=@{
  clientId = $AgentIdBpPrincipal.id
  consentType = 'AllPrincipals'
  resourceId = $GraphSP.id
  scope = $PermissionName
}
Invoke-RestMethod $endpointuri -Method Post -Headers $headers -Body $($body | ConvertTo-Json) -ContentType 'application/json'
```

## 2. Grant application permission to agent blueprint

[Application permissions](https://learn.microsoft.com/en-us/graph/permissions-overview#application-permissions), also called _app roles_, enables **non-interactive** access without a signed-in user present

The application can access any data that the permission is associated with

### 2.1. Get Graph API service principal ID and application permission ID

Using `SecurityIncident.Read.All` as example application permission to be granted

```pwsh
$endpointuri = "https://graph.microsoft.com/v1.0/servicePrincipals(appId='00000003-0000-0000-c000-000000000000')"
Invoke-RestMethod $endpointuri -Headers $headers | Tee-Object -Variable GraphSP
$PermissionName = 'SecurityIncident.Read.All'
$AppRole = $GraphSP.appRoles | ? { $_.value -eq $PermissionName }
```

### 2.2A. Grant permission to _application_, then get admin consent from a tenant administrator

#### 2.2A.1. Grant permission to _application_ [ᵈᵒᶜ](https://learn.microsoft.com/en-us/graph/api/application-update)

> [!Note]
>
> Use `type`: `Role` when granting application permission

```pwsh
$endpointuri = "https://graph.microsoft.com/beta/applications/$($AgentIdBp.id)"
$body = @{
  requiredResourceAccess = @(
    @{
      resourceAppId = '00000003-0000-0000-c000-000000000000'
      resourceAccess = @(
        @{
          id = $AppRole.id
          type = 'Role'
        }
      )
    }
  )
}
Invoke-RestMethod $endpointuri -Method Patch -Headers $headers -Body $($body | ConvertTo-Json -Depth 4) -ContentType 'application/json'
```

#### 2.2A.2. Request authorization from a tenant administrator [ᵈᵒᶜ](https://learn.microsoft.com/en-us/entra/agent-id/identity-platform/autonomous-agent-request-authorization-entra-admin?tabs=microsoft-graph-api)

Prepare the consent URL and use `Start-Process` to launch in browser:

> [!Note]
>
> Use `role`: `https://graph.microsoft.com/$PermissionName` when granting application permission

```pwsh
$state = [guid]::NewGuid().ToString()
$consent_url = "https://login.microsoftonline.com/$tenant/v2.0/adminconsent" +
  "?client_id=$($AgentIdBp.id)" +
  "&role=https://graph.microsoft.com/$PermissionName" +
  '&redirect_uri=https://entra.microsoft.com/TokenAuthorize' +
  "&state=$State"
Start-Process $consent_url
```

Sign in as tenant administrator to approve:

![](https://github.com/user-attachments/assets/862a46ee-427d-4778-8027-b17532f88177)

### 2.2B. Grant to permission to _service principal_ with `AppRoleAssignment.ReadWrite.All` permission [ᵈᵒᶜ](https://learn.microsoft.com/en-us/graph/api/serviceprincipal-post-approleassignments)

> [!Warning]
>
> `AppRoleAssignment.ReadWrite.All` allows a principal to grant admin consent for `Application` permissions

```pwsh
$endpointuri = "https://graph.microsoft.com/v1.0/servicePrincipals/$($AgentIdBpPrincipal.id)/appRoleAssignments"
$body=@{
  principalId = $AgentIdBpPrincipal.id
  resourceId = $GraphSP.id
  appRoleId = $AppRole.id
}
Invoke-RestMethod $endpointuri -Method Post -Headers $headers -Body $($body | ConvertTo-Json) -ContentType 'application/json'
```

## 3. Misc permissions troubleshooing

### 3.1. Application

#### 3.1.1. List permissions

```pwsh
$endpointuri = "https://graph.microsoft.com/v1.0/applications/$($AgentIdBp.id)"
(Invoke-RestMethod $endpointuri -Headers $headers).requiredResourceAccess
```

#### 3.1.2. Remove permissions

> [!Note]
>
> This empties `requiredResourceAccess`, clearing **ALL** permissions from the _application_

```pwsh
$endpointuri = "https://graph.microsoft.com/beta/applications/$($AgentIdBp.id)"
$body = @{
  requiredResourceAccess = @()
}
Invoke-RestMethod $endpointuri -Method Patch -Headers $headers -Body $($body | ConvertTo-Json -Depth 4) -ContentType 'application/json'
```

### 3.2. Service principal

#### 3.2.1. Check oauth2PermissionGrants [ᵈᵒᶜ](https://learn.microsoft.com/en-us/graph/api/serviceprincipal-list-oauth2permissiongrants)

```pwsh
$endpointuri = "https://graph.microsoft.com/v1.0/servicePrincipals/$($AgentIdBpPrincipal.id)/oauth2PermissionGrants"
Invoke-RestMethod $endpointuri -Headers $headers | Tee-Object -Variable oauth2PermissionGrants
$oauth2PermissionGrants.value
```

#### 3.2.2. Remove oauth2PermissionGrants [ᵈᵒᶜ](https://learn.microsoft.com/en-us/graph/api/oauth2permissiongrant-delete)

```pwsh
for ($i = 0; $i -lt $oauth2PermissionGrants.value.Length; $i++) {
  $endpointuri = "https://graph.microsoft.com/v1.0/oauth2PermissionGrants/$($oauth2PermissionGrants.value[$i].id)"
  Invoke-RestMethod $endpointuri -Method Delete -Headers $headers
}
```

#### 3.2.3. Check appRoleAssignments [ᵈᵒᶜ](https://learn.microsoft.com/en-us/graph/api/serviceprincipal-list-approleassignments)

```pwsh
$endpointuri = "https://graph.microsoft.com/v1.0/servicePrincipals/$($AgentId.id)/appRoleAssignments"
Invoke-RestMethod $endpointuri -Headers $headers | Tee-Object -Variable appRoleAssignments
$appRoleAssignments.value
```

#### 3.2.4. Remove appRoleAssignments [ᵈᵒᶜ](https://learn.microsoft.com/en-us/graph/api/serviceprincipal-delete-approleassignments)

```pwsh
for ($i = 0; $i -lt $appRoleAssignments.value.Length; $i++) {
  $endpointuri = "https://graph.microsoft.com/v1.0/appRoleAssignments/$($appRoleAssignments.value[$i].id)"
  Invoke-RestMethod $endpointuri -Method Delete -Headers $headers
}
```

## 4. Agent blueprint inheritable permissions [ᵈᵒᶜ](https://learn.microsoft.com/en-us/entra/agent-id/identity-professional/configure-inheritable-permissions-blueprints)

> To be eligible for inheritance, the agent blueprint service principal must already hold OAuth2PermissionGrants for those scopes to the target resource app.

## 4.1. Configure inheritable permissions on agent blueprint [ᵈᵒᶜ](https://learn.microsoft.com/en-us/graph/api/agentidentityblueprint-post-inheritablepermissions)

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
      $PermissionName
    )
  }
}
Invoke-RestMethod $endpointuri -Method Post -Headers $headers -Body $($body | ConvertTo-Json) -ContentType 'application/json'
```

## 4.2. List inheritable permissions [ᵈᵒᶜ](https://learn.microsoft.com/en-us/graph/api/agentidentityblueprint-list-inheritablepermissions)

```pwsh
$endpointuri = "https://graph.microsoft.com/beta/applications/$($AgentIdBp.id)/microsoft.graph.agentIdentityBlueprint/inheritablePermissions"
Invoke-RestMethod $endpointuri -Headers $headers
```

## 5. Assigning permissions used by Entra agent identity

### 5.1. Grant create agent user permission to agent blueprint [ᵈᵒᶜ](https://learn.microsoft.com/en-us/graph/api/serviceprincipal-post-approleassignments)

The agent blueprint requires `AgentIdUser.ReadWrite.IdentityParentedBy` application permission to create agent user with itself as parent

#### 5.1.1. Get Graph API service principal ID and application permission ID

```pwsh
$endpointuri = "https://graph.microsoft.com/v1.0/servicePrincipals(appId='00000003-0000-0000-c000-000000000000')"
Invoke-RestMethod $endpointuri -Headers $headers | Tee-Object -Variable GraphSP
$PermissionName = 'AgentIdUser.ReadWrite.IdentityParentedBy'
$AppRole = $GraphSP.appRoles | ? { $_.value -eq $PermissionName }
```

#### 5.1.2. Grant permission to agent blueprint principal

```pwsh
$endpointuri = "https://graph.microsoft.com/v1.0/servicePrincipals/$($AgentIdBpPrincipal.id)/appRoleAssignments"
$body=@{
  principalId = $AgentIdBpPrincipal.id
  resourceId = $GraphSP.id
  appRoleId = $AppRole.id
}
Invoke-RestMethod $endpointuri -Method Post -Headers $headers -Body $($body | ConvertTo-Json) -ContentType 'application/json'
```

### 5.2. Grant delegated permission to agent identity to authorize agent identity to act on behalf of agent user

Example: agent identity to use `SecurityIncident.Read.All` permission on behalf of agent user

> [!Tip]
>
> The delegated permission can also be granted to the agent blueprint, then have inheritable permissions push down to the agent identity ([section 1.](#1-grant-delegated-permission-to-agent-blueprint))
>
> The assignment via agent blueprint would need `consentType` to be set to `AllPrincipals`

#### 5.2.1. Get Graph API service principal ID

```pwsh
$endpointuri = "https://graph.microsoft.com/v1.0/servicePrincipals(appId='00000003-0000-0000-c000-000000000000')"
Invoke-RestMethod $endpointuri -Headers $headers | Tee-Object -Variable GraphSP
$PermissionName = 'SecurityIncident.Read.All'
```

#### 5.2.2. Grant permission to agent blueprint principal

Notice that `consentType` is set to `Principal` and the authorized principal is scoped only to the agent user (`principalId`: `$AgentUser.id`)

```pwsh
$endpointuri = "https://graph.microsoft.com/v1.0/oauth2PermissionGrants"
$body=@{
  clientId = $AgentId.id
  consentType = 'Principal'
  principalId = $AgentUser.id
  resourceId = $GraphSP.id
  scope = $PermissionName
}
Invoke-RestMethod $endpointuri -Method Post -Headers $headers -Body $($body | ConvertTo-Json) -ContentType 'application/json'
```
