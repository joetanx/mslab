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
- users:
  - SQL reporting account (e.g. ConfigMgrSQLReporting)
  - domain join account (e.g. ConfigMgrDomainJoin)
  - network access account (e.g. ConfigMgrNetworkAccess)
  - client push account (e.g. ConfigMgrClientPush)
- password options: `User cannot change password`, `Password never expires`
- groups:
  - ConfigMgrAdmins
  - ConfigMgrSiteServers

### 2.3. extend AD schema

```
Start-Process cd.retail.LN\SMSSETUP\BIN\X64\extadsch.exe
Get-Content C:\ExtADSch.log
```

## 3. Configure ConfigMgr prerequisites

### 3.1. configure firewall

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

### 3.3. install roles

```cmd
powershell -NoProfile Install-WindowsFeature NET-Framework-Features,NET-Framework-Core,NET-HTTP-Activation,NET-Non-HTTP-Activ,NET-Framework-45-Features,NET-Framework-45-Core,NET-Framework-45-ASPNET,NET-WCF-Services45,NET-WCF-HTTP-Activation45,NET-WCF-TCP-PortSharing45,Web-Server,Web-WebServer,Web-ISAPI-Ext,Web-Windows-Auth,Web-Asp-Net,Web-Asp-Net45,Web-Mgmt-Tools,Web-Mgmt-Console,Web-Mgmt-Compat,Web-Metabase,Web-WMI,BITS,BITS-IIS-Ext,RDC -IncludeManagementTools
```

### 3.4. install windows ADK and windows PE add-on for windows ADK

https://learn.microsoft.com/en-us/windows-hardware/get-started/adk-install

windows ADK:

- Deployment Tools
- User State Migration Tool (USMT)

## 4. Prepare SQL Server

### 4.1. Install SQL data engine add ConfigMgrAdmins to SQL server administrators

### 4.2. Install SSMS

https://learn.microsoft.com/en-us/ssms/release-history#release-dates-and-build-numbers

![](https://github.com/user-attachments/assets/bb3c1352-ce27-4fc4-adda-9b361617cfb8)

![](https://github.com/user-attachments/assets/5029fa40-ea9f-45d3-8190-ed181d4b7b1c)

### 4.3. Install SQL reporting services

https://www.microsoft.com/en-us/download/details.aspx?id=104502

### 4.4. configure SPN for SQL server

```cmd
setspn -a MSSQLSvc/mssql.lab.vx:1433 MSSQLSvc
setspn -a MSSQLSvc/mssql.lab.vx:MICROLAB MSSQLSvc
```

## 5. Install ConfigMgr

### 5.1. verify prerequisites

```
Start-Process cd.retail.LN\SMSSETUP\BIN\X64\prereqchk.exe /AdminUI
Get-Content C:\ExtADSch.log
```

### 5.2. Install ConfigMgr
