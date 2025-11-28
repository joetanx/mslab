## 1. Create Foundry resource

![](https://github.com/user-attachments/assets/8b8ec791-8929-4630-b0e1-44f950dac70e)

> [!Note]
>
> The name of the Foundry resource must be globally unique, because it forms the domain name (`https://<az-openai-resource-name>.openai.azure.com`) for the resource endpoint
> 
> ![](https://github.com/user-attachments/assets/3998d6d9-33d8-4138-90c1-af14b100025b)

![](https://github.com/user-attachments/assets/62258918-b12d-430a-a7df-dc3b0ae69906)

![](https://github.com/user-attachments/assets/405637e1-1c34-4a80-a8f0-e854a9ae7451)

![](https://github.com/user-attachments/assets/a81a66e7-4ecb-47d9-8739-626d58262ff5)

![](https://github.com/user-attachments/assets/852d25e7-a462-454c-8a2b-507e80a534fa)

## 2. Retrieve Endpoint and Keys

The API key shown at [Foundry portal](https://ai.azure.com) is `KEY 1` for the Foundry resource:

![](https://github.com/user-attachments/assets/b9edc76b-d249-428e-ae35-a70efe2b124c)

To access `KEY 2` or regenerate the keys, go the the Foundry resource in [Azure portal](https://portal.azure.com)

![](https://github.com/user-attachments/assets/67bcaedc-a00c-44d3-8703-eed155a14973)

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
