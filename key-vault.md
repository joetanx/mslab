## 1. Create Azure key vault

![image](https://github.com/user-attachments/assets/e7cccf42-06a5-4f10-a917-9981d4685310)

![image](https://github.com/user-attachments/assets/95719382-f88b-479a-89d9-351d1c43df17)

> [!Important]
>
> Enabling public access allows access from any network, relying on RBAC to control access to the key vault
>
> Secure the key vault by disabling public access or allowing only selected networks
>
> When public access is disabled, access from a non-whitelisted network would return the warning below:
> 
> ![image](https://github.com/user-attachments/assets/93b4bf0d-6cd7-45dd-a3b3-87618e002eef)

![image](https://github.com/user-attachments/assets/f9a698d1-2742-4a50-95f5-31fa0835fe49)

## 2. Configure key vault administrator access

> [!Important]
>
> The creator of the key vault is the owner, but this doesn't grant permissions on key vault contents
>
> `Key Vault XXXX` roles are required to work on key vault contents
>
> https://learn.microsoft.com/en-us/azure/key-vault/general/rbac-guide#azure-built-in-roles-for-key-vault-data-plane-operations

**Key Vault Secrets Officer** role is sufficient to onboard and use secrets

![image](https://github.com/user-attachments/assets/319cb7b1-244b-45bb-b6d4-aca4a3b2ee79)

## 3. Onboard secrets

### 3.1. SSH private key for Linux VM

> [!Tip]
>
> The private key file needs to be uploaded via Azure CLI

```pwsh
system [ ~ ]$ vi id_ed25519
system [ ~ ]$ az keyvault secret set --name VMSSHPrvKey --vault-name VMCredsKV --file id_ed25519 --encoding ascii
{
  "attributes": {
    "created": "2025-04-22T05:26:11+00:00",
    "enabled": true,
    "expires": null,
    "notBefore": null,
    "recoverableDays": 90,
    "recoveryLevel": "Recoverable+Purgeable",
    "updated": "2025-04-22T05:26:11+00:00"
  },
  "contentType": null,
  "id": "https://vmcredskv.vault.azure.net/secrets/VMSSHPrvKey/899d5ca25a6145fcbedf5249bb06a31b",
  "kid": null,
  "managed": null,
  "name": "VMSSHPrvKey",
  "tags": {
    "file-encoding": "ascii"
  },
  "value": "-----BEGIN OPENSSH PRIVATE KEY-----\n<REDACTED>\n-----END OPENSSH PRIVATE KEY-----\n\n"
}
```

#### 3.1.1. Create SSH key so that it can be used to create VMs in the future

![image](https://github.com/user-attachments/assets/254f290e-da61-4b99-90ea-997bb679d651)

### 3.2. Windows password

![image](https://github.com/user-attachments/assets/ee1057dc-046a-4e7c-8658-623965c59286)

## 4. Bastion connection to VMs using key vault secrets

### 4.1. Linux

![image](https://github.com/user-attachments/assets/424e5678-7bfb-4b59-97d5-ec38ac367314)

### 4.2. Windows

![image](https://github.com/user-attachments/assets/1a1eb6eb-9403-4a27-9140-1d440a9d4144)
