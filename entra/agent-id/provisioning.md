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

### 0.3. Get user id for sponsor and owner [ᵈᵒᶜ](https://learn.microsoft.com/en-us/graph/api/user-list)

Example using user UPN `admin@MngEnvMCAP398230.onmicrosoft.com`:

```pwsh
$userPN = 'admin@MngEnvMCAP398230.onmicrosoft.com'
$query = "userPrincipalName eq '$userPN'"
$endpointuri = 'https://graph.microsoft.com/v1.0/users?$filter='+$query
Invoke-RestMethod $endpointuri -Headers $headers | Tee-Object -Variable managerUser
```

### 0.4. Staging names

```pwsh
$AgentIdBpName = 'Agent IdBp01'
$AgentIdName = 'Agent IdBp01 Id01'
$AgentUserName = 'Agent IdBp01 Id01 User01'
$AgentUserAlias = 'agent-idbp01-id01-user01'
$tenantDomain = 'MngEnvMCAP398230.onmicrosoft.com'
```

## 1. Agent identity blueprint

### 1.1. Create agent identity blueprint [ᵈᵒᶜ](https://learn.microsoft.com/en-us/graph/api/agentidentityblueprint-post)

```pwsh
$endpointuri = 'https://graph.microsoft.com/beta/applications/microsoft.graph.agentIdentityBlueprint'
$body=@{
  '@odata.type' = 'Microsoft.Graph.AgentIdentityBlueprint'
  displayName = $AgentIdBpName
  'sponsors@odata.bind' = @( "https://graph.microsoft.com/v1.0/users/$($managerUser.value.id)" )
  'owners@odata.bind' = @( "https://graph.microsoft.com/v1.0/users/$($managerUser.value.id)" )
}
Invoke-RestMethod $endpointuri -Method Post -Headers $headers -Body $($body | ConvertTo-Json) -ContentType 'application/json' | Tee-Object -Variable AgentIdBp
```

### 1.2. Create agent identity blueprint principal [ᵈᵒᶜ](https://learn.microsoft.com/en-us/graph/api/agentidentityblueprintprincipal-post)

```pwsh
$endpointuri = 'https://graph.microsoft.com/beta/serviceprincipals/graph.agentIdentityBlueprintPrincipal'
$body=@{
  appId = $AgentIdBp.id
}
Invoke-RestMethod $endpointuri -Method Post -Headers $headers -Body $($body | ConvertTo-Json) -ContentType 'application/json' | Tee-Object -Variable AgentIdBpPrincipal
```

### 1.3. Add agent identity blueprint credentials

#### 1.3.A. Client secret

##### 1.3.A.1. Add password [ᵈᵒᶜ](https://learn.microsoft.com/en-us/graph/api/agentidentityblueprint-addpassword)

```pwsh
$endpointuri = "https://graph.microsoft.com/beta/applications/$($AgentIdBp.id)/microsoft.graph.agentIdentityBlueprint/addPassword"
$body=@{
  passwordCredential = @{
    displayName = ''
  }
}
Invoke-RestMethod $endpointuri -Method Post -Headers $headers -Body $($body | ConvertTo-Json) -ContentType 'application/json' | Tee-Object -Variable AgentIdBpPw
```

##### 1.3.A.2. Delete password [ᵈᵒᶜ](https://learn.microsoft.com/en-us/graph/api/agentidentityblueprint-removepassword)

```pwsh
$endpointuri = "https://graph.microsoft.com/beta/applications/$($AgentIdBp.id)/microsoft.graph.agentIdentityBlueprint/removePassword"
$body=@{ keyId = $AgentIdBpPw.keyId }
Invoke-RestMethod $endpointuri -Method Post -Headers $headers -Body $($body | ConvertTo-Json) -ContentType 'application/json'
```

#### 1.3.B. Federated identity credentials (FIC)

##### 1.3.B.1. Get managed identity using list servicePrincipals [ᵈᵒᶜ](https://learn.microsoft.com/en-us/graph/api/serviceprincipal-list)

Example using Azure VM with name `delta-vm-winsvr`:

```pwsh
$miName = 'delta-vm-winsvr'
$query = "servicePrincipalType eq 'ManagedIdentity' and displayName eq '$miName'"
$endpointuri = 'https://graph.microsoft.com/v1.0/servicePrincipals?$filter='+$query
Invoke-RestMethod $endpointuri -Headers $headers | Tee-Object -Variable managedIdentity
```

