## 1. Setup Agent 365 CLI

The [Agent 365 CLI](https://learn.microsoft.com/en-us/microsoft-agent-365/developer/agent-365-cli) is a cross-platform tool that works on Windows, Linux and macOS with .NET 8.0 or later

### 1.1. Install .NET, Azure CLI and PowerShell 7+ (Windows example)

```cmd
winget install Microsoft.DotNet.SDK.10 Microsoft.AzureCLI Microsoft.PowerShell
```

![](https://github.com/user-attachments/assets/daaa11e0-bc29-4d50-b098-abfa90650b83)

![](https://github.com/user-attachments/assets/132ac0e6-3ce8-4bf9-9704-2cdafd83567d)

### 1.2. Install Agent 365 CLI

```cmd
dotnet tool install --global Microsoft.Agents.A365.DevTools.Cli
```
![](https://github.com/user-attachments/assets/a9a7b3b0-3da7-4933-9863-29d1b594ce22)

![](https://github.com/user-attachments/assets/ac7d2118-c4a9-4d04-bf8f-c13632a36733)

## 2. Setup Azure CLI

Agent 365 CLI automatically detects the tenant ID from Azure CLI

> `a365 setup` commands fail without Azure CLI login
>
> ![](https://github.com/user-attachments/assets/2f72184b-f222-4f62-927b-e7128dd73c94)
>
> ![](https://github.com/user-attachments/assets/4c8aba57-9833-4c64-8fd9-ab773270b8ab)

Login with `az login`:

![](https://github.com/user-attachments/assets/bda42fd5-c151-433c-9cdf-6f064a07452d)

![](https://github.com/user-attachments/assets/31010c6d-6891-49f4-bc91-8a45bf3034b7)

![](https://github.com/user-attachments/assets/df51829e-a1f9-4bf0-9eb6-c79a3b4c3c9e)

## 3. Setup `Agent 365 CLI` client app

### 3.1. About the `Agent 365 CLI` client app

The CLI looks up the client app by the well-known display name `Agent 365 CLI` automatically

If this client app doesn't exist in the tenant, it prompts for the [custom client app](https://learn.microsoft.com/en-us/microsoft-agent-365/developer/custom-client-app-registration) to be used:

![](https://github.com/user-attachments/assets/914ee2ba-5dd3-42ed-b0ef-09cdd2123dda)

[Register](https://learn.microsoft.com/en-us/microsoft-agent-365/developer/custom-client-app-registration#1-register-application) the `Agent 365 CLI` client app and run `a365 setup requirements`

`a365 setup requirements` prepares the client app with the following:

![](https://github.com/user-attachments/assets/678c731c-2058-42ff-b96a-1b8f92b5faa0)

#### 3.1.1. Permissions

The `Agent 365 CLI` or _custom client app registration_ requires seven **delegated permissions**:

|Permission|Purpose|
|---|---|
|`AgentIdentityBlueprint.ReadWrite.All`|Blueprint creation, client secret management, inheritable permissions, federated identity credentials, and deletion|
|`AgentIdentityBlueprintPrincipal.Create`|Create the Agent Blueprint service principal|
|`AgentIdentity.Read.All`|Idempotency check and agent identity service principal lookup|
|`AgentIdentity.DeleteRestore.All`|Delete agent identity service principals during cleanup|
|`AgentRegistration.ReadWrite.All`|Read and write all agent registrations|
|`Application.Read.All`|Service principal lookup by app ID (narrower replacement for Directory.Read.All)|
|`User.Read`|Read signed-in user profile for blueprint owner and sponsor assignment|

![](https://github.com/user-attachments/assets/01097967-2bbc-43e0-b629-1bbd90b72b35)

#### 3.1.2. Redirect URIs

The CLI requires three redirect URIs in total:

|URI|Purpose|
|---|---|
|`http://localhost:8400/`|Microsoft Authentication Library (MSAL) interactive browser authentication|
|`http://localhost`|Microsoft Graph PowerShell SDK Connect-MgGraph|
|`ms-appx-web://Microsoft.AAD.BrokerPlugin/{client-id}`|Using Web Account Manager (WAM)|

> `AADSTS500113: No reply address is registered for the application.` error occurs if the redirect URIs are not configured
>
> ![](https://github.com/user-attachments/assets/39cfb949-25ea-43f8-9535-865a7f82f6d6)

#### 3.1.3. Public client flows

`Allow public client flows` must be enabled

### 3.2. Running `a365 setup requirements`

> [!Important]
>
> Client app configuration requires Global Administrator:
> 1. Run the CLI as a Global Administrator
> 2. Get the consent URL from the CLI and approve using Global Administrator

## 4. Register agent with Agent 365 CLI

To setup an agent in Agent 365, run `a365 setup all --agent-name <agent-name>`

### 4.1. Agent 365 CLI authentication

Agent 365 CLI automatically detects the tenant ID from Azure CLI

> [!Note]
>
> There was a `a365 config init` command to initialize a365 configuration file, but the `config` option appears to have been [removed](https://github.com/microsoft/Agent365-devTools/issues/370#issuecomment-4331725685)

![](https://github.com/user-attachments/assets/2bb1eacc-f7a1-4708-b5ad-6fab30816507)

Alternatively, use the `--tenant-id <tenant-id>` to skip auto detection

Running a365 in Windows automatically opens the Windows Account Manager (other platforms open browser)

![](https://github.com/user-attachments/assets/ccacd922-65f4-44c6-b9c5-f27e47a5337a)

![](https://github.com/user-attachments/assets/df51829e-a1f9-4bf0-9eb6-c79a3b4c3c9e)

Token cache location: `%LocalAppData%\Microsoft.Agents.A365.DevTools.Cli\`:
- `msal-token-cache`: DPAPI encypted cached token generated by MSAL
- `auth-token.json`: derived from `msal-token-cache`, used by Agent 365 CLI

![](https://github.com/user-attachments/assets/bfe2c7c8-dada-4a28-99cb-15d484964ac9)

### 4.2. Running agent setup

![](https://github.com/user-attachments/assets/e527a483-0f4b-48af-9958-f9097c52fba6)

![](https://github.com/user-attachments/assets/0e80fd2b-9bc4-4438-be74-d0d9527912c3)

```cmd

```

```cmd

```
