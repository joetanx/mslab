## 1. Open ID with Entra identity

### 1.1. Endpoints for Entra identity

Entra identity endpoints are scoped by `tenant ID` and the details are listed in the OIDC well-known configuration:

```
https://login.microsoftonline.com/$tenant/v2.0/.well-known/openid-configuration
```

The OAuth2 endpoints are in the format:

```pwsh
https://login.microsoftonline.com/$tenant/oauth2/v2.0/{token,authorize,devicecode,logout}
```

An endpoint can be referenced by the OIDC well-known configuration, e.g.:

```pwsh
$openid = Invoke-RestMethod https://login.microsoftonline.com/$tenant/v2.0/.well-known/openid-configuration
$token = Invoke-RestMethod $openid.token_endpoint -Method Post -Body $body
```

Or simply using the URI directly, since the endpoints format would likely never change:

|Endpoint|URI|
|---|---|
|`token_endpoint`|`https://login.microsoftonline.com/$tenant/oauth2/v2.0/token`|
|`authorization_endpoint`|`https://login.microsoftonline.com/$tenant/oauth2/v2.0/authorize`|
|`device_authorization_endpoint`|`https://login.microsoftonline.com/$tenant/oauth2/v2.0/devicecode`|
|`end_session_endpoint`|`https://login.microsoftonline.com/$tenant/oauth2/v2.0/logout`|

### 1.2. Setup Entra Identity for demo application

#### 1.2.1. Create app registration

> [!Note]
>
> Take note of the `Application (client) ID` and `Directory (tenant) ID`; these will be required later.

![image](https://github.com/user-attachments/assets/27f1a9eb-ec49-441a-b640-14eeca068906)

#### 1.2.2. Create client secret

> [!Important]
>
> The client secret is displayed **only once**, copy and store it securely right after creation
>
> There is no way to retrieve the client secret if it's lost, it will need to be deleted and create a new one

![image](https://github.com/user-attachments/assets/ff2b9cbe-7e95-4941-acf3-715478de4eb7)

## 2. Client Credentials Flow

```mermaid
sequenceDiagram
  participant B as Application
  participant C as Authorization<br>endpoint
  note over C:Not used in client<br>credentials flow
  participant D as Token<br>endpoint
  participant E as Resource
  B->>D:Request token with application credentials
  D->>D:Verify application<br>credentials
  D->>B:Access token
  B->>E:Request resource with access token
  E->>B:Response
```

Ref: https://learn.microsoft.com/en-us/entra/identity-platform/v2-oauth2-client-creds-grant-flow

Application credentials can be:
1. `client_secret`: symmetric shared secret
2. `client_assertion`: a JWT signed by the client certificate that is registered as credentials for the application; the token endpoint uses the registered client certificate to validate the JWT

## 3. Authorization Code Flow

```mermaid
sequenceDiagram
  actor A as User
  participant B as Application
  participant C as Authorization<br>endpoint
  participant D as Token<br>endpoint
  participant E as Resource
  A->>B:Initiate login
  B->>C:Authorization<br>code request
  C->>A:Redirect to authorization page
  A->>C:Authenticate and consent
  C->>B:Authorization code
  B->>D:Request token with authorization code
  D->>B:Access token and refresh token
  B->>E:Request resource with access token
  E->>B:Response
  loop Refresh access token
    B->>D:Request new access token with<br>refresh token before expiry
    D->>B:New access token and new refresh token
    B->>E:Request resource with new access token
  end
```

Ref: https://learn.microsoft.com/en-us/entra/identity-platform/v2-oauth2-auth-code-flow

> [!Note]
>
> PKCE (below) is recommended for all application types, both public and confidential clients, and required by the Microsoft identity platform for single page apps using the authorization code flow.

> [!Note]
>
> Application credentials are also required by the Microsoft identity platform for confidential web apps

## 4. Authorization Code Flow with Proof Key for Code Exchange (PKCE)

```mermaid
sequenceDiagram
  actor A as User
  participant B as Application
  participant C as Authorization<br>endpoint
  participant D as Token<br>endpoint
  participant E as Resource
  A->>B:Initiate login
  B->>B:Generate code_verifier<br>and code_challenge
  note over B: code_challenge is a hash of code_verifier<br>using code_challenge_method
  B->>C:Authorization code request<br>+ code_challenge<br>+ code_challenge_method
  note over C,D:Stores code_challenge<br>+ code_challenge_method
  C->>A:Redirect to authorization page
  A->>C:Authenticate and consent
  C->>B:Authorization code
  B->>D:Request token with authorization code and code_verifier
  D->>D:Hashes code_verfier with code_challenge_method<br>and validate against code_challenge
  D->>B:Access token and refresh token
  B->>E:Request resource with access token
  E->>B:Response
  loop Refresh access token
    B->>D:Request new access token with<br>refresh token before expiry
    D->>B:New access token and new refresh token
    B->>E:Request resource with new access token
  end
```

Ref: https://learn.microsoft.com/en-us/entra/identity-platform/v2-oauth2-auth-code-flow

> [!Note]
>
> Application credentials are also required by the Microsoft identity platform for confidential web apps
