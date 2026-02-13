## 1. Create Foundry resource

![](https://github.com/user-attachments/assets/6c38fb19-1ad5-41c3-9941-2a27370c3a53)

> [!Note]
>
> The name of the Foundry resource must be globally unique, because it forms the domain name (`https://<az-openai-resource-name>.openai.azure.com`) for the resource endpoint
> 
> ![](https://github.com/user-attachments/assets/f3f6aac1-9357-48ff-a447-2b459ff30fc6)

![](https://github.com/user-attachments/assets/58659b2c-6c8f-482a-b7ca-659ec2430b3e)

![](https://github.com/user-attachments/assets/d131fbe9-6367-4f73-93a0-a6b3d9df16d5)

![](https://github.com/user-attachments/assets/1402ac55-6c30-45f1-9cb1-3611f6ea3111)

![](https://github.com/user-attachments/assets/d46a96ab-bcfc-4866-9a28-0a98e05ab536)

## 2. Retrieve Endpoint and Keys

The API key shown at [Foundry portal](https://ai.azure.com) is `KEY 1` of the Foundry resource:

![](https://github.com/user-attachments/assets/60a26bc9-d5b2-4342-b2d3-91ac49b48576)

To access `KEY 2` or regenerate the keys, go the the Foundry resource in [Azure portal](https://portal.azure.com)

![](https://github.com/user-attachments/assets/a3c442b6-c1ae-4d58-a2ae-eb4e0b78de1a)

## 3. Deploy a model

![](https://github.com/user-attachments/assets/07815cd1-9400-446a-8375-9cd83488417b)

![](https://github.com/user-attachments/assets/2e4812da-0d48-4a14-a705-4268888123f4)

> [!Note]
>
> Claude Sonnet is available on Foundry, but requires permission to purchase from Marketplace
> 
> ![](https://github.com/user-attachments/assets/818040dd-3e93-4bc1-947f-05ec1e6ed9e8)
>
> ![](https://github.com/user-attachments/assets/ce9bb327-2a81-4384-8c01-3800d5e90ac4)

> [!Note]
> 
> Registration is required for access to the `gpt-5-pro`, `gpt-5`, & `gpt-5-codex` models.
>
> `gpt-5-mini` , `gpt-5-nano`, and `gpt-5-chat` do not require registration.
>
> https://learn.microsoft.com/en-us/azure/ai-foundry/foundry-models/concepts/models-sold-directly-by-azure#gpt-5
> 
> ![](https://github.com/user-attachments/assets/50a8335b-607c-4167-ac4d-7eb49248fc23)

Deploy the model with default or custom settings:

![](https://github.com/user-attachments/assets/4f29af1d-024c-4cab-a9e3-19264a4507b0)

Custom enable settings adjustment before deploying:

![](https://github.com/user-attachments/assets/cfa5cccc-2517-4370-abd7-9930345c11ff)

Default setting just proceeds to deploy:

![](https://github.com/user-attachments/assets/76f36f37-9fca-4bab-a29f-1cc5caa2a024)

> [!Note]
>
> 1. Settings can still be changed under _Details_ after the model is deployed:
> 2. The _Key_ listed in the model _Details_ is `Key 1` of the Foundry resource
>
> ![](https://github.com/user-attachments/assets/c12cef21-5e6b-4294-9b6a-5ecbe248b006)
