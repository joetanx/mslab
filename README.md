Collection of lab setups done as a Microsoft techie

### Agent 365

| Topic | Description |
|---|---|
| [Agent 365 SDK samples](samples) | Sample agents for Microsoft Agent Framework and Langchain deploying in Container Apps |
| [Agent 365 CLI](a365-cli.md) | Setting up Agent 365 CLI and using the CLI to setup an agent in Agent 365 |
| [Enable Security for AI](enable-security-for-ai.md) | Setting up [security for AI agents](https://learn.microsoft.com/en-us/security/security-for-ai/agent-365-security) |
| [Publishing agents](publish-agents-to-teams-copilot.md) | Walkthrough of publishing agents from Copilot Studio and Foundry,<br>and approving request to publish to M365 Copilot and Teams |

### [Entra authorization flows](https://github.com/joetanx/mslab/tree/main/entra/flows)

| Topic | Description |
|---|---|
|[Client credentials flow](https://github.com/joetanx/mslab/blob/main/entra/flows/client-credentials.md)|[Entra client credential flow](https://learn.microsoft.com/en-us/entra/identity-platform/v2-oauth2-client-creds-grant-flow) using client secret or client certificate for application authentication|
|[Authorization code flow](https://github.com/joetanx/mslab/blob/main/entra/flows/authorization-code.md)|[Entra authorization code flow](https://learn.microsoft.com/en-us/entra/identity-platform/v2-oauth2-auth-code-flow) for delegated user access|
|[On-behalf-of flow](https://github.com/joetanx/mslab/blob/main/entra/flows/on-behalf-of.md)|[Entra on-behalf-of flow](https://learn.microsoft.com/en-us/entra/identity-platform/v2-oauth2-on-behalf-of-flow) uses authorization code flow to get delegated token access and passing access to middle-tier application to act on-behalf-of user|

### [Entra Agent Identity](https://github.com/joetanx/mslab/tree/main/entra/agent-id)

| Topic | Description |
|---|---|
|[Provisioning Agent Identity objects](https://github.com/joetanx/mslab/blob/main/entra/agent-id/provisioning.md)|Use Microsoft Graph API to provisioning agent blueprint, agent blueprint principal, agent identity and agent user|
|[Granting permission and consent to Agent Identity objects](https://github.com/joetanx/mslab/blob/main/entra/agent-id/permissions-and-consent.md)|Use Microsoft Graph API to grant Graph API application and delegated permissions to Agent Identity objects|
|[Entra agent identity authorization flows](https://github.com/joetanx/mslab/blob/main/entra/agent-id/auth-flows.md)|Walkthrough of autonomous agent, agent user impersonation and on-behalf-of human user authorization flows|

### Others

| Topic | Description |
|---|---|
| [Simple secure VNET setup](https://github.com/joetanx/mslab/blob/main/firewall-bastion-natgw.md) | Secure Azure VM access with Bastion and internet connection with Azure Firewall |
| [Key vault](https://github.com/joetanx/mslab/blob/main/key-vault.md) | Onboard VM credentials to Azure key vault to secure VM access via bastion |
| [Azure Arc](https://github.com/joetanx/mslab/blob/main/arc.md) | Setup Azure Arc connection for on-premise Windows and Linux machines |
| [Azure OpenAI](https://github.com/joetanx/mslab/blob/main/azure-openai.md) | Create Azure OpenAI resource (for use with tools like n8n) |
