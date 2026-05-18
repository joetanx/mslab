## 1. Setup [Agent 365 CLI](https://learn.microsoft.com/en-us/microsoft-agent-365/developer/agent-365-cli)

The Agent 365 CLI is a cross-platform tool that works on Windows, Linux and macOS with .NET 8.0 or later

### 1.1. Install .NET and Azure CLI (Windows example)

```cmd
winget install Microsoft.DotNet.SDK.10 Microsoft.AzureCLI
```

![](https://github.com/user-attachments/assets/b66cd69b-ea71-4ab6-9312-15997835aeb1)

![](https://github.com/user-attachments/assets/328139da-c5d6-4f05-9b06-e8680765678b)

### 1.2. Install Agent 365 CLI

```cmd
dotnet tool install --global Microsoft.Agents.A365.DevTools.Cli
```
![](https://github.com/user-attachments/assets/7d869db6-b083-416c-ae2a-5dad9a31b6e4)

![](https://github.com/user-attachments/assets/8709ae0d-2026-4c87-aaf5-3897b0b3020a)

## 2. Register agent with Agent 365 CLI

To setup an agent in Agent 365, run `a365 setup all --agent-name <agent-name>`

Agent 365 CLI automatically detects the tenant ID from Azure CLI

> [!Note]
>
> It was originally possible to initialize the a365 configuration file with `a365 config init`, but the `config` option appears to have been [removed](https://github.com/microsoft/Agent365-devTools/issues/370#issuecomment-4331725685)

![](https://github.com/user-attachments/assets/2bb1eacc-f7a1-4708-b5ad-6fab30816507)

Alternatively, use the `--tenant-id <tenant-id>` to skip auto detection

Running a365 in Windows automatically opens the Windows Account Manager (other platforms open browser)

![](https://github.com/user-attachments/assets/da04fd08-770f-4919-8e81-47917e514e0e)

```cmd

```

```cmd

```
