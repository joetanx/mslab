## 0. Cloud infrastructure setup

> Adapted from https://github.com/microsoft/Agent365-Samples/tree/main/python/agent-framework/sample-agent

> [!Important]
>
> The setup is performed in Cloud Shell (bash) in Azure portal, which already has `az`, `dotnet`, `python` and `pwsh` (v7) tools.
>
> (it even has most bash utilities like `vi` and `envsubst`)
>
> This is convenient, but the session is **ephemeral**, so any files to be kept from the session must be download via `Manage files` from the Cloud Shell

Setup the shell/environment variables:

```sh
SUBSCRIPTION_ID='<subscription-id>'
export LOCATION='southeastasia'
export APP_NAME='a365-test-01'
export RG="rg-$APP_NAME"
CAE_NAME="cae-$APP_NAME"
FOUNDRY_NAME="foundry-$APP_NAME"
PROJECT_NAME="proj-$APP_NAME"
MODEL_NAME='gpt-5.4-mini'
UAMI_NAME="uami-$APP_NAME"
```

> [!Tip]
>
> Shell vs environment variables:
>
> |  | Shell variables | Environment variables|
> |---|---|---|
> | Scope | **Local** to the current shell process | **Global** to the shell and all spawned child processes. |
> | Viewing command | `set` (displays all shell and environment variables) | `env` or `printenv` |
> 
> Notice that certain variables in this write-up are `export`ed because they are used for `envsubst` later to be substituted into the container app manifest file

Set az CLI to desired subscription (so that all future az commands uses this subscription without having to specify `--subscription`) and create the resource group:

```sh
az account set --subscription $SUBSCRIPTION_ID
az group create --name $RG --location $LOCATION
```

> [!Note]
>
> The subscription needs to be registered for `Microsoft.OperationalInsights` and `Microsoft.ContainerRegistry` resource provider for container apps environment and container registry creation.
>
> ```sh
> az provider register --namespace Microsoft.OperationalInsights
> az provider register --namespace Microsoft.ContainerRegistry
> ```
>
> Check the registration state, it can take some time to change from `Registering` to `Registered`:
>
> ```sh
> az provider show --namespace Microsoft.OperationalInsights --query "registrationState"
> az provider show --namespace Microsoft.ContainerRegistry --query "registrationState"
> ```

## 1. Foundry

Create Foundry resource:

```sh
az cognitiveservices account create \
  --name $FOUNDRY_NAME --resource-group $RG \
  --location $LOCATION --kind 'AIServices' --sku 'S0' \
  --allow-project-management 'true' --custom-domain $FOUNDRY_NAME --yes
```

> Delete and purge Foundry resource (if need to redo)
> 
> ```sh
> az cognitiveservices account delete --name $FOUNDRY_NAME --resource-group $RG
> az cognitiveservices account purge --name $FOUNDRY_NAME --resource-group $RG --location $LOCATION
> ```

Create Project under the Foundry resource:

```sh
az cognitiveservices account project create \
  --name $FOUNDRY_NAME --resource-group $RG --location $LOCATION \
  --project-name $PROJECT_NAME --display-name $PROJECT_NAME
```

Create model deployment:

```sh
MODEL_VERSION=$(az cognitiveservices model list --location $LOCATION --query "[?model.name=='${MODEL_NAME}'&&kind=='AIServices'].model.version" -o tsv)
az cognitiveservices account deployment create \
  --name $FOUNDRY_NAME --resource-group $RG --deployment-name $MODEL_NAME \
  --model-name $MODEL_NAME --model-version $MODEL_VERSION --model-format 'OpenAI' \
  --sku-capacity 500 --sku 'GlobalStandard'
```

Export project endpoint and model environment variables:

```sh
export FOUNDRY_PROJECT_ENDPOINT=$(az cognitiveservices account project show --name $FOUNDRY_NAME --resource-group $RG --project-name $PROJECT_NAME  --query 'properties.endpoints' -o tsv)
export FOUNDRY_MODEL=$MODEL_NAME
```

