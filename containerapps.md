## Azure Container Apps Walkthrough: Vanilla vs Dockerfile Deployment

### 0.1. Example whoami app.py

```python
from aiohttp import web
import json

async def whoami(request: web.Request) -> web.Response:
    data = {
        "method": request.method,
        "path": str(request.rel_url),
        "remote": request.remote,
        "headers": dict(request.headers),
        "query": dict(request.rel_url.query),
    }
    return web.Response(
        text=json.dumps(data, indent=2),
        content_type="application/json",
    )

app = web.Application()
app.router.add_route("*", "/whoami", whoami)

if __name__ == "__main__":
    web.run_app(app, host="0.0.0.0", port=8080)
```

### 0.2. Common Setup

```sh
RG="rg-myapp"
LOCATION="eastus"
ENV_NAME="cae-myapp"
APP_NAME="myapp"

az group create --name $RG --location $LOCATION
```

> [!Note]
>
> The `app.py` must bind aiohttp to `0.0.0.0`, not `127.0.0.1`, for container networking to work:
>
> ```python
> web.run_app(app, host="0.0.0.0", port=8080)
> ```

## 1. Method 1: Vanilla `python:alpine` + Azure Files Mount

### 1.1. Create Resources

```sh
SA_NAME="samyapp$RANDOM"
SHARE_NAME="appcode"

# Storage account + file share
az storage account create \
  --name $SA_NAME --resource-group $RG \
  --location $LOCATION --sku Standard_LRS

CONN_STR=$(az storage account show-connection-string \
  --name $SA_NAME --resource-group $RG \
  --query connectionString -o tsv)

az storage share create --name $SHARE_NAME --connection-string "$CONN_STR"

# Upload app files
az storage file upload --share-name $SHARE_NAME \
  --source requirements.txt --connection-string "$CONN_STR"
az storage file upload --share-name $SHARE_NAME \
  --source app.py --connection-string "$CONN_STR"

# Container Apps environment
az containerapp env create \
  --name $ENV_NAME --resource-group $RG --location $LOCATION

# Register Azure Files storage in the environment
SA_KEY=$(az storage account keys list \
  --name $SA_NAME --resource-group $RG \
  --query "[0].value" -o tsv)

az containerapp env storage set \
  --name $ENV_NAME --resource-group $RG \
  --storage-name appcode \
  --azure-file-account-name $SA_NAME \
  --azure-file-account-key "$SA_KEY" \
  --azure-file-share-name $SHARE_NAME \
  --access-mode ReadOnly
```

### 1.2. Deploy Container App

Volume mounts cannot be expressed as inline CLI flags, both methods below use a YAML manifest. The difference is where that manifest lives.

#### 1.2.1. Option 1: az CLI (deploy from YAML file)

```sh
# Inject the real environment resource ID first
ENV_ID=$(az containerapp env show \
  --name $ENV_NAME --resource-group $RG --query id -o tsv)

az containerapp create \
  --name $APP_NAME \
  --resource-group $RG \
  --yaml containerapp-vanilla.yaml
```

#### 1.2.2. Option 2: YAML Manifest - `containerapp-vanilla.yaml`

```yaml
location: eastus
resourceGroup: rg-myapp
name: myapp
properties:
  managedEnvironmentId: /subscriptions/<SUBSCRIPTION_ID>/resourceGroups/rg-myapp/providers/Microsoft.App/managedEnvironments/cae-myapp
  configuration:
    ingress:
      external: true
      targetPort: 8080
      transport: auto
  template:
    volumes:
      - name: appcode-vol
        storageType: AzureFile
        storageName: appcode        # must match the name used in env storage set
    containers:
      - name: myapp
        image: python:alpine
        command:
          - /bin/sh
          - "-c"
          - "pip install --no-cache-dir -r /app/requirements.txt && python /app/app.py"
        volumeMounts:
          - volumeName: appcode-vol
            mountPath: /app
        resources:
          cpu: 0.5
          memory: 1Gi
    scale:
      minReplicas: 1
      maxReplicas: 3
```

> [!Tip]
>
> The `pip install` runs at every cold start. For anything beyond a quick prototype, method 2 below is preferable.

## 2. Method 2: Dockerfile + ACR

### 2.1. Dockerfile

```dockerfile
FROM python:alpine
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
EXPOSE 8080
CMD ["python", "app.py"]
```

### 2.2. Create Resources

```sh
ACR_NAME="acrmyapp$RANDOM"

# ACR
az acr create \
  --name $ACR_NAME --resource-group $RG \
  --location $LOCATION --sku Basic

# Build image directly in ACR (no local Docker needed)
az acr build \
  --registry $ACR_NAME \
  --image myapp:latest \
  --file Dockerfile .

# Container Apps environment (skip if already created above)
az containerapp env create \
  --name $ENV_NAME --resource-group $RG --location $LOCATION
```

### 2.3. Deploy Container App

#### 2.3.1. Option 1: az CLI

```sh
ACR_SERVER="$ACR_NAME.azurecr.io"

az containerapp create \
  --name $APP_NAME \
  --resource-group $RG \
  --environment $ENV_NAME \
  --image "$ACR_SERVER/myapp:latest" \
  --registry-server $ACR_SERVER \
  --registry-identity system \       # creates system MI + assigns AcrPull automatically
  --target-port 8080 \
  --ingress external \
  --min-replicas 1 \
  --max-replicas 3 \
  --cpu 0.5 --memory 1Gi
```

> [!Tip]
>
> `--registry-identity system` requires **Owner** or **User Access Administrator** on the subscription so Azure can assign the `AcrPull` role to the container app's managed identity. Otherwise, enable ACR admin instead:
>
> ```sh
> az acr update --name $ACR_NAME --admin-enabled true
> # then replace --registry-identity with:
> --registry-username $(az acr credential show --name $ACR_NAME --query username -o tsv) \
> --registry-password $(az acr credential show --name $ACR_NAME --query "passwords[0].value" -o tsv)
> ```

#### 2.3.2. Option 2: YAML Manifest - `containerapp-dockerfile.yaml`

```yaml
location: eastus
resourceGroup: rg-myapp
name: myapp
identity:
  type: SystemAssigned
properties:
  managedEnvironmentId: /subscriptions/<SUBSCRIPTION_ID>/resourceGroups/rg-myapp/providers/Microsoft.App/managedEnvironments/cae-myapp
  configuration:
    registries:
      - server: <ACR_NAME>.azurecr.io
        identity: system              # uses the SystemAssigned identity above
    ingress:
      external: true
      targetPort: 8080
      transport: auto
  template:
    containers:
      - name: myapp
        image: <ACR_NAME>.azurecr.io/myapp:latest
        resources:
          cpu: 0.5
          memory: 1Gi
    scale:
      minReplicas: 1
      maxReplicas: 3
```

Deploy via CLI:
```sh
az containerapp create \
  --name $APP_NAME \
  --resource-group $RG \
  --yaml containerapp-dockerfile.yaml
```

## 3. Get Container Apps application URL

```sh
az containerapp show \
  --name $APP_NAME \
  --resource-group $RG \
  --query properties.configuration.ingress.fqdn \
  -o tsv
```

Prefix with `https://`, ingress is always TLS on Container Apps.

Or inline to `curl` immediately:

```sh
URL=$(az containerapp show \
  --name $APP_NAME --resource-group $RG \
  --query properties.configuration.ingress.fqdn -o tsv)

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
