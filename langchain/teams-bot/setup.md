## 1. Function app

### 1.1. Create user-assigned managed identity

The agent code uses UAMI to authenticate to Foundry and PostgreSQL, and as federated identity credential (FIC) to the teams bot app

![](https://github.com/user-attachments/assets/d93bf613-5baa-44cb-aeb7-edca90c18380)

### 1.2. Create function app

Select `App Service` hosting plan:

![](https://github.com/user-attachments/assets/b27ee6b1-a91f-46ab-89f5-8e8c735abba5)

Operating System: `Linux`

Runtime stack: `Python`

![](https://github.com/user-attachments/assets/aeef9c78-48b0-4bfe-bf6f-3c1785d04fe4)

Configure VNet integration for private access from function to database:

![](https://github.com/user-attachments/assets/f1db2163-3531-46a6-a9b4-2a89cf83a7f8)

Select managed identity authentication type and the UAMI

![](https://github.com/user-attachments/assets/4229daad-378a-43a1-a870-daa5fc488725)

### 1.3. Storage account permissions

Assign the follow storage roles to the UAMI:
1. Storage Blob Data Owner
2. Storage Queue Data Contributor
3. Storage Table Data Contributor

![](https://github.com/user-attachments/assets/3b512c25-34c0-478f-8a6f-05d19e35f84c)

### 1.4. Setup function app

> [!Tip]
>
> It is also possible to use VS Code to deploy all files and let Kudo handle the deployment
>
> But it's simpler to just use manual setup and the Azure code editor for demo

SSH to the function app container: Development Tools → SSH

![](https://github.com/user-attachments/assets/e9fdbb4a-e5f2-47c9-8ae5-8adc39ba766b)

```sh
touch /home/site/wwwroot/{agent.py,bot.py,function_app.py,requirements.txt}
```

Paste in the function code: Functions → App files → select each file iteratively → paste content of respective files

Install dependent packages at `/home/site/wwwroot/.python_packages/lib/site-packages` (which persists container restarts)

```sh
pip install -r /home/site/wwwroot/requirements.txt --target /home/site/wwwroot/.python_packages/lib/site-packages
```

<details><summary>work in progress</summary>

> [!Warning]
>
> Review the code before deploying - the code provides functional agent setup, but it doesn't have production-ready practices like error handling

![](https://github.com/user-attachments/assets/db216953-1bfb-44ad-95ec-e6a391a2dd8c)

Populate the following environment variables:
- `ASSIGNEE_IN_PROGRESS`
- `ASSIGNEE_RESOLVED`
- `ENTRA_AGENT_BLUEPRINT_ID`
- `ENTRA_AGENT_IDENTITY_ID`
- `ENTRA_AGENT_USER_ID`
- `ENTRA_TENANT_ID`
- `FOUNDRY_MODEL`
- `FOUNDRY_PROJECT_ENDPOINT`

> [!Tip]
>
> The environment variables can also be edited as json under `advanced edit`

![](https://github.com/user-attachments/assets/c7f0cfa1-080f-43e6-b0e6-bd8ea2b70e22)

</details>

## 2. Azure database for PostgreSQL flexible server

### 2.1. Create delegated subnet for database

> [Network with private access (virtual network integration) for Azure Database for PostgreSQL](https://learn.microsoft.com/en-us/azure/postgresql/network/concepts-networking-private)
> 
> The smallest CIDR range you can specify for the subnet is /28, which provides 16 IP addresses.

![](https://github.com/user-attachments/assets/981fa1f5-f1db-4fa7-8243-fb6e6fa0697c)

### 2.2. Create azure database service

Customize the desire sizing and resiliency:

![](https://github.com/user-attachments/assets/26067ce4-3ab5-4b9f-bcf3-a55cf2a1e5ad)

Select Entra authentication:

> The function will use MI to connect to database

![](https://github.com/user-attachments/assets/b564a1f0-3ed0-4913-b7ae-0313baf594ec)

Select the subnet created earlier:

> This subnet will be delegated for use only with PostgreSQL Flexible Server (`Microsoft.DBforPostgreSQL/flexibleServers`).

![](https://github.com/user-attachments/assets/9efd1b95-63b6-434e-9d21-798264cf1c2d)

### 2.3. Create database and grant access to function MI

Connecting to the database - example connection commands are provide under Settings → Connect:

![](https://github.com/user-attachments/assets/8031caf6-c225-4580-9b4b-d2f5b776d6ee)

[Install Azure CLI](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli) and `az login` 

Get access token:

```
az account get-access-token --resource https://ossrdbms-aad.database.windows.net --query accessToken --output tsv
```

Connect to `postgres` database and pass `access_token` value as password:

```
psql -h agentrun.postgres.database.azure.com -p 5432 -U admin@MngEnvMCAP398230.onmicrosoft.com postgres
```

[Create PostgreSQL role](https://learn.microsoft.com/en-us/azure/postgresql/security/security-connect-with-managed-identity#create-an-azure-database-for-postgresql--user-for-your-managed-identity):

```sql
SELECT * FROM pgaadauth_create_principal('agentrun', false, false);
```

Create database and grant permissions to function MI:

```sql
-- Create the database
CREATE DATABASE teams_bot;

-- Switch to the newly created database
\c teams_bot

-- Allow function MI to connect to database
GRANT CONNECT ON DATABASE teams_bot TO agentrun;

-- Allow function MI to use the public schema and create the checkpointer tables (`checkpoints`, `checkpoint_blobs`, `checkpoint_writes`, `checkpoint_migrations`) that `AsyncPostgresSaver.setup()` creates

GRANT USAGE, CREATE ON SCHEMA public TO agentrun;

-- Grant only data modification permissions on existing objects
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO agentrun;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO agentrun;

-- Ensure future objects inherit these restricted permissions
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO agentrun;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO agentrun;
```

#### 2.3.1. Changing MI

In event that the MI is changed, the object ID needs to be updated

##### Dropping existing role and recreate

Repeat both `REASSIGN` and `DROP` commands on both `\c postgres` and `\c teams_bot`

```sql
-- Reassign owned objects to a safe role (e.g., your admin)
REASSIGN OWNED BY agentrun TO "admin@MngEnvMCAP398230.onmicrosoft.com";

-- Drop all privileges held by the role
DROP OWNED BY agentrun;
```

Then drop the role:

```sql
DROP ROLE agentrun;
```

##### Or just change the oid security label

```sql
SECURITY LABEL FOR pgaadauth ON ROLE agentrun IS 'aadauth,oid=48d6b874-c66a-47ab-9126-d6b1452f7325,type=service';
```

Then check the updated label:

```sql
SELECT * FROM pg_shseclabel WHERE objoid = (SELECT oid FROM pg_roles WHERE rolname = 'agentrun');
```


### 2.4. Test function MI login

Function defines `IDENTITY_ENDPOINT` and `IDENTITY_HEADER` environment variables for the app to connect to the [endpoint](https://learn.microsoft.com/en-us/azure/app-service/overview-managed-identity#rest-endpoint-reference)

```
curl "$IDENTITY_ENDPOINT?api-version=2019-08-01&resource=https://ossrdbms-aad.database.windows.net&client_id=43d9eeee-5654-433c-b428-6cdf12e8b4d9" -H "X-Identity-Header: $IDENTITY_HEADER"
```

Connect to database and pass token value as password:

```
apt update && apt -y install postgresql-client
psql -h agentrun.postgres.database.azure.com -p 5432 -U agentrun teams_bot
```

## 3. Foundry

Get the foundry project endpoint:

![](https://github.com/user-attachments/assets/21ae86ca-30e3-4953-8432-a7b10983013e)

Get the name of the deployment to be used:

![](https://github.com/user-attachments/assets/5586e5ae-f475-4edd-92f6-2885c9b9a396)

Give `Cognitive Services User` permission to function MI:

> Notice that recently created MIs has agent 365 logo

![](https://github.com/user-attachments/assets/9f5f1393-ddb9-430c-b7a4-38ceca746f8c)

## 4. Teams app

### 4.1. Enable sideloading in Teams

Teams CLI requires sideloading to be enabled in the policy applied to the sign-in user:

![](https://github.com/user-attachments/assets/880c15db-a16e-4c16-a609-e6a166df1c18)

Teams Admin Center → Users → Find the user → Policies → App setup policy → "Upload custom apps"

![](https://github.com/user-attachments/assets/ed911e99-d387-4666-9783-ab405b1b181c)

![](https://github.com/user-attachments/assets/707dc008-28bd-4306-906d-15819bda4c4c)

### 4.2. Install [Teams CLI v3](https://microsoft.github.io/teams-sdk/cli/)

```cmd
winget install -e --id OpenJS.NodeJS.LTS
npm install -g @microsoft/teams.cli
```

The Teams CLI v3 includes options like [login](https://microsoft.github.io/teams-sdk/cli/commands/login/), [status](https://microsoft.github.io/teams-sdk/cli/commands/status/) and [app create](https://microsoft.github.io/teams-sdk/cli/commands/app/create)

![](https://github.com/user-attachments/assets/c09756b1-172c-45ad-aa44-3503585f1261)

### 4.3. Login

```cmd
teams login
```

![](https://github.com/user-attachments/assets/419ac5b7-25be-4192-aad5-9879b07146ae)

![](https://github.com/user-attachments/assets/6d228f2e-db3e-4b49-918e-ca6950b5aaae)

```cmd
teams status
```

![](https://github.com/user-attachments/assets/90eef191-b96e-462c-a240-38be714857a0)

### 4.4. Create Teams app

Use `teams app create` to create the Teams app (add `--no-secret` to skip client secret creation)

```cmd
teams app create --name "LangChain Agent" --endpoint https://agentrun.azurewebsites.net/api/messages
```

![](https://github.com/user-attachments/assets/a72726dd-527f-409d-ba5d-808d1cb10f67)

The `teams app create` command creates a Teams app, a Teams-managed bot and an Entra ID app registration

Verify the Teams resources created on Teams developer portal: https://dev.teams.microsoft.com/

![](https://github.com/user-attachments/assets/aa018c89-a02e-4bea-a993-b10074917544)

![](https://github.com/user-attachments/assets/54ec7198-559e-4ab7-8db1-65bd4283cc98)

### 4.5. Setup federated identity credential to LangChain Agent app registration

The Teams CLI created a client secret for the app, which can be discarded since FIC is used

![](https://github.com/user-attachments/assets/5f0ab5ce-58b6-4fab-9540-1d6e0f285ae1)

![](https://github.com/user-attachments/assets/6e4fdb54-d857-495e-b17b-6f78542b3412)

### 4.6. Open app in teams

Get the app install link:

```cmd
teams app get <APP_ID> --install-link
```

Or select `Preview in Teams` at Teams Developer Portal (https://dev.teams.microsoft.com)

![](https://github.com/user-attachments/assets/cca9f306-a13d-4005-ad5d-61a964e2ca15)

![](https://github.com/user-attachments/assets/6f0c1d8a-526d-40c4-8544-37ebd4c423cc)

#### Optionally, publish the app for all users

![](https://github.com/user-attachments/assets/17d14776-9506-4526-b72a-6c3dc2124641)

![](https://github.com/user-attachments/assets/2f1eb494-cb73-4e83-a738-a51982b80691)

![](https://github.com/user-attachments/assets/1149e7d9-35f4-49f9-a37f-218f0eae8ccb)
