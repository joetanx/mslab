## 0. Setup

### 0.1. Grant OpenClaw access to Foundry model

Add role assignment for `Cognitive Services User` to the Azure VM system managed identity:

![](https://github.com/user-attachments/assets/173738c1-ca77-4aa7-8b89-018fb3b78d70)

### 0.2. Setup Azure CLI

Install Azure CLI:

```sh
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash
```

Login to Azure VM with system managed identity:

```sh
az login --identity
```

Check account and subscription are currently set as the active context:

```sh
az account show
```

### 0.3. Install OpenClaw

```sh
curl -fsSL https://openclaw.ai/install.sh | bash
```

![](https://github.com/user-attachments/assets/b8108796-8f88-437e-9ffe-0b476d9d2f13)

> [!Tip]
> 
> If the first setup was aborted, it can be rerun with:
> 
> ```sh
> openclaw onboard
> ```

Select `QuickStart` to use defaults:

![](https://github.com/user-attachments/assets/74c90a73-ed3e-4656-a199-8aa84ea71921)

### 0.4. Setup Microsoft Foundry model provider

![](https://github.com/user-attachments/assets/5753dddc-049f-49d4-abf4-5260e3c86750)

![](https://github.com/user-attachments/assets/5809e748-9bce-4bc9-844c-d35bd914e512)

![](https://github.com/user-attachments/assets/7ca529f1-97c8-493c-844c-7605b235986a)

![](https://github.com/user-attachments/assets/47f86230-e9a8-448b-a426-15619a16a94e)

![](https://github.com/user-attachments/assets/ee984f60-ce74-45ad-9461-4070d8d9bae1)

### 0.5. Setup Teams app

#### 0.5.1. Install [Teams CLI v3](https://microsoft.github.io/teams-sdk/cli/)

The `@preview` suffix is requried to install v3, which is current in preview

```sh
apt update && apt -y install npm
npm install -g @microsoft/teams.cli@preview
```

The Teams CLI v3 includes options like [login](https://microsoft.github.io/teams-sdk/cli/commands/login/), [status](https://microsoft.github.io/teams-sdk/cli/commands/status/) and [app create](https://microsoft.github.io/teams-sdk/cli/commands/app/create)

![](https://github.com/user-attachments/assets/61be52c0-170a-4a49-9acc-589b81164eb0)

#### 0.5.2. Login

```
teams login
```

![](https://github.com/user-attachments/assets/2f998112-41a5-4fc9-b272-89f403112f7e)

![](https://github.com/user-attachments/assets/2ee0af13-53e4-4b70-9942-233cbb9ddee7)

Teams CLI requires sideloading to be enabled in the policy applied to the sign-in user

Teams Admin Center → Users → Find the user → Policies → App setup policy → "Upload custom apps"

![](https://github.com/user-attachments/assets/ed911e99-d387-4666-9783-ab405b1b181c)

![](https://github.com/user-attachments/assets/707dc008-28bd-4306-906d-15819bda4c4c)

#### 0.5.3. Configure VNet for API management to reach OpenClaw VM

Select the VNet and subnet that the APIM should attach to:

![](https://github.com/user-attachments/assets/ef6c8b64-5158-4dbe-b8d2-94d9247ebd54)

Run the VNet verifier:

![](https://github.com/user-attachments/assets/9958f45e-f924-497f-8ba3-851bef3f4c88)

Example list of errors:

![](https://github.com/user-attachments/assets/c5997a6e-26b4-4b0d-a115-531b09dce085)

##### Vnet Routing Issues detected - Vnet peering is detected with no UDR for API Management network traffic on subnet access-apim. Please make the changes below.

![](https://github.com/user-attachments/assets/6d4e3309-6806-4e6d-ab79-02e41c5abfe9)

![](https://github.com/user-attachments/assets/e26fbd71-2484-46de-870f-1bf3570b23ff)

![](https://github.com/user-attachments/assets/f31cfd42-c822-4b99-9481-6de041e127bc)

##### NSG Security rules do not fulfill the recommended requirements

![](https://github.com/user-attachments/assets/f243843a-f057-499b-8419-4a4c5a4d517d)

![](https://github.com/user-attachments/assets/bc3840a5-2568-4d03-80cf-fae9fbdefd92)

##### Service endpoints are not enabled for recommended services.

![](https://github.com/user-attachments/assets/7630cfef-03c2-4ee4-92a8-d595931128d3)

![](https://github.com/user-attachments/assets/9d8e70c0-5e3f-4a0a-bd28-60670f711238)