### 1.1.  Create UAMI and assign role

Create UAMI:

```sh
az identity create --name $UAMI_NAME --resource-group $RG
```

Get UAMI service principal ID:

```sh
UAMI_ID=$(az identity show --name $UAMI_NAME --resource-group $RG --query principalId -o tsv)
```

Export UAMI client ID as environment variable:

```sh
export UAMI_CLIENT_ID=$(az identity show --name $UAMI_NAME --resource-group $RG --query clientId -o tsv)
```

Get Foundry ID:

```sh
FOUNDRY_ID=$(az cognitiveservices account show --name $FOUNDRY_NAME --resource-group $RG --query id -o tsv)
```

Grant `Cognitive Services User` to UAMI for Foundry resource:

```sh
az role assignment create --assignee $UAMI_ID --role 'Cognitive Services User' --scope $FOUNDRY_ID
```

Get UAMI resource ID (for later container app deployment use):

```sh
export UAMI_RSC_ID=$(az identity show --name $UAMI_NAME --resource-group $RG --query id -o tsv)
```

## 2. Container Apps Environment

Create Container Apps environment:

```sh
az containerapp env create --name $CAE_NAME --resource-group $RG --location $LOCATION
```

Verify container app environment ID:

```sh
export CAE_ID=$(az containerapp env show --name $CAE_NAME --resource-group $RG --query id -o tsv)
```

Get container app environment domain (for a365 CLI messaging endpoint):

```sh
CAE_DOMAIN=$(az containerapp env show --name $CAE_NAME --resource-group $RG --query "properties.defaultDomain" --output tsv)
```

## 3. Azure Files

Prepare variables (storage account name cannot contain dashes):

```sh
SA_NAME="sa${APP_NAME//-/}$RANDOM"
export SHARE_NAME="$APP_NAME-share"
```

Create storage account + file share:

```sh
az storage account create --name $SA_NAME --resource-group $RG --location $LOCATION --sku Standard_LRS --tags SecurityControl=Ignore
CONN_STR=$(az storage account show-connection-string --name $SA_NAME --resource-group $RG --query connectionString -o tsv)
az storage share create --name $SHARE_NAME --connection-string "$CONN_STR"
```

Download app files from GitHub and upload to storage account:

```sh
for FILE in start_with_generic_host.py host_agent_server.py agent.py agent_interface.py local_authentication_options.py token_cache.py; do
  curl -sLO "https://github.com/joetanx/mslab/raw/refs/heads/main/agent-365/samples/agent-framework/app/$FILE"
  az storage file upload --share-name $SHARE_NAME --source $FILE --connection-string $CONN_STR
done
```

Register Azure Files storage in container app environment:

```sh
SA_KEY=$(az storage account keys list --account-name $SA_NAME --resource-group $RG --query "[0].value" -o tsv)
az containerapp env storage set \
  --name $CAE_NAME --storage-name $SHARE_NAME --resource-group $RG \
  --azure-file-account-name $SA_NAME --azure-file-account-key "$SA_KEY" \
  --azure-file-share-name $SHARE_NAME --access-mode ReadOnly
```

## 4. Container Registry

Create ACR (ACR name cannot contain dashes):

```sh
export ACR_NAME="acr${APP_NAME//-/}$RANDOM"
az acr create --name $ACR_NAME --resource-group $RG --location $LOCATION --sku Basic --tags SecurityControl=Ignore
```

Build image directly in ACR (no local Docker needed):

```sh
curl -sLO "https://github.com/joetanx/mslab/raw/refs/heads/main/agent-365/samples/agent-framework/{pyproject.toml,Dockerfile}"
az acr build --registry $ACR_NAME --image $APP_NAME:latest --file Dockerfile .
```

Get ACR ID:

