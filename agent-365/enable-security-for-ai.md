## 1. Settings page

Defender portal → Settings → Security for AI

![](https://github.com/user-attachments/assets/c26563b2-bea9-4c43-b8a0-6d2ce41cbdaa)

### 1.1. Without Agent 365 license

|Security for AI agents: not enabled|Security for AI agents: enabled|
|---|---|
|![](https://github.com/user-attachments/assets/71a786ac-635e-40e7-b4e8-c7ccf7b40d2d)|![](https://github.com/user-attachments/assets/3c51fb94-2dad-47bf-a706-c21644cae6f0)|

### 1.2. With Agent 365 license

|Security for AI agents: not enabled|Security for AI agents: enabled|
|---|---|
|![](https://github.com/user-attachments/assets/4f72df25-457c-4142-ae79-930222934333)|![](https://github.com/user-attachments/assets/5d376646-bdb7-436c-ab00-1fbaec018865)|

## 2. Connect Agent 365

 AI security posture is automatically connected for Agent 365

For AI real-time protection & investigation, simply click `Connect`, select `Audit` or `Block`, then hit `Save`

![](https://github.com/user-attachments/assets/bc9fb562-9f8d-4502-a250-d0d168e32806)

## 3. Connect Copilot Studio

### 3.1. AI security posture

![](https://github.com/user-attachments/assets/0fb8487b-1336-4d85-96e4-26c306577835)

Open Power Platform Admin Center (click on link or go to https://admin.powerplatform.microsoft.com/security/threatdetection):

![](https://github.com/user-attachments/assets/c2bdcd3c-39f6-4352-b691-82fc52d4c9be)

Toggle: `Enable Microsoft Defender - For all Copilot Studio Agents in tenant`

![](https://github.com/user-attachments/assets/bedd682c-2ca7-462a-9b9d-851a922de46e)

> [!Note]
>
> Connected status may take up to 1 hour after admin setup.

### 3.2. AI real-time protection & investigation

#### [Create App Registration](https://learn.microsoft.com/en-us/microsoft-copilot-studio/external-security-provider#step-1-configure-microsoft-entra-application)

![](https://github.com/user-attachments/assets/d4f6f37a-1a69-40e3-9ccf-9fdbe8d38932)

#### [Configure Federated Identity Credentials (FIC)](https://learn.microsoft.com/en-us/microsoft-copilot-studio/external-security-provider#step-2-configure-the-threat-detection-system)

|Parameter|Value|
|---|---|
|Federated credential scenario|Other issuer|
|Issuer|https://login.microsoftonline.com/{tenantId}/v2.0|
|Value|`/eid1/c/pub/t/{base 64 encoded tenantId}/a/m1WPnYRZpEaQKq1Cceg--g/{base 64 encoded endpoint}`|

The `https://mcsaiagents.security.core.microsoft/v1/protection`

Example using PowerShell to get Base64 encoded values:

```pwsh
# Encoding tenant ID
$tenantId = [Guid]::Parse("323626f5-1bfe-48cd-8902-ddfdfd44e1ce")
$base64EncodedTenantId = [Convert]::ToBase64String($tenantId.ToByteArray()).Replace('+','-').Replace('/','_').TrimEnd('=')
Write-Output $base64EncodedTenantId

# Encoding the endpoint
$endpointURL = "https://mcsaiagents.security.core.microsoft/v1/protection"
$base64EncodedEndpointURL = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($endpointURL)).Replace('+','-').Replace('/','_').TrimEnd('=')
Write-Output $base64EncodedEndpointURL
```

#### Additional threat detection and protection for Copilot Studio agents (optional)

For integration to threat detection partner:

![](https://github.com/user-attachments/assets/a66ef35c-adc6-4fd4-84c2-07cebcbc9135)

![](https://github.com/user-attachments/assets/a125544d-c667-4ec3-9a4d-fb5e7133edb4)
