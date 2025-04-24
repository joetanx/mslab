## 1. Provision Sentinel workspace

### 1.1. Create log analytics workspace

![image](https://github.com/user-attachments/assets/d20053d3-1df5-4d36-8708-8d24d0c85413)

### 1.2. Add Sentinel to the LAW

![image](https://github.com/user-attachments/assets/51efe87f-8d9f-457c-8708-8161433bea98)

## 2. Essential Sentinel solutions

Install Sentinel solutions: left pane → Content management → Content hub

|Solution||
|---|---|
|Azure Activity|![image](https://github.com/user-attachments/assets/99e6037d-333b-4fec-a922-3a07b95c61ed)|
|Defender for Cloud|![image](https://github.com/user-attachments/assets/4bc10fbc-d5d6-4317-a109-7d7378812666)|
|Defender XDR|![image](https://github.com/user-attachments/assets/f123a955-101f-4d14-aadd-34e7e2d2239d)|
|Entra ID|![image](https://github.com/user-attachments/assets/fc995dd9-d871-475c-91a0-caca361e8f8b)|
|Security Threat Essentials|![image](https://github.com/user-attachments/assets/7eac5d1d-bc1c-4ca7-b39d-912628931882)|
|Sentinel SOAR Essentials|![image](https://github.com/user-attachments/assets/b5a7a767-2e4b-455c-b3ec-c2bf12f1c12f)|
|SOC Handbook|![image](https://github.com/user-attachments/assets/59fc8045-016f-49a5-aad8-1df0ffdd4d37)|
|Threat Intelligence|![image](https://github.com/user-attachments/assets/b394e52b-4575-46b3-9e1e-0ae9c9b2b63b)|
|UEBA Essentials|![image](https://github.com/user-attachments/assets/5e7f8d8f-91f3-4e40-89d7-ff465118eaa8)|
|VirusTotal|![image](https://github.com/user-attachments/assets/f8d2c9df-5b44-4c6d-a877-22436eef4c04)|
|Windows Security Events|![image](https://github.com/user-attachments/assets/9550b6e4-9c57-4545-ba5b-b962e8be578c)|
|Windows Forwarded Events|![image](https://github.com/user-attachments/assets/fcd818b5-81bf-4574-bec9-3f5730be721c)|
|Common Event Format|![image](https://github.com/user-attachments/assets/07f07c70-6295-48cc-bbff-e53bacd2c3fe)|
|Syslog|![image](https://github.com/user-attachments/assets/c38e4bcc-a6b3-4845-876c-a54706a9fe26)|

## 3. Ingestion

Configure data connectors: left pane → Configuration → Data connectors → select the connector → Open connector page

> [!Tip]
>
> The connector `Status` changes to `Connected` after it's configured
>
> The `Last Log Received` timestamp and `Data received` timeline would show if there is actually data coming in

### 3.1. Windows Security Events via AMA

Ref: https://learn.microsoft.com/en-us/azure/sentinel/connect-services-windows-based

#### 3.1.1. Create data collection rule

![image](https://github.com/user-attachments/assets/21be0540-aa92-4b56-a2f6-bd5c1870375a)

Select the resources that the DCR will cover:

> [!Note]
>
> At the end of this process, the Azure Monitor Agent will be installed on any selected machines that don't already have it installed.

![image](https://github.com/user-attachments/assets/071299d0-7aec-44cb-8e9a-16369371e3f5)

Select events to stream:

![image](https://github.com/user-attachments/assets/ad95ea3c-979b-40e1-b1a1-f9c113efbd4b)

#### 3.1.2. Results

![image](https://github.com/user-attachments/assets/7b781b4a-c3aa-44ba-9550-487950600190)

![image](https://github.com/user-attachments/assets/c6c90c79-ab77-40f2-ae6b-1f1d08c2ca70)

### 3.2. Windows Forwarded Events

#### 3.2.1. Create data collection rule

![image](https://github.com/user-attachments/assets/df1df6d5-4402-4b9e-bd76-5c9a5f177f5a)

Select the Windows events collector:

![image](https://github.com/user-attachments/assets/4f769184-5ce8-42a6-88f8-c670aa0d4caa)

Select events to stream:

![image](https://github.com/user-attachments/assets/ef6aa4e4-6698-405a-bb15-c7728c1346cc)

#### 3.2.2. Results

![image](https://github.com/user-attachments/assets/bf248c7c-c156-40f5-9a23-6f19668aa22d)

### 3.3. Syslog via AMA

Ref: https://learn.microsoft.com/en-us/azure/sentinel/connect-cef-syslog-ama

#### 3.3.1. Install AMA on Linux machines

```sh
curl -sLO https://github.com/Azure/Azure-Sentinel/raw/refs/heads/master/DataConnectors/Syslog/Forwarder_AMA_installer.py
python Forwarder_AMA_installer.py
```

![image](https://github.com/user-attachments/assets/614fe767-496c-4672-b293-263fb4a6ed44)

![image](https://github.com/user-attachments/assets/971c3dc3-4b47-4109-8282-3c5c200184e2)

#### 3.3.2. Create data collection rule

![image](https://github.com/user-attachments/assets/b8606a91-edf4-4d62-ba3a-c4fe79389c98)

Select the resources that the DCR will cover:

![image](https://github.com/user-attachments/assets/a0add627-3894-4021-ad4f-865f4d1e8dd3)

Select log facilities and levels to collect:

![image](https://github.com/user-attachments/assets/323e51f5-1f75-401d-827a-654da2ed0420)

#### 3.3.3. Results

![image](https://github.com/user-attachments/assets/583e9915-a5de-47d7-aec8-e990a02750dd)

Check AMA status `systemctl status azuremonitor*`:

![image](https://github.com/user-attachments/assets/88b4eb63-62c2-416f-9169-57663bbed1f7)