```sh
ACR_ID=$(az acr show --name $ACR_NAME --query id -o tsv)
```

Grant `AcrPull` to UAMI for ACR:

```sh
az role assignment create --assignee $UAMI_ID --role AcrPull --scope $ACR_ID
```

## 5. Agent 365 CLI

Install a365 CLI in the Cloud Shell:

```sh
dotnet tool install --global Microsoft.Agents.A365.DevTools.Cli
export PATH=$PATH:/home/system/.dotnet/tools/
```

> [!Tip]
>
> Run `a365 setup requirements` to verify if the tenant has the necessary prerequisites (e.g. `Agent 365 CLI` app registration)
>
> Read more about the prerequisites: https://github.com/joetanx/mslab/blob/main/agent-365/a365-cli.md

```sh
MESSAGING_ENDPOINT="https://ca-$APP_NAME.$CAE_DOMAIN/api/messages"
a365 setup all --aiteammate -n $APP_NAME --messaging-endpoint $MESSAGING_ENDPOINT
```

> [!Important]
>
> Download the `a365.config.json` and `a365.generated.config.json` files from the cloud shell and keep them.
>
> The a365 CLI references these config files to resume the work on the agent for future commands.

```sh
export TENANT_ID=$(python3 -c "import json; print(json.load(open('a365.config.json'))['tenantId'])")
export BLUEPRINT_CLIENT_ID=$(python3 -c "import json; print(json.load(open('a365.generated.config.json'))['agentBlueprintId'])")
export BLUEPRINT_CLIENT_SECRET=$(python3 -c "import json; print(json.load(open('a365.generated.config.json'))['agentBlueprintClientSecret'])")
```

### 5.1. Configure tools

List availables tools in the [Agent 365 tools catalog](https://learn.microsoft.com/en-us/microsoft-agent-365/tooling-servers-overview#agent-365-tools-catalog)

```sh
a365 develop list-available
```

Add desired tools to the agent, this generates the `ToolingManifest.json` file:

```sh
for mcp in mcp_M365Copilot mcp_CalendarTools mcp_MailTools mcp_SharePointRemoteServer mcp_OneDriveRemoteServer mcp_TeamsServer mcp_MeServer mcp_WordServer; do
  a365 develop add-mcp-servers $mcp
done
```

> [!Note]
>
> These tools are now consider legacy:
> - mcp_ExcelServer
> - mcp_ODSPRemoteServer
> - cp_WebSearchTools
> - mcp_SharePointListsTools
>
> Below warning occurs when trying to add legacy tools (but still usable at the time of writing):
>
> ```
> uses a legacy ATG audience and may not work correctly. Consider re-running add-mcp-servers to pick up the latest catalog.
> ```

Verify/view the tools configured in `ToolingManifest.json`

```sh
a365 develop list-configured
```

Run `setup all` again, or `setup permissions mcp` to grant the permissions required by the tool

```sh
a365 setup permissions mcp -n $APP_NAME
```

### 5.2. Publish agent manifest in M365 Admin Center

```sh
a365 publish
```

This command generates the `manifest/manifest.zip` file, download it from the cloud shell

Upload the manifest to M365 Admin Center

1. Go to https://admin.cloud.microsoft/#/agents/all
2. From menu on top of the agents list, click the elipsis `…` and select `Add agent`
3. `Choose file` to select the `manifest.zip` file
4. Select the desired users or groups to `Activate` for
5. Select the template to apply, review permission, then `Publish`

## 6. Deploy container app

Download manifest template and replace placeholders with environment variables

```sh
curl -sLO https://github.com/joetanx/mslab/raw/refs/heads/main/agent-365/samples/agent-framework/containerapp.yaml
envsubst < containerapp.yaml > containerapp-edited.yaml
```

Deploy container app with edited manifest file:

```sh
az containerapp create --name "ca-$APP_NAME" --resource-group $RG --yaml containerapp-edited.yaml
```
