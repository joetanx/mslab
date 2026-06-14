## 1. Function app

### 1.1. Create function app

Select `App Service` hosting plan:

![](https://github.com/user-attachments/assets/b27ee6b1-a91f-46ab-89f5-8e8c735abba5)

Operating System: `Linux`

Runtime stack: `Python`

![](https://github.com/user-attachments/assets/aeef9c78-48b0-4bfe-bf6f-3c1785d04fe4)

Configure VNet integration for private access from function to database:

![](https://github.com/user-attachments/assets/f1db2163-3531-46a6-a9b4-2a89cf83a7f8)

Enable system-assigned managed identity - the agent code uses this MI to authenticate to Foundry and databasee

![](https://github.com/user-attachments/assets/0a6800b0-d1b0-412b-98a2-861d3028ee19)

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

#### 2.3.1. Login to `postgres` database as admin

[Install Azure CLI](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli) and `az login` 

Get access token:

```
az account get-access-token --resource https://ossrdbms-aad.database.windows.net --query accessToken --output tsv
```

Connect to `postgres` database and pass `access_token` value as password:

```
psql -h agentrun.postgres.database.azure.com -p 5432 -U admin@MngEnvMCAP398230.onmicrosoft.com postgres
```

#### 2.3.2. Create PostgreSQL role for function MI

```sql
SELECT * FROM pgaadauth_create_principal('agentrun', false, false);
```

> [!Tip]
>
> The three arguments are: (`role_name`, `is_admin`, `can_create_roles`)
> 
> The role name is the display name of the function (e.g. `agentrun`)

#### 2.3.3. Create database

```sql
CREATE DATABASE teams_bot;
```

Allow the identity to connect to the new database:

```sql
GRANT CONNECT ON DATABASE teams_bot TO "agentrun";
```

#### 2.3.4. Connect to database and grant schema-level permissions to function MI

```sql
\c teams_bot
```

Allow the identity to use the public schema and create the checkpointer tables (`checkpoints`, `checkpoint_blobs`, `checkpoint_writes`, `checkpoint_migrations`) that `AsyncPostgresSaver.setup()` creates:

```sql
GRANT USAGE, CREATE ON SCHEMA public TO "agentrun";
```

Ensure the identity gets permissions on sequences and tables created in the future:

```sql
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO "agentrun";
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO "agentrun";
```

### 2.4. Test function MI login

Function defines `IDENTITY_ENDPOINT` and `IDENTITY_HEADER` environment variables for the app to connect to the [endpoint](https://learn.microsoft.com/en-us/azure/app-service/overview-managed-identity#rest-endpoint-reference)

```
curl "$IDENTITY_ENDPOINT?api-version=2019-08-01&resource=https://ossrdbms-aad.database.windows.net" -H "X-Identity-Header: $IDENTITY_HEADER"
```

Connect to database and pass token value as password:

```
apt update && apt -y install postgresql-client
psql -h agentrun.postgres.database.azure.com -p 5432 -U agentrun postgres
```