##### 1.3.B.2. Add FIC [ᵈᵒᶜ](https://learn.microsoft.com/en-us/graph/api/federatedidentitycredential-post)

```pwsh
$endpointuri = "https://graph.microsoft.com/beta/applications/$($AgentIdBp.id)/microsoft.graph.agentIdentityBlueprint/federatedIdentityCredentials"
$body=@{
  name = 'azure-vm-mi-fic'
  issuer = "https://login.microsoftonline.com/$tenant/v2.0"
  subject = $managedIdentity.value.id
  audiences = @( 'api://AzureADTokenExchange' )
}
Invoke-RestMethod $endpointuri -Method Post -Headers $headers -Body $($body | ConvertTo-Json) -ContentType 'application/json'
```

##### 1.3.B.3. Delete FIC [ᵈᵒᶜ](https://learn.microsoft.com/en-us/graph/api/federatedidentitycredential-delete)

```pwsh
$endpointuri = "https://graph.microsoft.com/beta/applications/$($AgentIdBp.id)/microsoft.graph.agentIdentityBlueprint/federatedIdentityCredentials/$($body.name)"
Invoke-RestMethod $endpointuri -Method Delete -Headers $headers
```

### 1.4. Grant agent identity blueprint permission to create agent user [ᵈᵒᶜ](https://learn.microsoft.com/en-us/graph/api/serviceprincipal-post-approleassignments)

```pwsh
$endpointuri = "https://graph.microsoft.com/v1.0/servicePrincipals(appId='00000003-0000-0000-c000-000000000000')"
Invoke-RestMethod $endpointuri -Headers $headers | Tee-Object -Variable GraphSP
$role = 'AgentIdUser.ReadWrite.IdentityParentedBy'
$AppRole = $GraphSP.appRoles | ? { $_.value -eq $role }
$endpointuri = "https://graph.microsoft.com/v1.0/servicePrincipals/$($AgentIdBpPrincipal.id)/appRoleAssignments"
$body=@{
  principalId = $AgentIdBpPrincipal.id
  resourceId = $GraphSP.id
  appRoleId = $AppRole.id
}
Invoke-RestMethod $endpointuri -Method Post -Headers $headers -Body $($body | ConvertTo-Json) -ContentType 'application/json'
```

## 2. Get access token for agent identity blueprint

### 2.1.A. Using client secret

```pwsh
$body=@{
  client_id = $AgentIdBp.id
  client_secret = $AgentIdBpPw.secretText
  grant_type = 'client_credentials'
  scope = 'https://graph.microsoft.com/.default'
}
Invoke-RestMethod $token_endpoint -Method Post -Body $body | Tee-Object -Variable tokenAgentIdBp
$headersAgentIdBp = @{ Authorization='Bearer '+$tokenAgentIdBp.access_token }
```

### 2.1.B. Using FIC (e.g. using Azure VM to get managed identity token)

#### 2.1.B.1. Get exchange token for MI [ᵈᵒᶜ](https://learn.microsoft.com/en-us/entra/identity/managed-identities-azure-resources/how-to-use-vm-token)

```pwsh
$endpointuri = 'http://169.254.169.254/metadata/identity/oauth2/token?api-version=2018-02-01&resource=api://AzureADTokenExchange'
Invoke-RestMethod $endpointuri -Headers @{Metadata="true"} | Tee-Object -Variable tokenMI
$tokenMI.access_token
```

#### 2.1.B.2. Exchange MI token for agent identity blueprint token [ᵈᵒᶜ](https://learn.microsoft.com/en-us/entra/agent-id/identity-platform/create-delete-agent-identities#get-an-access-token-using-agent-identity-blueprint)

```pwsh
$body=@{
  client_id = $AgentIdBp.id
  client_assertion_type = 'urn:ietf:params:oauth:client-assertion-type:jwt-bearer'
  client_assertion = $tokenMI.access_token
  grant_type = 'client_credentials'
  scope = 'https://graph.microsoft.com/.default'
}
Invoke-RestMethod $token_endpoint -Method Post -Body $body | Tee-Object -Variable tokenAgentIdBp
$headersAgentIdBp = @{ Authorization='Bearer '+$tokenAgentIdBp.access_token }
```

## 3. Create agent identity [ᵈᵒᶜ](https://learn.microsoft.com/en-us/graph/api/agentidentity-post)

