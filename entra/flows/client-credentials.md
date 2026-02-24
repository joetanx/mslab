> [!Tip]
>
> Example flow with PowerShell
> 
> There is a write-up about using PowerShell and cURL for API requests [here](https://github.com/joetanx/setup/blob/main/web-request-notes.md)

## 1. Client secret

Parameters required to [request access token with a shared secret](https://learn.microsoft.com/en-us/entra/identity-platform/v2-oauth2-client-creds-grant-flow#first-case-access-token-request-with-a-shared-secret):

|Parameter|Value|
|---|---|
|`tenant`|The Entra identity tenant ID|
|`client_id`|The client ID of the demo application|
|`client_secret`|The client secret created for the demo application|
|`grant_type`|`client_credentials`|
|`scope`|The target resource URI suffixed with `.default`<br>e.g. for Log Analytics Workspace `https://management.azure.com/.default`<br>e.g. for Graph API: `https://graph.microsoft.com/.default`|

### 1.1. Retrieve access token from token endpoint

Prepare the parameters:

```pwsh
$tenant = '<tenant-id>'
$clientid = '<client-id>'
$clientsecret = '<client-secret>'
$token_endpoint = "https://login.microsoftonline.com/$tenant/oauth2/v2.0/token"
$body=@{
  client_id = $clientid
  client_secret = $clientsecret
  grant_type = 'client_credentials'
  scope = 'https://graph.microsoft.com/.default'
}
```

Request for access token:

> [!Tip]
>
> The `Tee-Object` command in PowerShell works similar to `tee` in Linux
>
> it sends the output of the previous command to both the console and the specified variable

```pwsh
Invoke-RestMethod $token_endpoint -Method Post -Body $body | Tee-Object -Variable token
```

Example output:

```pwsh
token_type expires_in ext_expires_in access_token
---------- ---------- -------------- ------------
Bearer           3599           3599 <access-token-jwt>
```

## 2. Client certificate 

Parameters required to [request access token with a certificate](https://learn.microsoft.com/en-us/entra/identity-platform/v2-oauth2-client-creds-grant-flow#second-case-access-token-request-with-a-certificate):

|Parameter|Value|
|---|---|
|`tenant`|The Entra identity tenant ID|
|`client_id`|The client ID of the demo application|
|`client_assertion_type`|`urn:ietf:params:oauth:client-assertion-type:jwt-bearer`|
|`client_assertion`|An assertion (JWT) signed with the client certificate|
|`grant_type`|`client_credentials`|
|`scope`|The target resource URI suffixed with `.default`<br>e.g. for Log Analytics Workspace `https://management.azure.com/.default`<br>e.g. for Graph API: `https://graph.microsoft.com/.default`|

### 2.1. Setup client certificate

> [!Important]
>
> Entra supports only RSA certificates for application authentication
>
> Using ECDSA or other certificates leads to _unsupported asymmetric signing algorithm_ error
>
> ```
> Invoke-RestMethod : {"error":"invalid_client","error_description":"AADSTS700027: Invalid JWT token. Unsupported asymmetric signing algorithm.
> ```

Create self-signed certificate:

```pwsh
New-SelfSignedCertificate -Subject 'O=vx Lab, CN=Self-signed App Certificate'-CertStoreLocation cert:\CurrentUser\My
```

Export certificate:

> [!Note]
>
> The [Export-Certificate](https://learn.microsoft.com/en-us/powershell/module/pki/export-certificate#-type) command in PowerShell exports the certificate as DER encoded
>
> Use the method below to export the certificate as Base-64 encoded

```pwsh
$cert = Get-ChildItem -Path cert:\CurrentUser\My | Where-Object { $_.Subject -match 'Self-signed'}
$pem = "-----BEGIN PUBLIC KEY-----`n" +
 [Convert]::ToBase64String($cert.RawData, 'InsertLineBreaks') +
 "`n-----END PUBLIC KEY-----"
$pem | Out-File -FilePath app.cer -Encoding ascii
```

Upload the certificate to the app registration:

![](https://github.com/user-attachments/assets/c9c3bf88-9bd0-4d3c-a85e-9f1e6caedb50)

### 2.2. Retrieve access token from token endpoint

#### 2.2.1. Prepare the assertion JWT

Details on the assertion format required by Entra: https://learn.microsoft.com/en-us/entra/identity-platform/certificate-credentials

Prepare JWT header and payload as PowerShell object:

```pwsh
$jwtHeader = @{
  alg = 'PS256'
  typ = 'JWT'
  'x5t#S256' = [System.Convert]::ToBase64String([System.Security.Cryptography.SHA256]::Create().ComputeHash($cert.RawData)).Replace('+', '-').Replace('/', '_').TrimEnd('=')
}
$jwtPayload = @{
  aud = "https://login.microsoftonline.com/$tenant/oauth2/v2.0/token"
  iss = $clientid
  sub = $clientid
  jti = [guid]::NewGuid().ToString()
  exp = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds() + 600
  nbf = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
}
```

Convert the JWT header and payload objects to JSON:

```pwsh
$jwtHeaderJson = ConvertTo-Json $jwtHeader -Compress
$jwtPayloadJson = ConvertTo-Json $jwtPayload -Compress
```

Prepare the JWT header and payload JSONs in Base64url-encoded format

> [!Note]
>
> Base-64 encoding can lead to `+`, `/` and `=` characters
>
> The `.Replace()` methods replaces `+` with `-`, `/` with `_`, and omits padding `=` to modify the character set to be safe for use in URLs

```pwsh
$jwtHeaderBase64 = [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes($jwtHeaderJson)).Replace('+', '-').Replace('/', '_').TrimEnd('=')
$jwtPayloadBase64 = [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes($jwtPayloadJson)).Replace('+', '-').Replace('/', '_').TrimEnd('=')
```

Read the certificate private key with `GetRSAPrivateKey($cert)`:

```pwsh
$rsaKey = [System.Security.Cryptography.X509Certificates.RSACertificateExtensions]::GetRSAPrivateKey($cert)
```

Sign the JWT:

> [!Note]
> 
> JWT signing algorithms:
> - RS256 (RSA Signature with SHA-256) uses PKCS#1 padding (`[System.Security.Cryptography.RSASignaturePadding]::Pkcs1`)
> - PS256 (RSASSA-PSS with SHA-256) uses PSS (Probabilistic) pading (`[System.Security.Cryptography.RSASignaturePadding]::Pss`)

> [!Note]
>
> Signing with ECDSA - does not work for Entra, for reference only
> 
> ```pwsh
> $ecKey = [System.Security.Cryptography.X509Certificates.ECDsaCertificateExtensions]::GetECDsaPrivateKey($cert)
> $jwtSignature = $ecKey.SignData([System.Text.Encoding]::UTF8.GetBytes($jwtUnsigned), [System.Security.Cryptography.HashAlgorithmName]::SHA256)
> ```

```pwsh
$jwtSignature = $rsaKey.SignData([System.Text.Encoding]::UTF8.GetBytes($jwtUnsigned), [System.Security.Cryptography.HashAlgorithmName]::SHA256, [System.Security.Cryptography.RSASignaturePadding]::Pss)
```

#### 2.2.2. Request for access token with the signed JWT

The parameters required to request for access token are finally complete with the `client_assertion`:

```pwsh
$body=@{
  client_id = $clientid
  client_assertion_type = $client_assertion_type
  client_assertion = $client_assertion
  grant_type = 'client_credentials'
  scope = 'https://graph.microsoft.com/.default'
}
```

> [!Tip]
>
> The `Tee-Object` command in PowerShell works similar to `tee` in Linux
>
> it sends the output of the previous command to both the console and the specified variable

```pwsh
Invoke-RestMethod $token_endpoint -Method Post -Body $body | Tee-Object -Variable token
```

Example output:

```pwsh
token_type expires_in ext_expires_in access_token
---------- ---------- -------------- ------------
Bearer           3599           3599 <access-token-jwt>
```

## 3. Access target resource with access token

The access token is sent in the `Authorization` header in the format of: `Bearer: <access-token-jwt>`

Prepare the request header:

```pwsh
$headers = @{
  Authorization='Bearer '+$token.access_token
}
```

Prepare the target resource URL:

```pwsh
$endpointuri='https://graph.microsoft.com/v1.0/security/incidents'
```

Send the request:

```pwsh
Invoke-RestMethod $endpointuri -Headers $headers | Tee-Object -Variable incidents
```

Example output (Microsoft Graph Security API):

```pwsh
PS C:\Users\Administrator> $incidents.value[0]


id                 : 1791
tenantId           : 323626f5-1bfe-48cd-8902-ddfdfd44e1ce
status             : active
incidentWebUrl     : https://security.microsoft.com/incident2/1791/overview?tid=323626f5-1bfe-48cd-8902-ddfdfd44e1ce
redirectIncidentId :
displayName        : 'ReverseShell' malware was detected (Agentless)
createdDateTime    : 2026-02-18T04:02:35.22Z
lastUpdateDateTime : 2026-02-18T04:02:35.3733333Z
assignedTo         :
classification     : unknown
determination      : unknown
severity           : high
customTags         : {}
systemTags         : {}
description        :
lastModifiedBy     : Microsoft 365 Defender-IncidentCreation
resolvingComment   :
summary            :
priorityScore      : 19
comments           : {}
```
