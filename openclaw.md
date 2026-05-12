## 1. Setup OpenClaw

### 1.1. Install OpenClaw

```sh
curl -fsSL https://openclaw.ai/install.sh | bash
```

![](https://github.com/user-attachments/assets/a4f96b06-a6b6-4f0f-955f-55a86e69a14f)

Exit the setup with `Ctrl + C` and run below command to set gateway bind to `lan`:

```sh
openclaw config set gateway.bind lan
```

Set `OPENCLAW_ALLOW_INSECURE_PRIVATE_WS` client-side parameter to `1` to allow connection with `ws://` instead of `wss://` (default) for the setup process:

```sh
export OPENCLAW_ALLOW_INSECURE_PRIVATE_WS=1
```

Run the onboarding wizard with `--install-daemon` option:

```sh
openclaw onboard --install-daemon
```

Select `QuickStart` to use defaults:

![](https://github.com/user-attachments/assets/388e947b-0eda-41ab-9447-f0d95156a726)

### 1.2. Setup Microsoft Foundry model provider

#### 1.2.1. Grant Foundry model access to OpenClaw

Add role assignment for `Cognitive Services User` to the Azure VM system managed identity:

![](https://github.com/user-attachments/assets/173738c1-ca77-4aa7-8b89-018fb3b78d70)

#### 1.2.2. Setup Azure CLI

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

#### 1.2.2. Configure Microsoft Foundry model provider

![](https://github.com/user-attachments/assets/429b387a-a7e6-4c7b-a362-2f72822f4ec3)

![](https://github.com/user-attachments/assets/e53fbcbb-3429-4701-9886-332b89b42ed2)

![](https://github.com/user-attachments/assets/15e002c1-d256-4546-a11d-e19826382e78)

![](https://github.com/user-attachments/assets/93f90fc0-a95c-4839-b086-29a5c6479be2)

![](https://github.com/user-attachments/assets/1ef26ffb-85ea-4119-9adc-ae2fc9807db2)

Skip other configurations:

![](https://github.com/user-attachments/assets/407d3640-1a94-492b-873b-09633a2d1b47)

![](https://github.com/user-attachments/assets/95081108-9b57-4ffe-84f4-1503074cba63)

![](https://github.com/user-attachments/assets/faa03b56-64c4-4061-9f23-d2e94ebb01ad)

![](https://github.com/user-attachments/assets/ae5a80ab-d0ac-4569-bf74-a4044ce574f5)

![](https://github.com/user-attachments/assets/6a2c9c81-2449-4ef9-97c7-eb70b175fec4)

> [!Tip]
>
> If reset/reinstall or troubleshooting is required, the OpenClaw gateway systemd daemon can be uninstalled with below command
>
> ```sh
> openclaw gateway uninstall
> ```

![](https://github.com/user-attachments/assets/07876b0c-9d7c-4bf5-8316-b80e144c9cea)

### 1.3. Access OpenClaw gateway dashboard from reverse proxy

Example reverse proxy setup:

```
client
└───Azure app gateway → TLS offloading (e.g. https://<domain-name>/)
    └───OpenClaw VM → http://<vm-ip-address>:18789
```

To get OpenClaw gateway token:

```sh
cat .openclaw/openclaw.json | jq -r '.gateway.auth.token'
```

Access OpenClaw gateway dashboard: `https://<domain-name>/#token=<.gateway.auth.token>`

The gateway default settings allow origins from `http://localhost:18789` and `http://127.0.0.1:18789`

This setting is in `.openclaw/openclaw.json`:

```json
{
  ⋮
  "gateway": {
    ⋮
    "controlUi": {
      "allowInsecureAuth": true,
      "allowedOrigins": [
        "http://localhost:18789",
        "http://127.0.0.1:18789"
      ]
    },
```

Attempting to access from a reverse proxy's domain leads to `origin not allowed` error:

> origin not allowed (open the Control UI from the gateway host or allow it in gateway.controlUi.allowedOrigins)

![](https://github.com/user-attachments/assets/713cbc72-d16b-499d-aef9-023d82c060bb)

Add the desired domains with `openclaw config set gateway.controlUi.allowedOrigins` and restart the gateway:

```sh
openclaw config set gateway.controlUi.allowedOrigins '[ \
  "http://localhost:18789", \
  "http://127.0.0.1:18789", \
  "http://<vm-ip-address>:18789", \
  "https://<domain-name>" \
]' --strict-json
systemctl --user restart openclaw-gateway
```

![](https://github.com/user-attachments/assets/70dcaa16-bf48-463a-935a-1d7066b22f66)

Other than checking `.openclaw/openclaw.json`, the settings can also be retrieved with:

```sh
openclaw config get gateway.controlUi.allowedOrigins
```

![](https://github.com/user-attachments/assets/fbe2ca56-94fd-4e14-b9e2-bccfe20177eb)

### 1.4. Allow remote client connection to OpenClaw gateway dashboard

New clients connecting to OpenClaw gateway dashboard are blocked with `device pairing required` error:

![](https://github.com/user-attachments/assets/a85a12ef-edf9-4958-abb8-40f9a5f77240)

```sh
openclaw devices list
```

![](https://github.com/user-attachments/assets/ab244d52-7ea5-420f-bcd1-fe7cecd04394)

Approve the device with:

```sh
openclaw devices approve <request-id>
```

![](https://github.com/user-attachments/assets/a934e156-cf98-45d8-b19e-3457c206fcb9)

Reload the page after approval:

![](https://github.com/user-attachments/assets/c800e4d3-cdb7-4ae1-acd4-b14dac1652f4)

## 2. Setup Teams channel

### 2.1. Enable sideloading in Teams

Teams CLI requires sideloading to be enabled in the policy applied to the sign-in user:

![](https://github.com/user-attachments/assets/880c15db-a16e-4c16-a609-e6a166df1c18)

Teams Admin Center → Users → Find the user → Policies → App setup policy → "Upload custom apps"

![](https://github.com/user-attachments/assets/ed911e99-d387-4666-9783-ab405b1b181c)

![](https://github.com/user-attachments/assets/707dc008-28bd-4306-906d-15819bda4c4c)

### 2.2. Setup API management for OpenClaw Teams plugin

#### 2.2.1. Configure VNet for API management to reach OpenClaw VM

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

#### 2.2.2. Create API to OpenClaw Teams plugin

![](https://github.com/user-attachments/assets/d9b45a39-ee90-4af3-9a8b-6846f7782bf1)

![](https://github.com/user-attachments/assets/706686b8-81d6-4609-92a7-0a07684e3a60)

![](https://github.com/user-attachments/assets/7b187d36-1356-4507-adc4-2d8ccd5d9999)

### 2.3. Setup Teams app

[OpenClaw Teams plugin documentation](https://docs.openclaw.ai/channels/msteams)

#### 2.3.1. Install [Teams CLI v3](https://microsoft.github.io/teams-sdk/cli/)

The `@preview` suffix is requried to install v3, which is current in preview

```sh
apt update && apt -y install npm
npm install -g @microsoft/teams.cli@preview
```

The Teams CLI v3 includes options like [login](https://microsoft.github.io/teams-sdk/cli/commands/login/), [status](https://microsoft.github.io/teams-sdk/cli/commands/status/) and [app create](https://microsoft.github.io/teams-sdk/cli/commands/app/create)

![](https://github.com/user-attachments/assets/a87472b3-abcb-44ba-9c0a-f328566d9710)

#### 2.3.2. Login

On headless server (e.g. SSH) use:

```sh
export TEAMS_NO_INTERACTIVE=1
teams login
```

or

```sh
teams login --device-code
```

![](https://github.com/user-attachments/assets/03912198-18c8-4b9e-8fc9-e10550b21b9d)

```sh
teams status
```

![](https://github.com/user-attachments/assets/d9e8bacf-d3fc-4bf6-ab4d-1be559b36c78)

#### 2.3.3. Create Teams app

```
teams app create --name OpenClaw --endpoint https://access-7f518691.azure-api.net/api/messages
```

![](https://github.com/user-attachments/assets/b31cf775-5f68-44b4-b717-9695d6db5fd5)

The `teams app create` command creates a Teams app, a Teams-managed bot and an Entra ID app registration

Verify the Teams resources created on Teams developer portal: https://dev.teams.microsoft.com/

![](https://github.com/user-attachments/assets/419380a6-76d3-4f48-a1be-cdabf50efa1d)

![](https://github.com/user-attachments/assets/f64c2a6c-7be8-4376-9b48-24c37c0f3930)

#### 2.3.4. Setup federated identity credential to OpenClaw app registration

![](https://github.com/user-attachments/assets/c39e1c2f-3b70-4d23-9fbb-a7d0914cfb7a)

![](https://github.com/user-attachments/assets/f9a31961-5a5c-4bde-848e-313482766483)

### 2.4. Install Teams plugin

```sh
openclaw plugins install @openclaw/msteams
```

![](https://github.com/user-attachments/assets/f8d89e30-db21-4cba-88fe-76c47204d16b)

### 2.5. Configure Teams channel

```sh
openclaw config set channels.msteams.enabled true
openclaw config set channels.msteams.appId <APP_ID>
openclaw config set channels.msteams.tenantId <TENANT_ID>
openclaw config set channels.msteams.authType federated
openclaw config set channels.msteams.useManagedIdentity true
openclaw config set channels.msteams.webhook '{ "port": 3978, "path": "/api/messages" }' --strict-json
```

Restart OpenClaw gateway:

```
systemctl --user restart openclaw-gateway
```

### 2.6. Chat with OpenClaw over teams

Get the app install link:

```sh
teams app get <APP_ID> --install-link
```

![](https://github.com/user-attachments/assets/fb8b7579-7c33-445f-be3d-64b340fb90a7)

Open and send a message:

![](https://github.com/user-attachments/assets/d42d4b2b-f54f-43be-a6d5-6c272741ca15)

The default [DM access](https://docs.openclaw.ai/channels/msteams#access-control-dms-+-groups) is `channels.msteams.dmPolicy = "pairing"`: Unknown senders are ignored until approved.

List pending pairings:

```sh
openclaw pairing list msteams
```

![](https://github.com/user-attachments/assets/7925cb69-aec0-43f5-bb8b-31ff1973e381)

Approve pairing:

```sh
openclaw pairing approve msteams <code>
```

![](https://github.com/user-attachments/assets/09c9cac8-da60-4772-93b8-93f56a8b7e74)
