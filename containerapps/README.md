## Azure Container Apps Walkthrough: Vanilla vs Dockerfile Deployment

Prepare variables and create resource group (common step for both methods):

```sh
LOCATION='southeastasia'
APP_NAME='myapp'
RG="rg-$APP_NAME"
ENV_NAME="cae-$APP_NAME"
SUBSCRIPTION_ID='<subscription-id>'

az account set --subscription $SUBSCRIPTION_ID
az group create --name $RG --location $LOCATION
```

Create Container Apps environment:

```sh
az containerapp env create --name $ENV_NAME --resource-group $RG --location $LOCATION
```

Verify container app environment ID:

```sh
CAE_ID=$(az containerapp env show --name $ENV_NAME --resource-group $RG --query id -o tsv)
```

## 1. Method 1: Vanilla `python:alpine` + Azure Files mount

### 1.1. Setup storage account

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
for FILE in requirements.txt app.py; do
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

### 1.2. Deploy Container App (YAML manifest only)

> [!Note]
>
> Volume mounts cannot be expressed as inline `az containerapps create` CLI flags

Download [manifest-vanilla.yaml](manifest-vanilla.yaml) and replace variables:

```sh
curl -sLO https://github.com/joetanx/mslab/raw/refs/heads/main/containerapps/manifest-vanilla.yaml
sed -i "s/<LOCATION>/$LOCATION/" manifest-vanilla.yaml
sed -i "s/<APP_NAME>/$APP_NAME/" manifest-vanilla.yaml
sed -i "s/<RG>/$RG/" manifest-vanilla.yaml
sed -i "s/<CAE_ID>/$CAE_ID/" manifest-vanilla.yaml
sed -i "s/<SHARE_NAME>/$SHARE_NAME/" manifest-vanilla.yaml
```

Deploy container app with edited manifest file:

```sh
az containerapp create --name $APP_NAME --resource-group $RG --yaml manifest-vanilla.yaml
```

> [!Tip]
>
> The `pip install` runs at every cold start. For anything beyond a quick prototype, method 2 below is preferable.

## 2. Method 2: Build image with dependencies and code into Auzre Container Registry (ACR)

> [!Note]
>
> The subscription needs to be registered for `Microsoft.ContainerRegistry`

> ```sh
> az provider register --namespace Microsoft.ContainerRegistry
> az provider show --namespace Microsoft.ContainerRegistry --query "registrationState"
> ```

### 2.1. Setup container registry

Download app files:

```sh
curl -sLO https://github.com/joetanx/mslab/raw/refs/heads/main/containerapps/requirements.txt
curl -sLO https://github.com/joetanx/mslab/raw/refs/heads/main/containerapps/app.py
curl -sLO https://github.com/joetanx/mslab/raw/refs/heads/main/containerapps/Dockerfile
```

Create ACR (ACR name cannot contain dashes):

```sh
ACR_NAME="acr$APP_NAME$RANDOM"
az acr create --name $ACR_NAME --resource-group $RG --location $LOCATION --sku Basic --tags SecurityControl=Ignore
```

Build image directly in ACR (no local Docker needed):

```sh
az acr build --registry $ACR_NAME --image $APP_NAME:latest --file Dockerfile .
```

### 2.2. Deploy Container App

#### 2.2.1. Option 1: az CLI

```sh
ACR_SERVER="$ACR_NAME.azurecr.io"
az containerapp create \
  --name $APP_NAME --resource-group $RG --environment $ENV_NAME --image "$ACR_SERVER/myapp:latest" --registry-server $ACR_SERVER \
  --registry-identity system --target-port 8080 --ingress external --min-replicas 1 --max-replicas 1 --cpu 0.5 --memory 1Gi
```

> [!Tip]
>
> `-registry-identity system` creates system MI + assigns AcrPull automatically
>
> This requires **Owner** or **User Access Administrator** on the subscription so Azure can assign the `AcrPull` role to the container app's managed identity.
> 
> Otherwise, enable ACR admin instead:
>
> ```sh
> az acr update --name $ACR_NAME --admin-enabled true
> # then replace --registry-identity with:
> --registry-username $(az acr credential show --name $ACR_NAME --query username -o tsv) \
> --registry-password $(az acr credential show --name $ACR_NAME --query "passwords[0].value" -o tsv)
> ```

#### 2.2.2. Option 2: YAML Manifest

Download [manifest-dockerfile.yaml](manifest-dockerfile.yaml) and replace variables:

```sh
curl -sLO https://github.com/joetanx/mslab/raw/refs/heads/main/containerapps/manifest-dockerfile.yaml
sed -i "s/<LOCATION>/$LOCATION/" manifest-dockerfile.yaml
sed -i "s/<APP_NAME>/$APP_NAME/" manifest-dockerfile.yaml
sed -i "s/<RG>/$RG/" manifest-dockerfile.yaml
sed -i "s|<CAE_ID>|$CAE_ID|" manifest-dockerfile.yaml
sed -i "s/<ACR_NAME>/$ACR_NAME/" manifest-dockerfile.yaml
```

Deploy container app with edited manifest file:

```sh
az containerapp create --name $APP_NAME --resource-group $RG --yaml manifest-dockerfile.yaml
```

> [!Important]
>
> Creation by yaml manifest doesn't assign `AcrPull` to the container app managed identity for some reason:
>
> ```sh
> # 1. Get the Principal ID of the Container App identity
> ACA_MI_ID=$(az containerapp show --name $APP_NAME --resource-group $RG --query "identity.principalId" -o tsv)
> 
> # 2. Get the Scope ID of your ACR
> ACR_ID=$(az acr show --name $ACR_NAME --query id -o tsv)
> 
> # 3. Grant AcrPull role
> az role assignment create --assignee $ACA_MI_ID --role AcrPull --scope $ACR_ID
> ```

## 3. Get Container Apps application URL

```sh
az containerapp show --name $APP_NAME --resource-group $RG --query properties.configuration.ingress.fqdn -o tsv
```

Prefix with `https://`, ingress is always TLS on Container Apps.

Or inline to `curl` immediately:

```sh
URL=$(az containerapp show --name $APP_NAME --resource-group $RG --query properties.configuration.ingress.fqdn -o tsv)
curl "https://$URL/whoami"
```

## 4. Quick Comparison

| | Vanilla | Dockerfile |
|---|---|---|
| Image | `python:alpine` (Docker Hub) | Custom image in ACR |
| App files | Azure Files mount | Baked into image |
| Cold start | Slower (`pip install` runs each time) | Fast (deps pre-installed) |
| Update files | Re-upload to file share, restart | Rebuild & push new image tag |
| ACR required | No | Yes |
| Best for | Rapid iteration / hot-reload dev | Production workloads |
