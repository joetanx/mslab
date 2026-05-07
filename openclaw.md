## 0. Setup

### 0.1. Grant OpenClaw access to Foundry model

Add role assignment for `Cognitive Services User` to the Azure VM system managed identity:

![](https://github.com/user-attachments/assets/173738c1-ca77-4aa7-8b89-018fb3b78d70)

### 0.2. Setup Azure CLI

Install Azure CLI:

```sh
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash
```

Login to Azure VM with system managed identity:

```sh
az login --identity
```

Check account and subscription are currently set as the active context:

```sh
az account show
```

### 0.3. Install OpenClaw

```sh
curl -fsSL https://openclaw.ai/install.sh | bash
```

![](https://github.com/user-attachments/assets/b8108796-8f88-437e-9ffe-0b476d9d2f13)

> [!Tip] If the first setup was abort, setup can be rerun with:
> 
> ```sh
> openclaw onboard
> ```

Select `QuickStart` to use defaults:

![](https://github.com/user-attachments/assets/74c90a73-ed3e-4656-a199-8aa84ea71921)

### 0.4. Setup Microsoft Foundry model provider

![](https://github.com/user-attachments/assets/5753dddc-049f-49d4-abf4-5260e3c86750)

![](https://github.com/user-attachments/assets/5809e748-9bce-4bc9-844c-d35bd914e512)

![](https://github.com/user-attachments/assets/7ca529f1-97c8-493c-844c-7605b235986a)

![](https://github.com/user-attachments/assets/47f86230-e9a8-448b-a426-15619a16a94e)

![](https://github.com/user-attachments/assets/ee984f60-ce74-45ad-9461-4070d8d9bae1)
