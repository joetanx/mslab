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
|![](https://github.com/user-attachments/assets/4f72df25-457c-4142-ae79-930222934333)|![](https://github.com/user-attachments/assets/11dbad64-8879-4b36-ac26-7811049813aa)|

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

![](https://github.com/user-attachments/assets/4cf5ced6-4fd2-4e6c-9281-b683cf159906)

### 3.2. AI real-time protection & investigation

#### 3.2.1. [Create App Registration](https://learn.microsoft.com/en-us/microsoft-copilot-studio/external-security-provider#step-1-configure-microsoft-entra-application)

![](https://github.com/user-attachments/assets/c3960bbf-b1c8-4628-8812-20e6dca7895b)

#### 3.2.2. [Configure Federated Identity Credentials (FIC)](https://learn.microsoft.com/en-us/microsoft-copilot-studio/external-security-provider#step-2-configure-the-threat-detection-system)

Power Platform integration endpoint: `https://mcsaiagents.security.core.microsoft/v1/protection`

![](https://github.com/user-attachments/assets/791a1290-cec6-4d1b-a1f8-e3983c045653)

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

#### 3.2.3. Save protection setting on Defender

![](https://github.com/user-attachments/assets/7979c360-6aae-46a0-94a3-ec2ad61d0752)

The status of the connection changes from `Not csonnected` to `Pending Power Platform Action`:

![](https://github.com/user-attachments/assets/e1b6516a-0d36-4060-af56-5b27f1f0a732)

#### 3.2.4. Configure Power Platform: Additional threat detection and protection for Copilot Studio agents

> [!Important]
>
> The Defender setting above must be saved before the Power Platform setting
>
> Otherwise, below error will occur:
>
> ```
> The application ID in your authentication token does not match the registered application for webhook access. Please ensure you are using the correct application credentials.
> ```

Open Power Platform Admin Center (https://admin.powerplatform.microsoft.com/security/threatdetection):

![](https://github.com/user-attachments/assets/a66ef35c-adc6-4fd4-84c2-07cebcbc9135)

![](https://github.com/user-attachments/assets/2f872f4a-4e85-443f-8a56-0204b622c252)

![](https://github.com/user-attachments/assets/33becf40-2dca-4491-ac37-3abda3013bb7)

The status of the connection changes from `Pending Power Platform Action` to `Connected`:

![](https://github.com/user-attachments/assets/0cbaa110-ef28-4e34-ac8e-49150498fb3b)

## 4. Connect Microsoft 365

![](https://github.com/user-attachments/assets/9607bda1-7a0b-49b6-977c-3740fe6654d8)

Clicking `Connect` on the Microsft 365 section:

(The settings pop-up pane is actually the App Connectors settings for Defender for Cloud App at https://security.microsoft.com/cloudapps/settings?tabid=appConnectors)

![](https://github.com/user-attachments/assets/e8e0961d-4544-4fd8-81ff-6fd697778520)

![](https://github.com/user-attachments/assets/8e1343ab-46f4-448f-801d-d8d831da48f6)

### 4.1. Troubleshooting Microsoft 365 connection error

![](https://github.com/user-attachments/assets/a8ff6d3d-e9ea-4f97-b012-b91642fb3cfa)

![](https://github.com/user-attachments/assets/1d34c183-a376-445e-97f1-3caedd407e04)

![](https://github.com/user-attachments/assets/9fbd08eb-d9e7-4d0a-9739-22aaf9679db8)

This error occurs if unified auditing isn't enabled:

`Microsoft.Office.Compliance.Audit: DataServiceException: Tenant <tenantID> does not exist.`

![](https://github.com/user-attachments/assets/3387485c-8ab9-43b1-aa52-844a19329348)

[Unified auditing can be turned on or off](https://docs.microsoft.com/en-us/office365/securitycompliance/turn-audit-log-search-on-or-off) via [Purview portal](https://purview.microsoft.com/audit/auditsearch) or Exchange Online PowerShell

> [!Tip]
>
> Using Exchange Online PowerShell can be more reliable as Purview portal can some times show:
> 
> `Sorry, we're having trouble figuring out if activity is being recorded. Try refreshing the page`
>
> ![](https://github.com/user-attachments/assets/ce80a1d5-47f9-4d94-aa28-81454c496d75)

Exchange Online PowerShell can be used from Azure Cloud Shell with `Connect-ExchangeOnline`

> [!Note]
>
> `Connect-EXOPSSession` was the old commandlet for Exchange Online PowerShell v2, use `Connect-ExchangeOnline` for v3

![](https://github.com/user-attachments/assets/582392ae-a7c2-4845-85f1-0f1935e88abd)
