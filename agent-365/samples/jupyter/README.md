# LangChain sandbox using Jupyter

```sh
az account set -s 27b58ab1-f52c-498e-a03d-255b76c80a00
export TENANT_ID='323626f5-1bfe-48cd-8902-ddfdfd44e1ce'
export LOCATION='eastus2'
export APP_NAME='jupyter'
export RG='rg-'$APP_NAME
az group create --name $RG --location $LOCATION
```

## 1. Foundry

```sh
FOUNDRY_NAME='foundry-'$APP_NAME
FOUNDRY_PROJECT='proj-'$APP_NAME
export FOUNDRY_MODEL='gpt-5.6-luna'
az cognitiveservices account create \
  --name $FOUNDRY_NAME --resource-group $RG --location $LOCATION --kind 'AIServices' \
  --sku 'S0' --allow-project-management 'true' --custom-domain $FOUNDRY_NAME --yes
az cognitiveservices account project create \
  --name $FOUNDRY_NAME --resource-group $RG --location $LOCATION \
  --project-name $FOUNDRY_PROJECT --display-name $FOUNDRY_PROJECT
MODEL_VERSION=$(az cognitiveservices model list --location $LOCATION --query "[?model.name=='${FOUNDRY_MODEL}'&&kind=='AIServices'].model.version" -o tsv)
az cognitiveservices account deployment create \
  --name $FOUNDRY_NAME --resource-group $RG --deployment-name $FOUNDRY_MODEL --model-name $FOUNDRY_MODEL \
  --model-version $MODEL_VERSION --model-format 'OpenAI' --sku-capacity 500 --sku 'GlobalStandard'
export FOUNDRY_PROJECT_ENDPOINT=$(az cognitiveservices account project show --name $FOUNDRY_NAME --resource-group $RG --project-name $FOUNDRY_PROJECT --query 'properties.endpoints' -o tsv)
```

## 2. Storage

```sh
SA_NAME='stor'$APP_NAME
az storage account create --name $SA_NAME --resource-group $RG --location $LOCATION --sku Standard_LRS --tags SecurityControl=Ignore
CONN_STR=$(az storage account show-connection-string -n $SA_NAME -g $RG --query connectionString -o tsv)
az storage share create -n $APP_NAME --connection-string "$CONN_STR"
az storage file upload -s $APP_NAME --source token_manager.py --connection-string $CONN_STR
az storage file upload -s $APP_NAME --source agent.py --connection-string $CONN_STR
az storage file upload -s $APP_NAME --source server.py --connection-string $CONN_STR
```

## 3. Virtual network

```sh
VNET_NAME='vnet-'$APP_NAME
SUBNET_NAME='snet-'$APP_NAME
az network vnet create -n $VNET_NAME -g $RG -l $LOCATION --address-prefixes 10.30.0.0/16
az network vnet subnet create -n $SUBNET_NAME -g $RG --vnet-name $VNET_NAME \
  --address-prefixes 10.30.0.0/24 --delegations Microsoft.App/environments
SUBNET_ID=$(az network vnet subnet show -n $SUBNET_NAME -g $RG --vnet-name $VNET_NAME --query id -o tsv)
```

## 4. Container app environment

```sh
CAE_NAME='cae-'$APP_NAME
WORKSPACE_ID=$(az monitor log-analytics workspace show -g delta-security-rg -n delta-soc \
  --subscription b70fcef1-9e03-4184-9321-4266c7b469ab --query customerId -o tsv)
WORKSPACE_KEY=$(az monitor log-analytics workspace get-shared-keys -g delta-security-rg -n delta-soc \
  --subscription b70fcef1-9e03-4184-9321-4266c7b469ab --query primarySharedKey -o tsv)
az containerapp env create -n $CAE_NAME -g $RG -l $LOCATION --infrastructure-subnet-resource-id $SUBNET_ID \
  --logs-destination log-analytics --logs-workspace-id $WORKSPACE_ID --logs-workspace-key $WORKSPACE_KEY
export CAE_ID=$(az containerapp env show --name $CAE_NAME --resource-group $RG --query id -o tsv)
CAE_DOMAIN=$(az containerapp env show --name $CAE_NAME --resource-group $RG --query "properties.defaultDomain" --output tsv)
SA_KEY=$(az storage account keys list -n $SA_NAME -g $RG --query "[0].value" -o tsv)
az containerapp env storage set -n $CAE_NAME -g $RG --storage-name $APP_NAME \
  -a $SA_NAME -k "$SA_KEY" -f $APP_NAME --access-mode ReadWrite
```

## 5. Container registry

```sh
export ACR_NAME='acr'$APP_NAME
az acr create -n $ACR_NAME -g $RG -l $LOCATION --sku Basic --tags SecurityControl=Ignore
az acr build -r $ACR_NAME -t $APP_NAME:latest -f Dockerfile .
```

## 6. User assigned managed identity

```sh
UAMI_NAME='uami-'$APP_NAME
az identity create -n $UAMI_NAME -g $RG
UAMI_ID=$(az identity show -n $UAMI_NAME -g $RG --query principalId -o tsv)
export UAMI_CLIENT_ID=$(az identity show -n $UAMI_NAME -g $RG --query clientId -o tsv)
export UAMI_RSC_ID=$(az identity show -n $UAMI_NAME -g $RG --query id -o tsv)
FOUNDRY_ID=$(az cognitiveservices account show -n $FOUNDRY_NAME -g $RG --query id -o tsv)
az role assignment create --assignee $UAMI_ID --role 'Cognitive Services User' --scope $FOUNDRY_ID
ACR_ID=$(az acr show -n $ACR_NAME --query id -o tsv)
az role assignment create --assignee $UAMI_ID --role AcrPull --scope $ACR_ID
export BLUEPRINT_CLIENT_ID=$(python3 -c "import json; print(json.load(open('a365.generated.config.json'))['agentBlueprintId'])")
az ad app federated-credential create --id $BLUEPRINT_CLIENT_ID \
  --parameters '{
    "name": "jupyter-uami-fic",
    "issuer": "https://login.microsoftonline.com/'"$TENANT_ID"'/v2.0",
    "subject": "'"$UAMI_ID"'",
    "audiences": ["api://AzureADTokenExchange"]
  }'
```

## 7. Deploy container app

```sh
export JUPYTER_PASSWORD_HASH='argon2:$argon2id$v=19$m=10240,t=10,p=8$OZ7KfLGUQwCLKZCmcNdp5g$nlYY6a3JTo1nuEM7ixchARxFb/gjMv58QfbkqrXME4c'
envsubst < containerapp.yaml > containerapp-edited.yaml
az containerapp create -n $APP_NAME -g $RG --yaml containerapp-edited.yaml
echo https://$APP_NAME.$CAE_DOMAIN/api/messages
```

## 8. Local testing

```sh
podman build -t jupyter:langchain .
podman run -d -p 80:8888 -v /opt/jupyter:/home/jovyan/work -e 'JUPYTER_PASSWORD_HASH=argon2:$argon2id$v=19$m=10240,t=10,p=8$OZ7KfLGUQwCLKZCmcNdp5g$nlYY6a3JTo1nuEM7ixchARxFb/gjMv58QfbkqrXME4c' --name jupyter localhost/jupyter:langchain
```
