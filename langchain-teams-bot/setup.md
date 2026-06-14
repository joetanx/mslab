## 1. Function app

### 1.1. Create function app

Select `App Service` hosting plan:

![](https://github.com/user-attachments/assets/b27ee6b1-a91f-46ab-89f5-8e8c735abba5)

Operating System: `Linux`

Runtime stack: `Python`

![](https://github.com/user-attachments/assets/aeef9c78-48b0-4bfe-bf6f-3c1785d04fe4)

Configure VNet integration for private access from function to database:

![]("https://github.com/user-attachments/assets/f1db2163-3531-46a6-a9b4-2a89cf83a7f8)

Enable system-assigned managed identity - the agent code uses this MI to authenticate to Foundry and databasee

![](https://github.com/user-attachments/assets/0a6800b0-d1b0-412b-98a2-861d3028ee19)

## 2. Azure database for PostgreSQL flexible server

### 2.1. Create delegated subnet for database

> [Network with private access (virtual network integration) for Azure Database for PostgreSQL](https://learn.microsoft.com/en-us/azure/postgresql/network/concepts-networking-private)
> 
> The smallest CIDR range you can specify for the subnet is /28, which provides 16 IP addresses.

<img width="1272" height="524" alt="image" src="https://github.com/user-attachments/assets/981fa1f5-f1db-4fa7-8243-fb6e6fa0697c" />

### 2.2. Create database

Customize the desire sizing and resiliency:

![](https://github.com/user-attachments/assets/26067ce4-3ab5-4b9f-bcf3-a55cf2a1e5ad)

Select Entra authentication:

> The function will use MI to connect to database

![](https://github.com/user-attachments/assets/b564a1f0-3ed0-4913-b7ae-0313baf594ec)

Select the subnet created earlier:

> This subnet will be delegated for use only with PostgreSQL Flexible Server (`Microsoft.DBforPostgreSQL/flexibleServers`).

![](https://github.com/user-attachments/assets/9efd1b95-63b6-434e-9d21-798264cf1c2d)
