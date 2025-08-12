Ref:
- https://www.systemcenterdudes.com/complete-sccm-installation-guide-and-configuration/
- https://www.youtube.com/watch?v=hub1Lm7oVy8
- https://www.youtube.com/@microsoftendpointmanager-s5074/search?query=endpoint%20protection

## 1. Retrieve and extract ConfigMgr installation files

https://www.microsoft.com/en-us/evalcenter/download-microsoft-endpoint-configuration-manager

![](https://github.com/user-attachments/assets/9dbc867b-b246-4466-ae08-47d94489762d)

![](https://github.com/user-attachments/assets/d4f3ae2d-014b-47cc-8826-baac46ae5e2b)

![](https://github.com/user-attachments/assets/a5e269f8-58ad-4ad6-8d7e-dda90f2f08e0)

![](https://github.com/user-attachments/assets/eda4f970-1297-4279-a2a0-30a096b080b1)

## 2. Prepare Active Directory

### 2.1. Create service accounts in ADUC

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

![](https://github.com/user-attachments/assets/39e0317e-8ace-44f5-98cc-9c38b31928fa)

### 2.2. Prepare system management container

ADSI Edit → Connect to... → `Default naming context` → `CN=System` folder → New → Object → container → value: `System Management`

![](https://github.com/user-attachments/assets/cb1dd7e9-0cca-4ad8-945b-6ceaa87f6ef6)

![](https://github.com/user-attachments/assets/5ae9381a-3ec8-4416-a035-f269c98984c2)

![](https://github.com/user-attachments/assets/8dad4d9a-700d-4f2d-8df7-9c432bfbeab5)

### 2.3. Grant permissions on system management container to ConfigMgr

Right-click on created `System Management` container → Properties → Security → Advanced → Add

![](https://github.com/user-attachments/assets/1b948550-7304-4379-82ac-e928cadcaba3)

Select a principal → Object Types → check Computers → select site servers → Full control

(Note: Applies to: `This object and all descendant objects`)

![](https://github.com/user-attachments/assets/c381b1b4-75e8-4962-86f1-ce740a0b3b6c)

### 2.4. Extend AD schema

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
Install-WindowsFeature NET-Framework-Features,NET-Framework-Core,NET-HTTP-Activation,NET-Non-HTTP-Activ,NET-Framework-45-Features,NET-Framework-45-Core,NET-Framework-45-ASPNET,NET-WCF-Services45,NET-WCF-HTTP-Activation45,NET-WCF-TCP-PortSharing45,Web-Server,Web-WebServer,Web-ISAPI-Ext,Web-Windows-Auth,Web-Asp-Net,Web-Asp-Net45,Web-Mgmt-Tools,Web-Mgmt-Console,Web-Mgmt-Compat,Web-Metabase,Web-WMI,BITS,BITS-IIS-Ext,RDC,UpdateServices -IncludeManagementTools
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

### 3.5. Certificate binding for HTTPS

IIS Manager → Default Web Site → Bindings... → Add... → Type: `https` → select SSL certificate that has SAN for the ConfigMgr management and distribution point FQDNs

![](https://github.com/user-attachments/assets/591c8e2f-bdf5-44ab-b849-6f2842370c76)

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

### 5.1. Verify prerequisites

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

![](https://github.com/user-attachments/assets/6b171708-1c3a-426d-9ef8-b734d354b853)

![](https://github.com/user-attachments/assets/2d8928a9-1efc-426a-a2b9-172f93292342)

![](https://github.com/user-attachments/assets/339e346d-1b8e-4d62-8021-8813b9eb3d38)

![](https://github.com/user-attachments/assets/eb29241b-fb6a-447e-be4a-aa57dd133d2c)

![](https://github.com/user-attachments/assets/cb83b11b-654b-4c7d-bb64-f1e1e8015ac8)

![](https://github.com/user-attachments/assets/9a7b5ccd-c635-4b51-8441-a1d4baa89bd5)

![](https://github.com/user-attachments/assets/a8f276fe-5d5d-4c8a-9a5d-861580a9e544)

![](https://github.com/user-attachments/assets/f220c84a-5821-405c-9902-3ce526fbc0a9)

![](https://github.com/user-attachments/assets/50c4c0f4-c107-419d-a2a3-23247fe9a4cb)

The warnings are fine for a lab setup, the details to resolve them are:
- [SQL Server Native Client](https://learn.microsoft.com/en-us/intune/configmgr/core/servers/deploy/install/list-of-prerequisite-checks#sql-server-native-client)
- [SQL Server security mode](https://learn.microsoft.com/en-us/intune/configmgr/core/servers/deploy/install/list-of-prerequisite-checks#sql-server-security-mode)
- [Configuration for SQL Server memory usage](https://learn.microsoft.com/en-us/intune/configmgr/core/servers/deploy/install/list-of-prerequisite-checks#configuration-for-sql-server-memory-usage)
- [SQL Server process memory allocation](https://learn.microsoft.com/en-us/intune/configmgr/core/servers/deploy/install/list-of-prerequisite-checks#sql-server-process-memory-allocation)

The setup wizard takes about 25 mins before it can exit, with a few items still running:

![](https://github.com/user-attachments/assets/d194574f-f660-4d2b-a523-512c07fd1f68)

> [!Tip]
>
> Do not exit the setup wizard window, the status of each component setup is still being updated in the wizard
>
> It can take up to 1 hour for all setup to finish and the machine may look like it is idling at times
>
> When the setup is fully completed, all components have the ✅ completion icon
>
> ![](https://github.com/user-attachments/assets/0a840a05-c5ce-414c-8bd1-4d0b6172bc20)

### 5.3. Update ConfigMgr

> [!Tip]
>
> Service connection point is required for updates to work

#### 5.3.1. Initiate update

ConfigMgr console → Administration → Updates and Servicing

Check for updates, select the desired update, then `Run prerequisite check` followed by `Install Update pack`

![](https://github.com/user-attachments/assets/2c837c1c-b787-4bde-9b67-99647baeffe8)

![](https://github.com/user-attachments/assets/c1363463-f4a6-4253-98be-698759a05765)

![](https://github.com/user-attachments/assets/fe9d8104-3670-4b1e-8426-883c8d76d5fc)

![](https://github.com/user-attachments/assets/82506fe4-1154-4f9f-9a06-c6f7f885837a)

![](https://github.com/user-attachments/assets/353866e8-3a3a-4f1c-9c99-a70276f40e82)

![](https://github.com/user-attachments/assets/b40c2331-1d97-400f-8fc5-e4e7b17a176c)

![](https://github.com/user-attachments/assets/2c17f9c8-89fb-4b91-aa7a-a2865d706a36)

![](https://github.com/user-attachments/assets/8df915b1-d75a-4488-a68c-d481fc8ceb3f)

#### 5.3.2. Monitor update progress

Check status of the update installation: ConfigMgr console → Monitoring → Updates and Servicing Status → Show Status

![](https://github.com/user-attachments/assets/bdb1718c-6f53-4285-84c7-7713c46ece3f)

![](https://github.com/user-attachments/assets/70682128-af3f-4133-b4f8-124fd3e07f4d)

The update will take some time and it would look like the machine is idling at times, click on the step to see more task details:

![](https://github.com/user-attachments/assets/0db3d54a-ada9-49e6-b300-1530c718bc49)

The `SMS_EXECUTIVE` service will be stopped and disabled after some time as part of the update, and the ConfigMgr console will disconnect

![](https://github.com/user-attachments/assets/06ee8154-4389-4a4a-8b63-dcc7ebda5091)

Monitor the `C:\Program Files\Microsoft Configuration Manager\Logs\CMUpdate.log` file for upgrade progress

#### 5.3.3. Update ConfigMgr console

![](https://github.com/user-attachments/assets/27c4a1b0-47ee-4b10-8c5a-769aca910067)

#### 5.3.4. Update complete

- Microsoft Configuration Manager Version: 2503
- Console Version: 5.2503.1083.1000
- Site Version: 5.0.9135.1000

![](https://github.com/user-attachments/assets/e48960f6-daf1-4872-b553-af9225979aef)

## 6. Prepare Active Directory boundary for client installation

### 6.1. Configure Active Directory forest discovery

ConfigMgr console → Administration → Hierachy Configuration → Discovery Methods

![](https://github.com/user-attachments/assets/fff3ac6c-dc1e-4c85-89ee-c14a5819f96e)

![](https://github.com/user-attachments/assets/d7376225-b21c-4624-a345-ad6bf52d014b)

### 6.2. Verify boundary created from discovery

ConfigMgr console → Administration → Hierachy Configuration → Boundaries

![](https://github.com/user-attachments/assets/457593d2-8e62-424c-bc09-e43279d9436f)

### 6.3. Create boundary group to associate boundary and site server

ConfigMgr console → Administration → Hierachy Configuration → Boundary Groups → Create Boundary Group

![](https://github.com/user-attachments/assets/edc40cdf-cb2a-4b50-991d-a3f8fc9c234d)

General → Boundaries → Add... → select the Active Directory boundary:

![](https://github.com/user-attachments/assets/e7745143-eb57-447f-9c96-40b34fb0ab4c)

![](https://github.com/user-attachments/assets/92f0ffcb-e6cc-4d33-868b-2b1a7293d322)

References → Select site system servers → Add... → select the site system:

![](https://github.com/user-attachments/assets/b3bef1a9-7a95-48b9-a329-52068f2247ed)

![](https://github.com/user-attachments/assets/393cc69e-ea19-40f6-bc2c-d74f565100de)

![](https://github.com/user-attachments/assets/12798d4c-0c02-4172-b7fa-4ee2813732c9)