```pwsh
$endpointuri = 'https://graph.microsoft.com/beta/servicePrincipals/microsoft.graph.agentIdentity'
$body=@{
  displayName = $AgentIdName
  agentIdentityBlueprintId = $AgentIdBp.id
  'sponsors@odata.bind' = @( "https://graph.microsoft.com/v1.0/users/$($managerUser.value.id)" )
}
Invoke-RestMethod $endpointuri -Method Post -Headers $headersAgentIdBp -Body $($body | ConvertTo-Json) -ContentType 'application/json' | Tee-Object -Variable AgentId
```

## 4. Create agent user [ᵈᵒᶜ](https://learn.microsoft.com/en-us/graph/api/agentuser-post)

```pwsh
$endpointuri = 'https://graph.microsoft.com/beta/users/microsoft.graph.agentUser'
$body=@{
  accountEnabled = 'true'
  displayName = $AgentUserName
  mailNickname = $AgentUserAlias
  userPrincipalName = $AgentUserAlias+'@'+$tenantDomain
  identityParentId = $AgentId.id
}
Invoke-RestMethod $endpointuri -Method Post -Headers $headersAgentIdBp -Body $($body | ConvertTo-Json) -ContentType 'application/json' | Tee-Object -Variable AgentUser
```

## 5. Misc troubleshooing

### 5.1. Get things

#### 5.1.1. Get agentIdentityBlueprint [ᵈᵒᶜ](https://learn.microsoft.com/en-us/graph/api/agentidentityblueprint-list)

```pwsh
$query = "displayName eq '$AgentIdBpName'"
$endpointuri = 'https://graph.microsoft.com/beta/applications/microsoft.graph.agentIdentityBlueprint?$filter='+$query
$AgentIdBp = (Invoke-RestMethod $endpointuri -Headers $headers).value
```

#### 5.1.2. Get agentIdentityBlueprintPrincipal [ᵈᵒᶜ](https://learn.microsoft.com/en-us/graph/api/agentidentityblueprintprincipal-list)

```pwsh
$query = "displayName eq '$AgentIdBpName'"
$endpointuri = 'https://graph.microsoft.com/beta/servicePrincipals/microsoft.graph.agentIdentityBlueprintPrincipal?$filter='+$query
$AgentIdBpPrincipal = (Invoke-RestMethod $endpointuri -Headers $headers).value
```

#### 5.1.3. Get agentIdentity [ᵈᵒᶜ](https://learn.microsoft.com/en-us/graph/api/agentidentity-list)

```pwsh
$query = "displayName eq '$AgentIdName'"
$endpointuri = 'https://graph.microsoft.com/beta/servicePrincipals/microsoft.graph.agentIdentity?$filter='+$query
$AgentId = (Invoke-RestMethod $endpointuri -Headers $headers).value
```

#### 5.1.4. Get agentUser [ᵈᵒᶜ](https://learn.microsoft.com/en-us/graph/api/agentuser-list)

```pwsh
$query = "displayName eq '$AgentUserName'"
$endpointuri = 'https://graph.microsoft.com/beta/users/microsoft.graph.agentUser?$filter='+$query
$AgentUser = (Invoke-RestMethod $endpointuri -Headers $headers).value
```

### 5.2. Delete things

#### 5.2.1. Delete agentIdentityBlueprint [ᵈᵒᶜ](https://learn.microsoft.com/en-us/graph/api/agentidentityblueprint-delete)

> [!Tip]
>
> Agent blueprint principal is deleted when agent blueprint is deleted

```pwsh
$endpointuri = "https://graph.microsoft.com/beta/applications/$($AgentIdBp.id)/microsoft.graph.agentIdentityBlueprint"
Invoke-RestMethod $endpointuri -Method Delete -Headers $headers
```

#### 5.2.2. Delete agentIdentity [ᵈᵒᶜ](https://learn.microsoft.com/en-us/graph/api/serviceprincipal-delete?view=graph-rest-beta)

> [!Tip]
>
> Oddly, the agent identity isn't deleted when the agent bluepint is deleted
> 
> There also doesn't seem to be a docs for deleting agent identity, but deleting service prinicpal works

```pwsh
$endpointuri = "https://graph.microsoft.com/beta/serviceprincipals/$($AgentId.id)"
Invoke-RestMethod $endpointuri -Method Delete -Headers $headers
```

#### 5.2.3. Delete agentUser [ᵈᵒᶜ](https://learn.microsoft.com/en-us/graph/api/agentuser-delete)

```pwsh
$endpointuri = "https://graph.microsoft.com/beta/users/microsoft.graph.agentUser/$($AgentUser.id)"
Invoke-RestMethod $endpointuri -Method Delete -Headers $headersAgentIdBp
```

