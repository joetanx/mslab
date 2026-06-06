## 1. Settings page

Defender portal → Settings → Security for AI

![](https://github.com/user-attachments/assets/f66a0da4-3010-4e90-aa25-965677e27718)

### 1.1. Without Agent 365 license

|Security for AI agents: not enabled|Security for AI agents: enabled|
|---|---|
|![](https://github.com/user-attachments/assets/71a786ac-635e-40e7-b4e8-c7ccf7b40d2d)|![](https://github.com/user-attachments/assets/3c51fb94-2dad-47bf-a706-c21644cae6f0)|

### 1.2. With Agent 365 license

|Security for AI agents: not enabled|Security for AI agents: enabled|
|---|---|
|![](https://github.com/user-attachments/assets/4f72df25-457c-4142-ae79-930222934333)|![](https://github.com/user-attachments/assets/22d1596c-4279-4db6-8ca7-cda9e3dae77a)|

## 2. Connect Copilot Studio

### 2.1. AI security posture

![](https://github.com/user-attachments/assets/0fb8487b-1336-4d85-96e4-26c306577835)

Open Power Platform Admin Center (click on link or go to https://admin.powerplatform.microsoft.com/security/threatdetection):

![](https://github.com/user-attachments/assets/c2bdcd3c-39f6-4352-b691-82fc52d4c9be)

Toggle: `Enable Microsoft Defender - For all Copilot Studio Agents in tenant`

![](https://github.com/user-attachments/assets/bedd682c-2ca7-462a-9b9d-851a922de46e)

> [!Note]
>
> Connected status may take up to 1 hour after admin setup.

#### Additional threat detection and protection for Copilot Studio agents (optional)

For integration to threat detection partner:

![](https://github.com/user-attachments/assets/a66ef35c-adc6-4fd4-84c2-07cebcbc9135)

![](https://github.com/user-attachments/assets/a125544d-c667-4ec3-9a4d-fb5e7133edb4)

### 2.2. AI real-time protection & investigation

Create App Registration: https://learn.microsoft.com/en-us/microsoft-copilot-studio/external-security-provider#step-1-configure-microsoft-entra-application

Example display name: `Copilot Security Integration - Production`
