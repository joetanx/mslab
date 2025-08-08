Ref:
- https://www.youtube.com/watch?v=hub1Lm7oVy8
- https://www.youtube.com/@microsoftendpointmanager-s5074/search?query=endpoint%20protection

## 1. Retrieve and extract ConfigMgr installation files

https://www.microsoft.com/en-us/evalcenter/download-microsoft-endpoint-configuration-manager

![](https://github.com/user-attachments/assets/9dbc867b-b246-4466-ae08-47d94489762d)

![](https://github.com/user-attachments/assets/d4f3ae2d-014b-47cc-8826-baac46ae5e2b)

![](https://github.com/user-attachments/assets/a5e269f8-58ad-4ad6-8d7e-dda90f2f08e0)

![](https://github.com/user-attachments/assets/eda4f970-1297-4279-a2a0-30a096b080b1)

## 2. Prepare Active Directory

### 2.1. Prepare system management container

ADSI Edit → Connect to... → `Default naming context` → `CN=System` folder → New → Object → container → value: `System Management`

![](https://github.com/user-attachments/assets/cb1dd7e9-0cca-4ad8-945b-6ceaa87f6ef6)

![](https://github.com/user-attachments/assets/5ae9381a-3ec8-4416-a035-f269c98984c2)

![](https://github.com/user-attachments/assets/8dad4d9a-700d-4f2d-8df7-9c432bfbeab5)

### 2.2. Grant permissions on system management container to ConfigMgr

Right-click on created `System Management` container → Properties → Security → Advanced → Add

![](https://github.com/user-attachments/assets/1b948550-7304-4379-82ac-e928cadcaba3)

Select a principal → Object Types → check Computers → select site servers → Full control

(Note: Applies to: `This object and all descendant objects`)

![](https://github.com/user-attachments/assets/fc336fec-3628-4a12-9ca3-679109c235a0)

### 2.2. Create service accounts in ADUC

#### Users

Password options:
- User cannot change password
- Password never expires

|Account|Example name|
|---|---|
|SQL service account|`MSSQLSvc`|
|SQL reporting account|`ConfigMgrSQLReporting`|
|domain join account|`ConfigMgrDomainJoin`|
|network access account|`ConfigMgrNetworkAccess`|
|client push account|`ConfigMgrClientPush`|

#### Groups

|Account|Example name|
|---|---|
|Configuration Manager administrators|`ConfigMgrAdmins`|
|Configuration Manager site servers|`ConfigMgrSiteServers`|

#### Add ConfigMgr administrators and site servers group to `Administrators` group

![](https://github.com/user-attachments/assets/bb96237d-766f-400d-9d07-a1405c79341e)

### 2.3. Extend AD schema

```pwsh
PS C:\Users\Administrator> Start-Process cd.retail.LN\SMSSETUP\BIN\X64\extadsch.exe
PS C:\Users\Administrator> Get-Content C:\ExtADSch.log


<08-08-2025 13:18:29> Modifying Active Directory Schema - with SMS extensions.
﻿<08-08-2025 13:18:29> DS Root:CN=Schema,CN=Configuration,DC=lab,DC=vx
﻿<08-08-2025 13:18:29> Defined attribute cn=MS-SMS-Site-Code.
﻿<08-08-2025 13:18:29> Defined attribute cn=mS-SMS-Assignment-Site-Code.
﻿<08-08-2025 13:18:29> Defined attribute cn=MS-SMS-Site-Boundaries.
﻿<08-08-2025 13:18:29> Defined attribute cn=MS-SMS-Roaming-Boundaries.
﻿<08-08-2025 13:18:29> Defined attribute cn=MS-SMS-Default-MP.
﻿<08-08-2025 13:18:29> Defined attribute cn=mS-SMS-Device-Management-Point.
﻿<08-08-2025 13:18:29> Defined attribute cn=MS-SMS-MP-Name.
﻿<08-08-2025 13:18:29> Defined attribute cn=MS-SMS-MP-Address.
﻿<08-08-2025 13:18:29> Defined attribute cn=mS-SMS-Health-State.
﻿<08-08-2025 13:18:29> Defined attribute cn=mS-SMS-Source-Forest.
﻿<08-08-2025 13:18:29> Defined attribute cn=MS-SMS-Ranged-IP-Low.
﻿<08-08-2025 13:18:29> Defined attribute cn=MS-SMS-Ranged-IP-High.
﻿<08-08-2025 13:18:29> Defined attribute cn=mS-SMS-Version.
﻿<08-08-2025 13:18:29> Defined attribute cn=mS-SMS-Capabilities.
﻿<08-08-2025 13:18:29> Defined class cn=MS-SMS-Management-Point.
﻿<08-08-2025 13:18:29> Defined class cn=MS-SMS-Server-Locator-Point.
﻿<08-08-2025 13:18:29> Defined class cn=MS-SMS-Site.
﻿<08-08-2025 13:18:29> Defined class cn=MS-SMS-Roaming-Boundary-Range.
﻿<08-08-2025 13:18:30> Successfully extended the Active Directory schema.

﻿<08-08-2025 13:18:30> Please refer to the ConfigMgr documentation for instructions on the manual
﻿<08-08-2025 13:18:30> configuration of access rights in active directory which may still
﻿<08-08-2025 13:18:30> need to be performed.  (Although the AD schema has now be extended,
﻿<08-08-2025 13:18:30> AD must be configured to allow each ConfigMgr Site security rights to
﻿<08-08-2025 13:18:30> publish in each of their domains.)
```

## 3. Configure ConfigMgr prerequisites

### 3.1. Configure firewall

```cmd
@echo ---- SQL Server Ports ----
@echo Enabling SQL Server default instance port 1433
netsh advfirewall firewall add rule name="SQL Server" dir=in action=allow protocol=TCP localport=1433
@echo Enabling Dedicated Admin Connection port 1434
netsh advfirewall firewall add rule name="SQL Admin Connection" dir=in action=allow protocol=TCP localport=1434
@echo Enabling conventional SQL Server Service Broker port 4022
netsh advfirewall firewall add rule name="SQL Service Broker" dir=in action=allow protocol=TCP localport=49022
@echo Enabling Transact-SQL Debugger/RPC port 135
netsh advfirewall firewall add rule name="SQL Debugger/RPC" dir=in action=allow protocol=TCP localport=135
@echo ---- Analysis Services Ports ----
@echo Enabling SSAS Default Instance port 2383
netsh advfirewall firewall add rule name="Analysis Services" dir=in action=allow protocol=TCP localport=2383
@echo Enabling SQL Server Browser Service port 2382
netsh advfirewall firewall add rule name="SQL Browser" dir=in action=allow protocol=TCP localport=2382
@echo ---- Misc Applications ----
@echo Enabling HTTP port 80
netsh advfirewall firewall add rule name="HTTP" dir=in action=allow protocol=TCP localport=80
@echo Enabling SSL port 443
netsh advfirewall firewall add rule name="SSL" dir=in action=allow protocol=TCP localport=443
@echo Enabling port for SQL Server Browser Service's 'Browse' Button
netsh advfirewall firewall add rule name="SQL Browser" dir=in action=allow protocol=TCP localport=1434
@echo Allowing Ping command
netsh advfirewall firewall add rule name="ICMP Allow incoming V4 echo request" protocol=icmpv4:8,any dir=in action=allow
```

### 3.2. Prevent ConfigManager from installing on unintended drives

Create an empty no_sms_on_drive.sms file

Place the file on drives that ConfigManager should not install on

### 3.3. Install roles

```cmd
Install-WindowsFeature NET-Framework-Features,NET-Framework-Core,NET-HTTP-Activation,NET-Non-HTTP-Activ,NET-Framework-45-Features,NET-Framework-45-Core,NET-Framework-45-ASPNET,NET-WCF-Services45,NET-WCF-HTTP-Activation45,NET-WCF-TCP-PortSharing45,Web-Server,Web-WebServer,Web-ISAPI-Ext,Web-Windows-Auth,Web-Asp-Net,Web-Asp-Net45,Web-Mgmt-Tools,Web-Mgmt-Console,Web-Mgmt-Compat,Web-Metabase,Web-WMI,BITS,BITS-IIS-Ext,RDC -IncludeManagementTools
```

### 3.4. install windows ADK and windows PE add-on for windows ADK

https://learn.microsoft.com/en-us/windows-hardware/get-started/adk-install

![](https://github.com/user-attachments/assets/7ae328bb-21a6-46a2-a2b4-eaaa6b392846)

#### Windows ADK

![](https://github.com/user-attachments/assets/bdb8448e-d67e-40b5-aa71-2685d54d6812)

- Deployment Tools
- User State Migration Tool (USMT)

![](https://github.com/user-attachments/assets/ce46257e-e091-4bd5-aeb2-4531f35b9630)

#### Windows PE add-on for the Windows ADK

![](https://github.com/user-attachments/assets/ac444a43-0297-464d-a2d2-9c65ea7a0107)

![](https://github.com/user-attachments/assets/5d4ec707-9c66-43f5-bdfb-bdf0ec19cb08)

## 4. Prepare SQL Server

### 4.1. Install SQL data engine add ConfigMgrAdmins to SQL server administrators

![](https://github.com/user-attachments/assets/2c30ffc9-0d74-4ecd-9307-479b867f5aa8)

![](https://github.com/user-attachments/assets/00093c32-3a20-48be-8ca5-db0958d0105d)

![](https://github.com/user-attachments/assets/cddcf160-8ab6-4bf8-8445-9540f522eb56)

### 4.2. Install SSMS

https://learn.microsoft.com/en-us/ssms/release-history#release-dates-and-build-numbers

![](https://github.com/user-attachments/assets/bb3c1352-ce27-4fc4-adda-9b361617cfb8)

![](https://github.com/user-attachments/assets/5029fa40-ea9f-45d3-8190-ed181d4b7b1c)

### 4.3. Install SQL reporting services

https://www.microsoft.com/en-us/download/details.aspx?id=104502

![](https://github.com/user-attachments/assets/d85316ce-e5f9-4a8e-bbc4-3e1cd7ffb393)

![](https://github.com/user-attachments/assets/6c2279ab-9ce4-46bf-94ce-2e7114f0fac0)

### 4.4. configure SPN for SQL server

```cmd
setspn -a MSSQLSvc/mssql.lab.vx:1433 MSSQLSvc
setspn -a MSSQLSvc/mssql.lab.vx:MICROLAB MSSQLSvc
```

### 4.5. Install ODBC Driver for SQL Server

https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server

![](https://github.com/user-attachments/assets/4550f908-fe72-4d27-8255-da0d4b7e43a5)

Test that the ODBC Driver for SQL Server exists when selecting ODBC data source

![](https://github.com/user-attachments/assets/34a955b0-add8-429e-a91b-478ba713bbc7)

## 5. Install ConfigMgr

### 5.1. verify prerequisites

```
Start-Process cd.retail.LN\SMSSETUP\BIN\X64\prereqchk.exe /AdminUI
```

![](https://github.com/user-attachments/assets/7a43e2df-181e-4c94-8840-6b68af914463)

### 5.2. Install ConfigMgr

```
Start-Process cd.retail.LN\splash.hta
```

![](https://github.com/user-attachments/assets/d5fefc25-5660-445f-b239-858759ea4711)

![](https://github.com/user-attachments/assets/d49040a4-a705-43ed-b3c6-f7fd4483109d)

![](https://github.com/user-attachments/assets/0bcf14bc-cb51-44d4-ad76-c83148d1cf49)

![](https://github.com/user-attachments/assets/1f6d0e81-3cb6-4d1e-b949-fb6bf94c0017)

![](https://github.com/user-attachments/assets/c53e0e7d-d47d-4ccf-97b2-622c8254f065)

![](https://github.com/user-attachments/assets/25715e07-0817-4dc5-902f-5f185dd14675)

![](https://github.com/user-attachments/assets/c17800f7-5923-454c-90ee-7db2b5d7f757)

![](https://github.com/user-attachments/assets/41b92906-d972-4017-9795-31da8c6ddfe7)

![](https://github.com/user-attachments/assets/d3680388-5e64-47d5-9c12-1a1a7ad4c641)

![](https://github.com/user-attachments/assets/ebcc4aaa-df0a-4284-8a00-473b9d3402c8)

![](https://github.com/user-attachments/assets/87c13175-9eba-41b7-aead-7293fe3d0777)

![](https://github.com/user-attachments/assets/2d8928a9-1efc-426a-a2b9-172f93292342)

