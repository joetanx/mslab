Ref: https://learn.microsoft.com/en-us/intune/configmgr/protect/deploy-use/endpoint-protection-configure

## 1. Setup EPP site system role

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

## 2. Setup alerts for endpoint protection

ConfigMgr console → Assets and Compliance → Device Collections → Select device collection → Properties

![](https://github.com/user-attachments/assets/9b2c616d-9591-40bd-82f6-0d6228a7d6f9)

> [!Tip]
>
> Right-click and select Show Members to see the devices in the device collection
>
> ![](https://github.com/user-attachments/assets/69c596fd-a5cf-4dcb-be03-ad26090cc13a)
>
> ![](https://github.com/user-attachments/assets/b7cbbdce-05f9-477a-806a-5ac7c92ce4d6)

