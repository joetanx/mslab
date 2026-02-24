## 1. Entra applications

### 1.1. Entra identity endpoints

|Endpoint|URI prefix|Usage|
|---|---|---|
|Common|`https://login.microsoftonline.com/common/…`|A shared endpoint that supports sign-in for any tenant (multi-tenant apps) and also Microsoft personal accounts. It does not bind to a specific tenant until the user logs in.|
|Tenant-specific|`https://login.microsoftonline.com/<tenant_id>/…`|Bound to a specific tenant (identified by tenant ID or domain name). Only users from that tenant can authenticate.|

|Endpoint|URI suffix|
|---|---|
|OIDC well-known configuration|`…/v2.0/.well-known/openid-configuration`|
|`token_endpoint`|`…/oauth2/v2.0/token`|
|`authorization_endpoint`|`…/oauth2/v2.0/authorize`|
|`device_authorization_endpoint`|`…/oauth2/v2.0/devicecode`|
|`end_session_endpoint`|`…/oauth2/v2.0/logout`|

### 1.2. App registration

App registration is the **application object** which contains configurations like redirect URL, API permissions, credentials (client secrets, certificate, FIC) app roles, etc

![](https://github.com/user-attachments/assets/a8433c2e-7f75-4d3f-94cd-3d82caef638f)

|ID|Purpose|
|---|---|
|Application (client) ID|Unique ID of the **application object** in the Entra directory<br>Also known as AppID or client ID|
|Object ID|Unique ID of **the service principal object** associated with the application|
|Directory (tenant) ID|Unique ID of the Entra tenant|

#### 1.2.1. Application credentials

##### Client secret:

- The client secret is like an API key or client password
- Used in the `client_secret` parameter during authentication
- Good for testing, not recommended for production

![](https://github.com/user-attachments/assets/8b1b0074-6190-4ffc-b22f-13b089e5bab3)

##### Client certificate:

- The client certificate is used to sign the JWT that claims the application's identity
- The signed JWT is used the `client_assertion` parameter during authentication
- When using a certificate chain, upload the certificate that is signing the JWT to the app registration, not the root or intermediate CAs, the public key in the signing certificate is used to verify the JWT signature

![](https://github.com/user-attachments/assets/5c6c604b-9a51-471e-aba2-ab43697a9de3)

##### Federated identity credential (FIC)

- The FIC represents the trust relationship between an external identity provider (IdP) and an app in Microsoft Entra ID
- Several scenarios of [workload identity federation](https://learn.microsoft.com/en-us/entra/workload-id/workload-identity-federation#supported-scenarios) are supported, includign the managed identity example below
- Note: it is not possible to use another application in Entra as FIC:
  - `AADSTS700222: AAD-issued tokens may not be used for federated identity flows.`

![](https://github.com/user-attachments/assets/469ce69d-7688-4f8e-a38b-ba8b7453991a)

#### 1.2.2. API permissions

Application and delegated permissions

Entra permission reference: https://learn.microsoft.com/en-us/graph/permissions-reference

#### 1.2.3. Authentication

##### Redirect URI

##### Public client flow

### 1.3. Enterprise application

Enterprise application is the **service principal object** (i.e. service account or machine identity) created from the _application object_

![](https://github.com/user-attachments/assets/7c0dc378-930a-470f-a569-18348dc373ff)

#### 1.3.1. Permissions

#### 1.3.2. Group membership

#### 1.3.3. Azure and Defender RBAC

## 2. Authentication Flows

### 2.1. Client credential

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

### 2.2. Authorization code

#### 2.2.1. without Proof Key for Code Exchange (PKCE)

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

#### 2.2.2. with Proof Key for Code Exchange (PKCE)

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

### 2.3. On-behalf-of

```mermaid
sequenceDiagram
  actor A as User
  participant B as Application<br>(client)
  participant C as Authorization<br>endpoint
  participant D as Token<br>endpoint
  participant E as Application<br>(middle-tier)
  participant F as Resource
  rect rgb(32, 32, 32)
    note over A,D:Authorization code flow
    A->>B:Initiate login
    B->>C:Authorization<br>code request
    C->>A:Redirect to authorization page
    A->>C:Authenticate and consent
    C->>B:Authorization code
    B->>D:Request token (client) with authorization code
    D->>B:Token (client)
  end
  rect rgb(32, 32, 32)
    note over B,E:On-behalf-of flow
    B->>E:Send token (client) to middle-tier app
    E->>D:Request token (resource)<br>with token (client)
    E->>B:Return token (resource)
  end
  E->>F:Request resource<br>with token (resource)
  F->>E:Response
```
