## Cloud infrastructure setup

```sh
LOCATION='southeastasia'
APP_NAME='a365-test-01'
RG="rg-$APP_NAME"
SUBSCRIPTION_ID='<subscription-id>'
```

```sh
az account set --subscription $SUBSCRIPTION_ID
az group create --name $RG --location $LOCATION
```

```sh
FOUNDRY_NAME="foundry-$APP_NAME"
PROJECT_NAME="proj-$APP_NAME"
MODEL_NAME='gpt-5.4-mini'
UAMI_NAME="uami-$APP_NAME"
```

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

Get project endpoint:

```sh
az cognitiveservices account project show \
  --name $FOUNDRY_NAME --resource-group $RG --project-name $PROJECT_NAME  --query 'properties.endpoints' -o tsv
```

Create model deployment:

```sh
MODEL_VERSION=$(az cognitiveservices model list --location $LOCATION --query "[?model.name=='${MODEL_NAME}'&&kind=='AIServices'].model.version" -o tsv)
az cognitiveservices account deployment create \
  --name $FOUNDRY_NAME --resource-group $RG --deployment-name $MODEL_NAME \
  --model-name $MODEL_NAME --model-version $MODEL_VERSION --model-format 'OpenAI' \
  --sku-capacity 500 --sku 'GlobalStandard'
```

### 1.1.  Create UAMI and assigne role

Create UAMI:

```sh
az identity create --name $UAMI_NAME --resource-group $RG
```

Get UAMI ID:

```sh
UAMI_ID=$(az identity show --name $UAMI_NAME --resource-group $RG --query principalId -o tsv)
```

Get Foundry ID:

```sh
FOUNDRY_ID=$(az cognitiveservices account show --name $FOUNDRY_NAME --resource-group $RG --query id -o tsv)
```

Grant UAMI Cognitive Services User to Foundry resource:

```sh
az role assignment create --assignee $UAMI_ID --role 'Cognitive Services User' --scope $FOUNDRY_ID
```

## 2. Azure Files

Prepare variables (storage account name cannot contain dashes):

```sh
SA_NAME="sa$APP_NAME$RANDOM"
SHARE_NAME="$APP_NAME-share"
```

Create storage account + file share:

```sh
az storage account create \
  --name $SA_NAME --resource-group $RG --location $LOCATION \
  --sku Standard_LRS --tags SecurityControl=Ignore
CONN_STR=$(az storage account show-connection-string \
  --name $SA_NAME --resource-group $RG --query connectionString -o tsv)
az storage share create --name $SHARE_NAME --connection-string "$CONN_STR"
```

Download app files from GitHub and upload to storage account:

```sh
for FILE in start_with_generic_host.py host_agent_server.py agent.py agent_interface.py local_authentication_options.py token_cache.py; do
  curl -sLO "https://github.com/joetanx/mslab/raw/refs/heads/main/agent-365/samples/python/agent-framework/app/$FILE"
  az storage file upload --share-name $SHARE_NAME --source $FILE --connection-string $CONN_STR
done
```

Register Azure Files storage in container app environment:

```sh
SA_KEY=$(az storage account keys list --account-name $SA_NAME --resource-group $RG --query "[0].value" -o tsv)

az containerapp env storage set \
  --name $ENV_NAME --storage-name $SHARE_NAME --resource-group $RG \
  --azure-file-account-name $SA_NAME --azure-file-account-key "$SA_KEY" \
  --azure-file-share-name $SHARE_NAME --access-mode ReadOnly
```

## 3. Container Registry

Create ACR (ACR name cannot contain dashes):

```sh
ACR_NAME="acr$APP_NAME$RANDOM"
az acr create --name $ACR_NAME --resource-group $RG --location $LOCATION --sku Basic --tags SecurityControl=Ignore
```

Build image directly in ACR (no local Docker needed):

```sh
curl -sLO https://github.com/joetanx/mslab/raw/refs/heads/main/agent-365/samples/python/agent-framework/pyproject.toml
curl -sLO https://github.com/joetanx/mslab/raw/refs/heads/main/agent-365/samples/python/agent-framework/Dockerfile
az acr build --registry $ACR_NAME --image $APP_NAME:latest --file Dockerfile .
```

## 4. Container Apps Environment

Create Container Apps environment:

```sh
az containerapp env create --name $ENV_NAME --resource-group $RG --location $LOCATION
```

Verify container app environment ID:

```sh
ENV_ID=$(az containerapp env show --name $ENV_NAME --resource-group $RG --query id -o tsv)
```

Get container app environment domain:

```sh
ENV_DOMAIN=$(az containerapp env show --name $ENV_NAME --resource-group $RG --query "properties.defaultDomain" --output tsv)
```

## 5. Agent 365 CLI

```sh
MESSAGING_ENDPOINT="https://$APP_NAME.$ENV_DOMAIN/api/messages"
a365 setup all --aiteammate -n $AGENT_NAME --messaging-endpoint $MESSAGING_ENDPOINT
```

## 6. Deploy container app

Add agent blueprint secret

```sh
az containerapp secret set \
  --name <YOUR_CONTAINER_APP_NAME> \
  --resource-group <YOUR_RESOURCE_GROUP> \
  --secrets "my-db-password=YourSuperSecretValue123"
```

```sh

```
