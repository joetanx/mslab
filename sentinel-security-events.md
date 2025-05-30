## 1. Windows security events collected by Sentinel

There are 4 options during the configuration of DCR:

1. All security events
2. Common
3. Minimal
4. Custom

![image](https://github.com/user-attachments/assets/ad95ea3c-979b-40e1-b1a1-f9c113efbd4b)

The details of each options is documented here: https://learn.microsoft.com/en-us/azure/sentinel/windows-security-event-id-reference

## 2. "Common" Windows security events

The xPathQueries used when the DCR is configured for **common** can be verified from the JSON view of the DCR:

![image](https://github.com/user-attachments/assets/4dfeed86-c706-4014-8dc9-1b18195c263f)

```
"Security!*[System[(EventID=1) or (EventID=299) or (EventID=300) or (EventID=324) or (EventID=340) or (EventID=403) or (EventID=404) or (EventID=410) or (EventID=411) or (EventID=412) or (EventID=413) or (EventID=431) or (EventID=500) or (EventID=501) or (EventID=1100)]]",
"Security!*[System[(EventID=1102) or (EventID=1107) or (EventID=1108) or (EventID=4608) or (EventID=4610) or (EventID=4611) or (EventID=4614) or (EventID=4622) or (EventID=4624) or (EventID=4625) or (EventID=4634) or (EventID=4647) or (EventID=4648) or (EventID=4649) or (EventID=4657)]]",
"Security!*[System[(EventID=4661) or (EventID=4662) or (EventID=4663) or (EventID=4665) or (EventID=4666) or (EventID=4667) or (EventID=4688) or (EventID=4670) or (EventID=4672) or (EventID=4673) or (EventID=4674) or (EventID=4675) or (EventID=4689) or (EventID=4697) or (EventID=4700)]]",
"Security!*[System[(EventID=4702) or (EventID=4704) or (EventID=4705) or (EventID=4716) or (EventID=4717) or (EventID=4718) or (EventID=4719) or (EventID=4720) or (EventID=4722) or (EventID=4723) or (EventID=4724) or (EventID=4725) or (EventID=4726) or (EventID=4727) or (EventID=4728)]]",
"Security!*[System[(EventID=4729) or (EventID=4733) or (EventID=4732) or (EventID=4735) or (EventID=4737) or (EventID=4738) or (EventID=4739) or (EventID=4740) or (EventID=4742) or (EventID=4744) or (EventID=4745) or (EventID=4746) or (EventID=4750) or (EventID=4751) or (EventID=4752)]]",
"Security!*[System[(EventID=4754) or (EventID=4755) or (EventID=4756) or (EventID=4757) or (EventID=4760) or (EventID=4761) or (EventID=4762) or (EventID=4764) or (EventID=4767) or (EventID=4768) or (EventID=4771) or (EventID=4774) or (EventID=4778) or (EventID=4779) or (EventID=4781)]]",
"Security!*[System[(EventID=4793) or (EventID=4797) or (EventID=4798) or (EventID=4799) or (EventID=4800) or (EventID=4801) or (EventID=4802) or (EventID=4803) or (EventID=4825) or (EventID=4826) or (EventID=4870) or (EventID=4886) or (EventID=4887) or (EventID=4888) or (EventID=4893)]]",
"Security!*[System[(EventID=4898) or (EventID=4902) or (EventID=4904) or (EventID=4905) or (EventID=4907) or (EventID=4931) or (EventID=4932) or (EventID=4933) or (EventID=4946) or (EventID=4948) or (EventID=4956) or (EventID=4985) or (EventID=5024) or (EventID=5033) or (EventID=5059)]]",
"Security!*[System[(EventID=5136) or (EventID=5137) or (EventID=5140) or (EventID=5145) or (EventID=5632) or (EventID=6144) or (EventID=6145) or (EventID=6272) or (EventID=6273) or (EventID=6278) or (EventID=6416) or (EventID=6423) or (EventID=6424) or (EventID=8001) or (EventID=8002)]]",
"Security!*[System[(EventID=8003) or (EventID=8004) or (EventID=8005) or (EventID=8006) or (EventID=8007) or (EventID=8222) or (EventID=26401) or (EventID=30004)]]",
"Microsoft-Windows-AppLocker/EXE and DLL!*[System[(EventID=8001) or (EventID=8002) or (EventID=8003) or (EventID=8004)]]",
"Microsoft-Windows-AppLocker/MSI and Script!*[System[(EventID=8005) or (EventID=8006) or (EventID=8007)]]"
```

## 3. Inspecting event message from event ID

Event Viewer in Windows retrieves event messages from event IDs by referencing message resources stored within the associated event provider's DLL

The details of registered event providers are in the registry path: `HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services\EventLog\`

```cmd
C:\Windows\System32>reg query HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services\EventLog\

HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services\EventLog
    Description    REG_SZ    @%SystemRoot%\system32\wevtsvc.dll,-201
    DisplayName    REG_SZ    @%SystemRoot%\system32\wevtsvc.dll,-200
    ErrorControl    REG_DWORD    0x1
    FailureActions    REG_BINARY    80510100000000000000000003000000140000000100000060EA000001000000C0D401000000000000000000
    FailureActionsOnNonCrashFailures    REG_DWORD    0x1
    Group    REG_SZ    Event Log
    ImagePath    REG_EXPAND_SZ    %SystemRoot%\System32\svchost.exe -k LocalServiceNetworkRestricted -p
    ObjectName    REG_SZ    NT AUTHORITY\LocalService
    PlugPlayServiceType    REG_DWORD    0x3
    RequiredPrivileges    REG_MULTI_SZ    SeChangeNotifyPrivilege\0SeImpersonatePrivilege\0SeAuditPrivilege
    ServiceSidType    REG_DWORD    0x1
    Start    REG_DWORD    0x2
    Type    REG_DWORD    0x20

HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services\EventLog\Application
HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services\EventLog\HardwareEvents
HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services\EventLog\Internet Explorer
HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services\EventLog\Key Management Service
HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services\EventLog\Parameters
HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services\EventLog\Security
HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services\EventLog\State
HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services\EventLog\System
HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services\EventLog\Windows PowerShell
```

Get all the `EventMessageFile` fields under `Security` by doing a recursive query (`/s`) and filtering (`findstr`) for `EventMessageFile`:

```cmd
C:\Windows\System32>reg query HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services\EventLog\Security /s | findstr EventMessageFile
    EventMessageFile    REG_EXPAND_SZ    %SystemRoot%\System32\wevtsvc.dll
    EventMessageFile    REG_EXPAND_SZ    %SystemRoot%\system32\adtschema.dll
    EventMessageFile    REG_EXPAND_SZ    %SystemRoot%\System32\MsAuditE.dll
    EventMessageFile    REG_SZ    C:\Windows\Microsoft.NET\Framework64\v4.0.30319\ServiceModelEvents.dll
    EventMessageFile    REG_EXPAND_SZ    %SystemRoot%\System32\VSSVC.EXE
```

The main file containing the message table for security events is: `%SystemRoot%\system32\adtschema.dll`

Exploring the DLL can be done with [Resource Hacker](https://www.angusj.com/resourcehacker/):

![image](https://github.com/user-attachments/assets/5c0a2f85-fc4e-4731-af0d-c092e2f4bb9b)

Another useful resource for event reference is: https://www.ultimatewindowssecurity.com/securitylog/encyclopedia/default.aspx

> [!Note]
>
> A lookup table for event IDs to event messages is tabulated [here](/sentinel_security_events.csv)
>
> Most of the event IDs are found, but there are several that I still couldn't find them, contact me if you know what they are
