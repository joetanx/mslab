## 1. Setup prequisites

### 1.1. Grant Foundry model access to OpenClaw

Add role assignment for `Cognitive Services User` to the Azure VM system managed identity:

![](https://github.com/user-attachments/assets/173738c1-ca77-4aa7-8b89-018fb3b78d70)

### 1.2. Enable sideloading in Teams

Teams CLI requires sideloading to be enabled in the policy applied to the sign-in user:

![](https://github.com/user-attachments/assets/2ee0af13-53e4-4b70-9942-233cbb9ddee7)

Teams Admin Center → Users → Find the user → Policies → App setup policy → "Upload custom apps"

![](https://github.com/user-attachments/assets/ed911e99-d387-4666-9783-ab405b1b181c)

![](https://github.com/user-attachments/assets/707dc008-28bd-4306-906d-15819bda4c4c)

### 1.3. Setup API management for OpenClaw Teams plugin

#### 1.3.1. Configure VNet for API management to reach OpenClaw VM

Select the VNet and subnet that the APIM should attach to:

![](https://github.com/user-attachments/assets/ef6c8b64-5158-4dbe-b8d2-94d9247ebd54)

Run the VNet verifier:

![](https://github.com/user-attachments/assets/9958f45e-f924-497f-8ba3-851bef3f4c88)

<details><Summary><h5>Common APIM VNet integration errors and fixes</h5></Summary>

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

##### Example successful VNet verifier results

![](https://github.com/user-attachments/assets/f85a5624-c358-4554-b191-b1b4a163a4da)

</details>

#### 1.3.2. Create API to OpenClaw Teams plugin

![](https://github.com/user-attachments/assets/d9b45a39-ee90-4af3-9a8b-6846f7782bf1)

![](https://github.com/user-attachments/assets/0cad784e-9a96-42da-a4c3-be39632f8ebd)

![](https://github.com/user-attachments/assets/a9fe2c61-ed67-46ff-852c-1e7002cd0281)

### 1.4. Setup Teams app

[OpenClaw Teams plugin documentation](https://docs.openclaw.ai/channels/msteams)

#### 1.4.1. Install [Teams CLI v3](https://microsoft.github.io/teams-sdk/cli/)

The `@preview` suffix is requried to install v3, which is current in preview

```sh
apt update && apt -y install npm
npm install -g @microsoft/teams.cli@preview
```

The Teams CLI v3 includes options like [login](https://microsoft.github.io/teams-sdk/cli/commands/login/), [status](https://microsoft.github.io/teams-sdk/cli/commands/status/) and [app create](https://microsoft.github.io/teams-sdk/cli/commands/app/create)

![](https://github.com/user-attachments/assets/9fedc0f1-8259-47c8-924a-db1626813e2d)

#### 1.4.2. Login

On headless server (e.g. SSH) use:

```sh
export TEAMS_NO_INTERACTIVE=1
teams login
```

or

```sh
teams login --device-code
```

![](https://github.com/user-attachments/assets/aacbdb79-c5e7-4480-a99f-41e7df33dcae)

```sh
teams status
```

![](https://github.com/user-attachments/assets/5472caa0-b703-477c-9d7f-d0669518667d)

#### 1.4.3. Create Teams app

```
teams app create --name OpenClaw --endpoint https://access-7f518691.azure-api.net/api/messages
```

![](https://github.com/user-attachments/assets/e96f74e7-0bbe-49b6-b4d7-d47702be9694)

The `teams app create` command creates a Teams app, a Teams-managed bot and an Entra ID app registration

Verify the Teams resources created on Teams developer portal: https://dev.teams.microsoft.com/

![](https://github.com/user-attachments/assets/419380a6-76d3-4f48-a1be-cdabf50efa1d)

![](https://github.com/user-attachments/assets/f64c2a6c-7be8-4376-9b48-24c37c0f3930)

#### 1.4.4. Setup federated identity credential to OpenClaw app registration

![](https://github.com/user-attachments/assets/c39e1c2f-3b70-4d23-9fbb-a7d0914cfb7a)

![](https://github.com/user-attachments/assets/f9a31961-5a5c-4bde-848e-313482766483)

## 2. Setup OpenClaw

### 2.1. Install OpenClaw

```sh
curl -fsSL https://openclaw.ai/install.sh | bash
```

![](https://github.com/user-attachments/assets/3ed219b2-bd0e-42d5-9d5b-1752e7ccec33)

Exit the setup with `Ctrl + C` and run below command to set gateway bind to `lan`:

```sh
openclaw config set gateway.bind lan
```

Run the onboarding wizard with `--install-daemon` option:

```sh
openclaw onboard --install-daemon
```

Select `QuickStart` to use defaults:

![](https://github.com/user-attachments/assets/388e947b-0eda-41ab-9447-f0d95156a726)

### 2.2. Setup Microsoft Foundry model provider

#### 2.2.1. Setup Azure CLI

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

#### 2.2.2. Configure Microsoft Foundry model provider

![](https://github.com/user-attachments/assets/429b387a-a7e6-4c7b-a362-2f72822f4ec3)

![](https://github.com/user-attachments/assets/e53fbcbb-3429-4701-9886-332b89b42ed2)

![](https://github.com/user-attachments/assets/15e002c1-d256-4546-a11d-e19826382e78)

![](https://github.com/user-attachments/assets/93f90fc0-a95c-4839-b086-29a5c6479be2)

![](https://github.com/user-attachments/assets/1ef26ffb-85ea-4119-9adc-ae2fc9807db2)
