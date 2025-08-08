Ref:
- https://www.youtube.com/watch?v=hub1Lm7oVy8
- https://www.youtube.com/@microsoftendpointmanager-s5074/search?query=endpoint%20protection

## 1. Retrieve and extract ConfigMgr installation files



## 2. Prepare SQL Server

### 2.1. Install SQL data engine add ConfigMgrAdmins to SQL server administrators

### 2.2. Install SSMS

https://learn.microsoft.com/en-us/ssms/release-history#release-dates-and-build-numbers

### 2.3. Install SQL reporting services
https://www.microsoft.com/en-us/download/details.aspx?id=104502

### 2.4. configure SPN for SQL server
setspn -a MSSQLSvc/mssql.lab.vx:1433 MSSQLSvc
setspn -a MSSQLSvc/mssql.lab.vx:MICROLAB MSSQLSvc

## 3. Prepare Active Directory

### 3.1. Create system management container

ADSI edit → Connect to... → Default naming context → `CN=System` folder → New → Object → container → value: `System Management`
right-click created `System Management` container → Properties → Security → add → Object Types \ Computers → select site servers → Full control
Advanced → Edit added site server → change `Applies to`: `This object and all descendant objects`

### 3.2. Create service accounts in ADUC
- users:
  - SQL reporting account (e.g. ConfigMgrSQLReporting)
  - domain join account (e.g. ConfigMgrDomainJoin)
  - network access account (e.g. ConfigMgrNetworkAccess)
  - client push account (e.g. ConfigMgrClientPush)
- password options: `User cannot change password`, `Password never expires`
- groups:
  - ConfigMgrAdmins
  - ConfigMgrSiteServers

### 3.3. extend AD schema

```
Start-Process cd.retail.LN\SMSSETUP\BIN\X64\extadsch.exe
Get-Content C:\ExtADSch.log
```

## 4. Configure ConfigMgr prerequisites

### 4.1. configure firewall

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

### 4.2. Prevent ConfigManager from installing on unintended drives

Create an empty no_sms_on_drive.sms file

Place the file on drives that ConfigManager should not install on

### 4.3. install roles

```cmd
powershell -NoProfile Install-WindowsFeature NET-Framework-Features,NET-Framework-Core,NET-HTTP-Activation,NET-Non-HTTP-Activ,NET-Framework-45-Features,NET-Framework-45-Core,NET-Framework-45-ASPNET,NET-WCF-Services45,NET-WCF-HTTP-Activation45,NET-WCF-TCP-PortSharing45,Web-Server,Web-WebServer,Web-ISAPI-Ext,Web-Windows-Auth,Web-Asp-Net,Web-Asp-Net45,Web-Mgmt-Tools,Web-Mgmt-Console,Web-Mgmt-Compat,Web-Metabase,Web-WMI,BITS,BITS-IIS-Ext,RDC -IncludeManagementTools
```

### 4.4. install windows ADK and windows PE add-on for windows ADK

https://learn.microsoft.com/en-us/windows-hardware/get-started/adk-install

windows ADK:

- Deployment Tools
- User State Migration Tool (USMT)

## 5. Install ConfigMgr

### 5.1. verify prerequisites

```
Start-Process cd.retail.LN\SMSSETUP\BIN\X64\prereqchk.exe /AdminUI
Get-Content C:\ExtADSch.log
```

### 5.2. Install ConfigMgr
