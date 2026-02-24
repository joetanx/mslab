## 1. Note on scopes in authorization code flow

|Scope|Note|
|---|---|
|`.default`|Used to refer generically to a resource service (API) in a request, without identifying specific permissions. If consent is necessary, using `.default` signals that consent should be prompted for all required permissions listed in the application registration (for all APIs in the list).|
|`openid`|Receives a unique identifier for the user in the form of the sub claim<br>Includes `id_token` in the response|
|`offline_access`|Gives the app access to resources on behalf of the user for an extended time<br>Includes `refresh_token` in the response|

## 2. Using PowerShell

Using PowerShell for authorization code flow requires 2 PowerShell windows:
1. Listener session to capture the authorization code (run as administrator required)
2. Sends request to authorization endpoint for the authorization code

Prepare the parameters (for both windows):

```pwsh
$tenant = '<tenant-id>'
$clientid = '<client-id>'
$scope = 'openid offline_access https://graph.microsoft.com/.default'
```

### 2.1. Listener window

Start the listener to listen on `http://localhost` (this should also be the redirect URI configured for the app):

```pwsh
$listener = [System.Net.HttpListener]::new()
$listener.Prefixes.Add('http://localhost/')
$listener.Start()
$context = $listener.GetContext()
$request = $context.Request
$code = $request.QueryString['code']
## respond to browser
$response = $context.Response
$html = "<html><body>Login has completed. This window can be closed.</body></html>"
$buffer = [System.Text.Encoding]::UTF8.GetBytes($html)
$response.ContentLength64 = $buffer.Length
$response.OutputStream.Write($buffer, 0, $buffer.Length)
$response.OutputStream.Close()
$listener.Stop()
```

### 2.2. Authorization endpoint request window

Prepare the authorization URL and use `Start-Process` to open a browser for user sign-in:

```pwsh
$redirect_uri = 'http://localhost'
$state = [guid]::NewGuid().ToString()
$auth_url = "https://login.microsoftonline.com/$tenant/oauth2/v2.0/authorize" +
  "?client_id=$clientid" +
  "&redirect_uri=$([uri]::EscapeDataString($redirect_uri))" +
  "&response_type=code" +
  "&response_mode=query" +
  "&scope=$([uri]::EscapeDataString($scope))" +
  "&state=$State"
Start-Process $auth_url
```

1. Complete the user login in the browser
2. The browser sends the authorization code to the redirect URI, which is captured by the listener window
3. The listener responds to the browser with `Login has completed. This window can be closed.`

### 2.3. Retrieve access token (back in the listener window)

```pwsh
$clientsecret = '<client-secret>'
$token_endpoint = "https://login.microsoftonline.com/$tenant/oauth2/v2.0/token"
$body=@{
  client_id = $clientid
  client_secret = $clientsecret
  scope = $scope
  code = $code
  redirect_uri = 'http://localhost'
  grant_type = 'authorization_code'
}
Invoke-RestMethod $token_endpoint -Method Post -Body $body | Tee-Object -Variable token
$headers = @{ Authorization='Bearer '+$token.access_token }
```

### 2.4. Access target resource with access token

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

## 3. Using Postman

> [!Tip]
>
> Postman handles the authorization code request and redirection in the `Authorization` tab:
> - Generate the `code_verifier` and hashes the it with the specified `code_challenge_method` to create the `code_challenge`
> - Submit authorization code request to the authorization endpoint
> - Submit access token request to the token endpoint with the authorization code retrieved

### 3.1. Getting access token

|Parameter|Value|
|---|---|
|Grant Type|Authorization Code (With PKCE)|
|Callback URL|The exact redirect URI configured in the demo application<br>e.g. `http://localhost`|
|Auth URL|Authorization endpoint<br>`https://login.microsoftonline.com/<tenant>/oauth2/v2.0/authorize`|
|Access Token URL|Token endpoint<br>`https://login.microsoftonline.com/<tenant>/oauth2/v2.0/token`|
|Client ID|The client ID of the demo application|
|Client Secret|The client secret created for the demo application|
|Code Challenge Method|SHA-256 recommended, but plain is also supported|
|Code verifier|Leave blank to automatically generate|
|Scope|The target resource URI suffixed with `.default`<br>e.g. for Log Analytics Workspace `https://management.azure.com/.default`
|State|A randomly generated unique value to prevent CSRF, can just leave blank for testing|
|Client Authentication|**Send as Basic Auth header**: encodes client credentials in Base64 and sends them in the `Authorization` header (`Authorization: Basic base64(client_id:client_secret)`)<br>**Send client credentials in body**: sends client credentials as form parameters in the request body (`client_id=your_client_id&client_secret=your_client_secret`)|

Fill in the parameters and click `Get New Access Token`:

![image](https://github.com/user-attachments/assets/896046d2-316c-49bb-aa4a-91aad7a1b6a8)

#### 3.1.1. Grant user consent

Sign-in to user account:

![image](https://github.com/user-attachments/assets/f22a49b7-c09a-4c92-97b1-2ead84c0b839)

Approve permission to impersonate user:

![image](https://github.com/user-attachments/assets/88fc614d-152b-438c-8b93-80c912e59dc0)

#### 3.1.2. Access token acquired

![image](https://github.com/user-attachments/assets/d6eb0e66-0493-4d91-bff8-20165fe9319f)

> [!Tip]
>
> The authorization flow of request to authorization endpoint, redirect to user sign-in, and request to token endpoint is captured in the Postman console:
>
> ![image](https://github.com/user-attachments/assets/f24a9001-d8ce-4a29-ac56-7e145c214f42)

### 3.2 Request resource with access token

Select _Use Token_ and the _Authorization_ header is automatically added with the access token:

> This is similar to the PowerShell example of:
>
> ```pwsh
> $headers = @{
>   Authorization='Bearer '+$token.access_token
> }
>```

![image](https://github.com/user-attachments/assets/8de4f654-5b7c-447a-95dd-e20696ce6585)

Simply send the request:

![image](https://github.com/user-attachments/assets/72143bcc-f56d-4259-9e1c-8b9e2630d0b9)
