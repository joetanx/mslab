Ref: https://learn.microsoft.com/en-us/intune/configmgr/protect/deploy-use/endpoint-protection-configure

## 1. Setup EPP site system role

https://learn.microsoft.com/en-us/intune/configmgr/protect/deploy-use/endpoint-protection-site-role

ConfigMgr console → Administration → Site Configuration → Servers and Site System roles

![](https://github.com/user-attachments/assets/3c36a1cb-2a8d-46e4-8b19-41a755d397da)

Configure site system settings:

![](https://github.com/user-attachments/assets/f54b785a-8740-4614-a0b3-d8801f3dddbc)

Configure proxy settings:

![](https://github.com/user-attachments/assets/82ac5522-6251-444e-b2b9-317547b0e584)

Configure endpoint protection point:

![](https://github.com/user-attachments/assets/c1a76015-bc73-4519-9e60-5d373f04253d)

![](https://github.com/user-attachments/assets/867dff26-9c27-4413-b269-42ad9d40cb55)

![](https://github.com/user-attachments/assets/26dd09f4-2458-446c-8c3e-946135a73e6b)

![](https://github.com/user-attachments/assets/3edd1d65-74aa-4d53-8560-e487ae2d785b)

![](https://github.com/user-attachments/assets/8cee221e-ffda-4cf6-968c-10c7c5898652)

![](https://github.com/user-attachments/assets/fbdf1191-3d38-4a0e-836e-fc6c7cb644ad)

### 1.1. Verify installation status

The ConfigMgr logs are at: `C:\Program Files\Microsoft Configuration Manager\Logs`

> [!Tip]
>
> The ConfigMgr trace tool at `C:\Program Files\Microsoft Configuration Manager\tools\cmtrace.exe` makes tracing ConfigMgr logs easier

Status of site system role installation: `EPSetup.log`:

![](https://github.com/user-attachments/assets/6ae604f3-19da-471a-94a5-bffa369085b3)

## 2. Configure alerts for endpoint protection

https://learn.microsoft.com/en-us/intune/configmgr/protect/deploy-use/endpoint-configure-alerts

ConfigMgr console → Assets and Compliance → Device Collections → Select device collection → Properties

![](https://github.com/user-attachments/assets/9b2c616d-9591-40bd-82f6-0d6228a7d6f9)

> [!Tip]
>
> Right-click and select Show Members to see the devices in the device collection
>
> ![](https://github.com/user-attachments/assets/69c596fd-a5cf-4dcb-be03-ad26090cc13a)
>
> ![](https://github.com/user-attachments/assets/b7cbbdce-05f9-477a-806a-5ac7c92ce4d6)

Alerts → Add...

![](https://github.com/user-attachments/assets/860a9443-fd81-4a88-a102-1ab1fcad16dc)

Select the desired events to alert for:

![](https://github.com/user-attachments/assets/12e74c9c-eae4-4993-a421-75955d96a106)

Configure the details for each alert:

|Alert|Details|
|---|---|
|Client check|![](https://github.com/user-attachments/assets/6f875826-500d-4422-a374-75836d1e16d9)|
|Client remediation|![](https://github.com/user-attachments/assets/19200db9-2c93-4820-969a-a3787aef807c)|
|Client activity|![](https://github.com/user-attachments/assets/f8cbd38f-d259-4344-af6d-b2be55c9ee53)|
|Malware detection|![](https://github.com/user-attachments/assets/0d77a9ad-3378-49e7-af07-7a41473659b3)|
|Malware outbreak|![](https://github.com/user-attachments/assets/7b62caf1-02a3-49d2-a8f1-a6314b2bb868)|
|Repeated malware detection|![](https://github.com/user-attachments/assets/37acf6e8-5c99-4c74-b45d-e9be71b58eb5)|
|Multiple malware detection|![](https://github.com/user-attachments/assets/fc6721bc-7004-4416-b902-b49f1fa86cf1)|
|Collection membership|![](https://github.com/user-attachments/assets/bc08005a-069a-44c8-8c73-c8c416b54688)|

## 3. Setup ConfigMgr to deliver definition updates

https://learn.microsoft.com/en-us/intune/configmgr/protect/deploy-use/endpoint-definitions-configmgr

ConfigMgr console → Administration → Site Configuration → Sites → Select site → Right-click → Configure Site Components → Software Update Point

![](https://github.com/user-attachments/assets/825a7332-e543-4ff2-bfbe-897068567961)

Classifications tab → Check "Definition Updates":

![](https://github.com/user-attachments/assets/b980fe6c-f0b2-41f7-a766-ff876fd30708)

Products tab → Check "System Center Endpoint Protection", "Microsoft Defender Antivirus" and "Microsoft Defender for Endpoint":

> [!Tip]
>
> "System Center Endpoint Protection" is under "Forefront" but not "System Center" because it was "Forefront Endpoint Protection" previously

![](https://github.com/user-attachments/assets/891a6f8d-e9d6-4ecd-ae74-2f7c1b83e56a)

![](https://github.com/user-attachments/assets/0b40566c-e99b-41c3-aeeb-1ea5ffadbba9)

## 4. Configure antimalware policies for endpoint protection

https://learn.microsoft.com/en-us/intune/configmgr/protect/deploy-use/endpoint-antimalware-policies

Antimalware policies specify how Endpoint Protection protects devices from malware and other threats

ConfigMgr console → Assets and Compliance → Endpoint Protection → Antimalware Policies

![](https://github.com/user-attachments/assets/09dfbad8-472f-47cd-a771-cae0174cc5d4)

Edit the Default Client Antimalware Policy or Create Antimalware Policy

> [!Tip]
>
> Create antimalware policies to control specific settings and deploy to specified device collections
>
> ![](https://github.com/user-attachments/assets/13ba085c-6b64-4a89-9ced-8a8916626d4b)
>
> ![](https://github.com/user-attachments/assets/d00f6c7b-79c9-4499-9342-c40a233d4d5c)
>
> ![](https://github.com/user-attachments/assets/691815a2-5c35-4740-a116-3c563ceca53e)

|Setting|Details|
|---|---|
|Scheduled scans|![](https://github.com/user-attachments/assets/27fa2386-5519-4b63-b663-af05bd0f227b)|
|Scan settings|![](https://github.com/user-attachments/assets/551566bf-8885-4b9d-8d69-cd235575525d)|
|Default actions|![](https://github.com/user-attachments/assets/15be32ef-d274-4542-bd10-1842bed38d9c)|
|Real-time protection|![](https://github.com/user-attachments/assets/567669af-ed89-4a41-8699-764f9d66a130)|
|Exclusion settings|![](https://github.com/user-attachments/assets/016c56b1-e07f-40e4-b8a2-93a257be0511)|
|Advanced|![](https://github.com/user-attachments/assets/221ab8e5-9ded-48a3-b075-4179fa851730)|
|Threat overrides|![](https://github.com/user-attachments/assets/76a99f81-4769-4cc4-9a86-57e580d6dad2)|
|Cloud Protection Service|![](https://github.com/user-attachments/assets/2263f52a-36f2-4b41-b453-0b7ca873aab3)|

### 4.1. Configure definition updates for endpoint protection

https://learn.microsoft.com/en-us/intune/configmgr/protect/deploy-use/endpoint-definition-updates

Security Intelligence updates → Set Source

> Definition updates was renamed to Security Intelligence updates from ConfigMgr 1902

![](https://github.com/user-attachments/assets/4d9aede9-40ef-43e7-a3c4-37a807275f5e)

![](https://github.com/user-attachments/assets/c294fe27-5c4f-4169-b3c9-d898b9297031)

|Setting|Description|
|---|---|
|[Updates distributed from Configuration Manager](https://learn.microsoft.com/en-us/intune/configmgr/protect/deploy-use/endpoint-definitions-configmgr)|This method uses Configuration Manager software updates to deliver definition and engine updates to computers in your hierarchy.|
|[Updates distributed from Windows Server Update Services (WSUS)](https://learn.microsoft.com/en-us/intune/configmgr/protect/deploy-use/endpoint-definitions-wsus)|This method uses your WSUS infrastructure to deliver definition and engine updates to computers.|
|[Updates distributed from Microsoft Update](https://learn.microsoft.com/en-us/intune/configmgr/protect/deploy-use/endpoint-definitions-microsoft-updates)|This method allows computers to connect directly to Microsoft Update in order to download definition and engine updates. This method can be useful for computers that are not often connected to the business network.|
|Updates distributed from Microsoft Malware Protection Center|This method will download definition updates from the Microsoft Malware Protection Center.|
|[Updates from UNC file shares](https://learn.microsoft.com/en-us/intune/configmgr/protect/deploy-use/endpoint-definitions-network)|With this method, you can save the latest definition and engine updates to a share on the network. Clients can then access the network to install the updates.|

## 5. Configure client settings for endpoint protection

https://learn.microsoft.com/en-us/intune/configmgr/protect/deploy-use/endpoint-protection-configure-client

ConfigMgr console → Administration → Client Seetings

Edit the Default Client Settings or Create Custom Client Device Settings

|Setting|Value|
|---|---|
|Manage Endpoint Protection client on client computers|Yes|
|Microsoft Defender for Endpoint client on Windows Server 2012 R2 and Windows Server 2016 [More information](https://learn.microsoft.com/en-us/defender-endpoint/onboard-server#functionality-in-the-modern-unified-solution-for-windows-server-2016-and-windows-server-2012-r2)|MDE client (recommended)|

> [!Note]
>
> "Manage Endpoint Protection client on client computers" is grayed out if endpoint protection site system role is not installed

![](https://github.com/user-attachments/assets/b15f0a73-d4cb-485f-bdc3-101aa5292611)

> [!Tip]
>
> Create custom client device settings to control specific settings and deploy to specified device collections
>
> ![](https://github.com/user-attachments/assets/1679cbc1-856f-4c94-8d31-132b1e575ef1)
>
> ![](https://github.com/user-attachments/assets/f996a614-a37f-4915-b240-f2e66bbc7e97)
>
> ![](https://github.com/user-attachments/assets/9054b899-e61b-4ff3-aa9e-a1c662ba1a3b)
