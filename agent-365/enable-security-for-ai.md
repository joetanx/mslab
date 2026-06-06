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

Open Power Platform Admin Center (https://admin.powerplatform.microsoft.com/security/threatdetection):

![](https://github.com/user-attachments/assets/c2bdcd3c-39f6-4352-b691-82fc52d4c9be)

Toggle: `Enable Microsoft Defender - For all Copilot Studio Agents in tenant`

![](https://github.com/user-attachments/assets/bedd682c-2ca7-462a-9b9d-851a922de46e)

> [!Note]
>
> Connected status may take up to 1 hour after admin setup.

### 3.2. AI real-time protection & investigation

#### [Create App Registration](https://learn.microsoft.com/en-us/microsoft-copilot-studio/external-security-provider#step-1-configure-microsoft-entra-application)

![](https://github.com/user-attachments/assets/c3960bbf-b1c8-4628-8812-20e6dca7895b)

#### [Configure Federated Identity Credentials (FIC)](https://learn.microsoft.com/en-us/microsoft-copilot-studio/external-security-provider#step-2-configure-the-threat-detection-system)

Power Platform integration endpoint: `https://mcsaiagents.security.core.microsoft/v1/protection`

![](https://github.com/user-attachments/assets/9bc94fc7-a4e8-4f7d-99d7-3ae5241b49cb)

|Parameter|Value|
|---|---|
|Federated credential scenario|`Other issuer`|
|Issuer|`https://login.microsoftonline.com/{tenantId}/v2.0`|
|Value|`/eid1/c/pub/t/{base64-encoded tenantId}/a/m1WPnYRZpEaQKq1Cceg--g/{base64-encoded endpoint}`|

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

![](https://github.com/user-attachments/assets/df593baa-3174-4738-9581-754de040493d)

#### Configure Power Platform: Additional threat detection and protection for Copilot Studio agents

Open Power Platform Admin Center (https://admin.powerplatform.microsoft.com/security/threatdetection):

![](https://github.com/user-attachments/assets/a66ef35c-adc6-4fd4-84c2-07cebcbc9135)

![](https://github.com/user-attachments/assets/2f872f4a-4e85-443f-8a56-0204b622c252)

#### Save protection setting on Defender

![](https://github.com/user-attachments/assets/7979c360-6aae-46a0-94a3-ec2ad61d0752)

![](https://github.com/user-attachments/assets/e1b6516a-0d36-4060-af56-5b27f1f0a732)
