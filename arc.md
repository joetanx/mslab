## 1. Connect hybrid machines to Azure using a deployment script

![image](https://github.com/user-attachments/assets/fa01e36f-609c-4ce8-807c-7b91754bf12e)

![image](https://github.com/user-attachments/assets/75041680-c2c5-4057-a105-f60ed5265d46)

## 2. Windows

### 2.1. Generate installation script

![image](https://github.com/user-attachments/assets/e11fc376-13a5-4e9f-af8d-a3469275984f)

#### 2.2. Execute installation script

Run the powershell script:

```pwsh
PS C:\Users\Administrator> .\OnboardingScript.ps1
VERBOSE: Installing Azure Connected Machine Agent
VERBOSE: PowerShell version: 5.1.26100.2161
VERBOSE: Total Physical Memory: 4096 MB
VERBOSE: .NET Framework version: 4.8.9032
VERBOSE: Checking if this is an Azure virtual machine
VERBOSE: Error The operation has timed out. checking if we are in Azure
VERBOSE: Downloading agent package from https://gbl.his.arc.azure.com/azcmagent/latest/AzureConnectedMachineAgent.msi to C:\Users\ADMINI~1\AppData\Local\Temp\2\AzureConnectedMachineAgent.msi
VERBOSE: Installing agent package
Installation of azcmagent completed successfully
INFO    Connecting machine to Azure... This might take a few minutes.
INFO    Testing connectivity to endpoints that are needed to connect to Azure... This might take a few minutes.
INFO    Please login using the pop-up browser to authenticate.
```

Login and authenticate through pop-up browser:

![image](https://github.com/user-attachments/assets/a656abf7-95a4-4768-97a6-5aab7e84fde6)

![image](https://github.com/user-attachments/assets/f7519e48-9e63-4276-be15-fdbfc0c0c36f)

Installation proceeds automatically after authentication:

```pwsh
  20% [==>            ]
  30% [===>           ]
  INFO    Creating resource in Azure...                 Correlation ID=640902b0-5155-4a11-8fa3-6a4a97d631f1 Resource ID=/subscriptions/3d0e465b-5f2e-4874-bf2c-99c3af896a41/resourceGroups/ConnectedMachinesRG/providers/Microsoft.HybridCompute/machines/azcm-winsvr
  60% [========>      ]
  80% [===========>   ]
 100% [===============]
  INFO    Connected machine to Azure
INFO    Machine overview page: https://portal.azure.com/#@659330c7-4c00-42e9-b0d6-411ab5697f6e/resource/subscriptions/3d0e465b-5f2e-4874-bf2c-99c3af896a41/resourceGroups/ConnectedMachinesRG/providers/Microsoft.HybridCompute/machines/azcm-winsvr/overview
```

### 2.3. Verify connection in Azure

![image](https://github.com/user-attachments/assets/8948dd30-21a2-455a-8b0f-b5c47890c94c)

## 3. Linux

### 3.1. Generate installation script:

![image](https://github.com/user-attachments/assets/f2449a51-5b10-4115-9cb7-7f6a52b7e0ee)

### 3.2. Execute installation script

#### 3.2.1. Rocky Linux

Run the bash script:

```console
[root@azcm-rocky ~]# chmod +x OnboardingScript.sh
[root@azcm-rocky ~]# ./OnboardingScript.sh
--2025-04-23 09:29:28--  https://gbl.his.arc.azure.com/azcmagent-linux
Resolving gbl.his.arc.azure.com (gbl.his.arc.azure.com)... 172.202.65.10, 172.202.64.10, 2603:1030:13:201::10, ...
Connecting to gbl.his.arc.azure.com (gbl.his.arc.azure.com)|172.202.65.10|:443... connected.
HTTP request sent, awaiting response... 200 OK
Length: unspecified [text/plain]
Saving to: ‘/tmp/install_linux_azcmagent.sh’

     0K .......... .......... .......... .                      458K=0.07s

2025-04-23 09:29:29 (458 KB/s) - ‘/tmp/install_linux_azcmagent.sh’ saved [32155]
Using 'curl' for downloads
Total physical memory: 4007416 kB
Platform type:  x86_64:Linux
Retrieving distro info from /etc/os-release...
Configuring for Rocky Linux 9...
Using 'dnf' instead of 'yum'
No match for argument: packages-microsoft-prod
No packages marked for removal.
Dependencies resolved.
Nothing to do.
Complete!
  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed
100  9450  100  9450    0     0  70000      0 --:--:-- --:--:-- --:--:-- 69485
warning: /tmp/packages-microsoft-prod.rpm: Header V4 RSA/SHA256 Signature, key ID be1229cf: NOKEY
Microsoft Production                                                                                                                                                            3.1 kB/s | 481  B     00:00
Microsoft Production                                                                                                                                                            960 kB/s | 983  B     00:00
Importing GPG key 0xBE1229CF:
 Userid     : "Microsoft (Release signing) <gpgsecurity@microsoft.com>"
 Fingerprint: BC52 8686 B50D 79E3 39D3 721C EB3E 94AD BE12 29CF
 From       : /etc/pki/rpm-gpg/RPM-GPG-KEY-Microsoft
Microsoft Production                                                                                                                                                            4.4 MB/s |  13 MB     00:02
Last metadata expiration check: 0:00:03 ago on Wed 23 Apr 2025 09:29:33 AM +08.
Dependencies resolved.
================================================================================================================================================================================================================
 Package                                      Architecture                              Version                                            Repository                                                      Size
================================================================================================================================================================================================================
Installing:
 azcmagent                                    x86_64                                    1.51.03008-304                                     packages-microsoft-com-prod                                     82 M

Transaction Summary
================================================================================================================================================================================================================
Install  1 Package

Total download size: 82 M
Installed size: 239 M
Downloading Packages:
azcmagent-1.51.03008-304.x86_64.rpm                                                                                                                                             2.9 MB/s |  82 MB     00:28
----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
Total                                                                                                                                                                           2.9 MB/s |  82 MB     00:28
Microsoft Production                                                                                                                                                            960 kB/s | 983  B     00:00
Importing GPG key 0xBE1229CF:
 Userid     : "Microsoft (Release signing) <gpgsecurity@microsoft.com>"
 Fingerprint: BC52 8686 B50D 79E3 39D3 721C EB3E 94AD BE12 29CF
 From       : /etc/pki/rpm-gpg/RPM-GPG-KEY-Microsoft
Key imported successfully
Running transaction check
Transaction check succeeded.
Running transaction test
Transaction test succeeded.
Running transaction
  Preparing        :                                                                                                                                                                                        1/1
  Running scriptlet: azcmagent-1.51.03008-304.x86_64                                                                                                                                                        1/1
Pre...Install
Creating himds group ...
Creating himds account ...
Creating arcproxy account ...
Applying udev rule to access TPM...
Adding TPM udev rule
KERNEL=="tpm*", SUBSYSTEM=="tpm", TAG+="systemd", OWNER="root", GROUP="tss", MODE="0660"
User 'himds' added to tss group
No TPM device detected

  Installing       : azcmagent-1.51.03008-304.x86_64                                                                                                                                                        1/1
  Running scriptlet: azcmagent-1.51.03008-304.x86_64                                                                                                                                                        1/1
Post...Install
which: no netstat in (/sbin:/bin:/usr/sbin:/usr/bin:/usr/X11R6/bin)
Netstat not installed.  Skipping IP port checking. The services need to listen on 40342 and 40343
/var/tmp/rpm-tmp.Xx667O: line 38:  : command not found
which: no semanage in (/sbin:/bin:/usr/sbin:/usr/bin:/usr/X11R6/bin)
Created symlink /etc/systemd/system/multi-user.target.wants/himdsd.service → /usr/lib/systemd/system/himdsd.service.
Local configuration file is found
Created symlink /etc/systemd/system/multi-user.target.wants/arcproxyd.service → /usr/lib/systemd/system/arcproxyd.service.
Getting status via systemd
Arc GC service is not running.
Configuring Arc GC service ...
Found systemd service controller...for Arc GC Service
Created symlink /etc/systemd/system/multi-user.target.wants/gcad.service → /usr/lib/systemd/system/gcad.service.
Service configured through systemd service controller. Gc Service
Local configuration file is found
Checked guest config disabled: 0
Getting status via systemd
Arc GC service is not running.
STARTING Arc GC
Getting status via systemd
EXT service is not running.
Configuring EXT service ...
Found systemd service controller...for Extension Service
Created symlink /etc/systemd/system/multi-user.target.wants/extd.service → /usr/lib/systemd/system/extd.service.
Service configured through systemd service controller. Extension Service
Local configuration file is found
Checked extd disabled: 0
STARTING EXT

  Verifying        : azcmagent-1.51.03008-304.x86_64                                                                                                                                                        1/1

Installed:
  azcmagent-1.51.03008-304.x86_64

Complete!
Latest version of azcmagent is installed.
INFO    Connecting machine to Azure... This might take a few minutes.
INFO    Testing connectivity to endpoints that are needed to connect to Azure... This might take a few minutes.
To sign in, use a web browser to open the page https://microsoft.com/devicelogin and enter the code E4PQ6FEZ8 to authenticate.
```

![image](https://github.com/user-attachments/assets/419e551a-1e09-4894-b7ba-acfb8f75252b)

![image](https://github.com/user-attachments/assets/8e4a88d8-c372-439e-830a-e15ea4e309ee)

![image](https://github.com/user-attachments/assets/ab11ae70-cbdf-4098-bd6e-46294ad7fe55)

![image](https://github.com/user-attachments/assets/0747d3a3-a5ca-4b44-a077-60a709d17227)

Installation proceeds automatically after authentication:

```console
  20% [==>            ]
  30% [===>           ]
  INFO    Creating resource in Azure...                 Correlation ID=640902b0-5155-4a11-8fa3-6a4a97d631f1 Resource ID=/subscriptions/3d0e465b-5f2e-4874-bf2c-99c3af896a41/resourceGroups/ConnectedMachinesRG/providers/Microsoft.HybridCompute/machines/azcm-rocky
  60% [========>      ]
  80% [===========>   ]
 100% [===============]
  INFO    Connected machine to Azure
INFO    Machine overview page: https://portal.azure.com/#@659330c7-4c00-42e9-b0d6-411ab5697f6e/resource/subscriptions/3d0e465b-5f2e-4874-bf2c-99c3af896a41/resourceGroups/ConnectedMachinesRG/providers/Microsoft.HybridCompute/machines/azcm-rocky/overview
```

#### 3.2.2. Ubuntu

Run the bash script:

```console
root@azcm-ubuntu:~# chmod +x OnboardingScript.sh
root@azcm-ubuntu:~# ./OnboardingScript.sh
--2025-04-23 09:29:30--  https://gbl.his.arc.azure.com/azcmagent-linux
Resolving gbl.his.arc.azure.com (gbl.his.arc.azure.com)... 172.202.65.10, 172.202.64.10, 2603:1030:13:201::10, ...
Connecting to gbl.his.arc.azure.com (gbl.his.arc.azure.com)|172.202.65.10|:443... connected.
HTTP request sent, awaiting response... 200 OK
Length: unspecified [text/plain]
Saving to: ‘/tmp/install_linux_azcmagent.sh’

     0K .......... .......... .......... .                      366K=0.09s

2025-04-23 09:29:30 (366 KB/s) - ‘/tmp/install_linux_azcmagent.sh’ saved [32155]
Using 'curl' for downloads
Total physical memory: 4008704 kB
Platform type:  x86_64:Linux
Retrieving distro info from /etc/os-release...
Configuring for Ubuntu 24.04...
sudo: lsof: command not found
sudo: lsof: command not found
Get:1 http://security.ubuntu.com/ubuntu noble-security InRelease [126 kB]
Hit:2 http://archive.ubuntu.com/ubuntu noble InRelease
Get:3 http://archive.ubuntu.com/ubuntu noble-updates InRelease [126 kB]
Get:4 http://security.ubuntu.com/ubuntu noble-security/main amd64 Packages [781 kB]
Get:5 http://security.ubuntu.com/ubuntu noble-security/main Translation-en [147 kB]
Get:6 http://security.ubuntu.com/ubuntu noble-security/main amd64 Components [8956 B]
Get:7 http://security.ubuntu.com/ubuntu noble-security/restricted amd64 Packages [931 kB]
Get:8 http://archive.ubuntu.com/ubuntu noble-backports InRelease [126 kB]
Get:9 http://security.ubuntu.com/ubuntu noble-security/restricted Translation-en [190 kB]
Get:10 http://security.ubuntu.com/ubuntu noble-security/restricted amd64 Components [212 B]
Get:11 http://security.ubuntu.com/ubuntu noble-security/universe amd64 Packages [833 kB]
Get:12 http://security.ubuntu.com/ubuntu noble-security/universe Translation-en [181 kB]
Get:13 http://security.ubuntu.com/ubuntu noble-security/universe amd64 Components [52.2 kB]
Get:14 http://security.ubuntu.com/ubuntu noble-security/multiverse amd64 Packages [17.6 kB]
Get:15 http://security.ubuntu.com/ubuntu noble-security/multiverse Translation-en [3792 B]
Get:16 http://security.ubuntu.com/ubuntu noble-security/multiverse amd64 Components [208 B]
Get:17 http://archive.ubuntu.com/ubuntu noble/restricted amd64 Packages [93.9 kB]
Get:18 http://archive.ubuntu.com/ubuntu noble/restricted Translation-en [18.7 kB]
Get:19 http://archive.ubuntu.com/ubuntu noble/universe amd64 Packages [15.0 MB]
Get:20 http://archive.ubuntu.com/ubuntu noble/universe Translation-en [5982 kB]
Get:21 http://archive.ubuntu.com/ubuntu noble/universe amd64 Components [3871 kB]
Get:22 http://archive.ubuntu.com/ubuntu noble/multiverse amd64 Packages [269 kB]
Get:23 http://archive.ubuntu.com/ubuntu noble/multiverse Translation-en [118 kB]
Get:24 http://archive.ubuntu.com/ubuntu noble/multiverse amd64 Components [35.0 kB]
Get:25 http://archive.ubuntu.com/ubuntu noble-updates/main amd64 Packages [1026 kB]
Get:26 http://archive.ubuntu.com/ubuntu noble-updates/main Translation-en [223 kB]
Get:27 http://archive.ubuntu.com/ubuntu noble-updates/main amd64 Components [151 kB]
Get:28 http://archive.ubuntu.com/ubuntu noble-updates/restricted amd64 Packages [964 kB]
Get:29 http://archive.ubuntu.com/ubuntu noble-updates/restricted Translation-en [198 kB]
Get:30 http://archive.ubuntu.com/ubuntu noble-updates/restricted amd64 Components [212 B]
Get:31 http://archive.ubuntu.com/ubuntu noble-updates/universe amd64 Packages [1056 kB]
Get:32 http://archive.ubuntu.com/ubuntu noble-updates/universe Translation-en [266 kB]
Get:33 http://archive.ubuntu.com/ubuntu noble-updates/universe amd64 Components [367 kB]
Get:34 http://archive.ubuntu.com/ubuntu noble-updates/multiverse amd64 Packages [21.5 kB]
Get:35 http://archive.ubuntu.com/ubuntu noble-updates/multiverse Translation-en [4788 B]
Get:36 http://archive.ubuntu.com/ubuntu noble-updates/multiverse amd64 Components [940 B]
Get:37 http://archive.ubuntu.com/ubuntu noble-backports/main amd64 Packages [39.1 kB]
Get:38 http://archive.ubuntu.com/ubuntu noble-backports/main Translation-en [8676 B]
Get:39 http://archive.ubuntu.com/ubuntu noble-backports/main amd64 Components [7064 B]
Get:40 http://archive.ubuntu.com/ubuntu noble-backports/restricted amd64 Components [216 B]
Get:41 http://archive.ubuntu.com/ubuntu noble-backports/universe amd64 Packages [27.1 kB]
Get:42 http://archive.ubuntu.com/ubuntu noble-backports/universe Translation-en [16.5 kB]
Get:43 http://archive.ubuntu.com/ubuntu noble-backports/universe amd64 Components [15.8 kB]
Get:44 http://archive.ubuntu.com/ubuntu noble-backports/multiverse amd64 Components [212 B]
Fetched 33.3 MB in 7s (4978 kB/s)
Reading package lists... Done
Building dependency tree... Done
Reading state information... Done
100 packages can be upgraded. Run 'apt list --upgradable' to see them.
Reading package lists... Done
Building dependency tree... Done
Reading state information... Done
E: Unable to locate package packages-microsoft-prod
  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed
100  4298  100  4298    0     0  81745      0 --:--:-- --:--:-- --:--:-- 82653
Selecting previously unselected package packages-microsoft-prod.
(Reading database ... 72864 files and directories currently installed.)
Preparing to unpack .../packages-microsoft-prod.deb ...
Unpacking packages-microsoft-prod (1.1-ubuntu24.04) ...
Setting up packages-microsoft-prod (1.1-ubuntu24.04) ...
Get:1 https://packages.microsoft.com/ubuntu/24.04/prod noble InRelease [3600 B]
Get:2 https://packages.microsoft.com/ubuntu/24.04/prod noble/main arm64 Packages [17.7 kB]
Get:3 https://packages.microsoft.com/ubuntu/24.04/prod noble/main armhf Packages [8042 B]
Get:4 https://packages.microsoft.com/ubuntu/24.04/prod noble/main all Packages [576 B]
Get:5 https://packages.microsoft.com/ubuntu/24.04/prod noble/main amd64 Packages [28.1 kB]
Hit:6 http://archive.ubuntu.com/ubuntu noble InRelease
Hit:7 http://security.ubuntu.com/ubuntu noble-security InRelease
Hit:8 http://archive.ubuntu.com/ubuntu noble-updates InRelease
Hit:9 http://archive.ubuntu.com/ubuntu noble-backports InRelease
Fetched 58.1 kB in 1s (79.4 kB/s)
Reading package lists... Done
Reading package lists... Done
Building dependency tree... Done
Reading state information... Done
The following NEW packages will be installed:
  azcmagent
0 upgraded, 1 newly installed, 0 to remove and 100 not upgraded.
Need to get 80.8 MB of archives.
After this operation, 0 B of additional disk space will be used.
Get:1 https://packages.microsoft.com/ubuntu/24.04/prod noble/main amd64 azcmagent amd64 1.51.03008.304 [80.8 MB]
Fetched 80.8 MB in 11s (7216 kB/s)
debconf: delaying package configuration, since apt-utils is not installed
Selecting previously unselected package azcmagent.
(Reading database ... 72881 files and directories currently installed.)
Preparing to unpack .../azcmagent_1.51.03008.304_amd64.deb ...
Preinstall...install
Creating himds group ...
Creating himds account ...
Creating arcproxy account ...
Applying udev rule to access TPM...
Adding TPM udev rule
KERNEL=="tpm*", SUBSYSTEM=="tpm", TAG+="systemd", OWNER="root", GROUP="tss", MODE="0660"
Creating tss group ...
User 'himds' added to tss group
No TPM device detected
Unpacking azcmagent (1.51.03008.304) ...
Setting up azcmagent (1.51.03008.304) ...
Postinstall...configure
Creating new /var/opt/azcmagent/agentconfig.json
Creating new /etc/cron.d/azcmagent_autoupgrade
Netstat not installed.  Skipping IP port checking. The service needs to listen on 40342
Created symlink /etc/systemd/system/multi-user.target.wants/himdsd.service → /usr/lib/systemd/system/himdsd.service.
Checked guest config disabled:
Checked ext service disabled:
Checked arc proxy enabled: 0
Enabling arcproxyd
Created symlink /etc/systemd/system/multi-user.target.wants/arcproxyd.service → /usr/lib/systemd/system/arcproxyd.service.
Getting status via systemd
Arc GC service is not running.
Configuring Arc GC service ...
Found systemd service controller...for Arc GC Service
Created symlink /etc/systemd/system/multi-user.target.wants/gcad.service → /usr/lib/systemd/system/gcad.service.
Service configured through systemd service controller. Gc Service
Enabling gcad
Getting status via systemd
Arc GC service is not running.
STARTING Arc GC
Getting status via systemd
EXT service is not running.
Configuring EXT service ...
Found systemd service controller...for Extension Service
Created symlink /etc/systemd/system/multi-user.target.wants/extd.service → /usr/lib/systemd/system/extd.service.
Service configured through systemd service controller. Extension Service
Enabling extd
STARTING EXT
Scanning processes...
Scanning linux images...

Running kernel seems to be up-to-date.

No services need to be restarted.

No containers need to be restarted.

No user sessions are running outdated binaries.

No VM guests are running outdated hypervisor (qemu) binaries on this host.
Latest version of azcmagent is installed.
INFO    Connecting machine to Azure... This might take a few minutes.
INFO    Testing connectivity to endpoints that are needed to connect to Azure... This might take a few minutes.
To sign in, use a web browser to open the page https://microsoft.com/devicelogin and enter the code A8ZGT9KQ7 to authenticate.
```

Open `https://microsoft.com/devicelogin` and authenticate:

![image](https://github.com/user-attachments/assets/419e551a-1e09-4894-b7ba-acfb8f75252b)

![image](https://github.com/user-attachments/assets/8e4a88d8-c372-439e-830a-e15ea4e309ee)

![image](https://github.com/user-attachments/assets/ab11ae70-cbdf-4098-bd6e-46294ad7fe55)

![image](https://github.com/user-attachments/assets/0747d3a3-a5ca-4b44-a077-60a709d17227)

Installation proceeds automatically after authentication:

```console
  20% [==>            ]
  30% [===>           ]
  INFO    Creating resource in Azure...                 Correlation ID=640902b0-5155-4a11-8fa3-6a4a97d631f1 Resource ID=/subscriptions/3d0e465b-5f2e-4874-bf2c-99c3af896a41/resourceGroups/ConnectedMachinesRG/providers/Microsoft.HybridCompute/machines/azcm-ubuntu
  60% [========>      ]
  80% [===========>   ]
 100% [===============]
  INFO    Connected machine to Azure
INFO    Machine overview page: https://portal.azure.com/#@659330c7-4c00-42e9-b0d6-411ab5697f6e/resource/subscriptions/3d0e465b-5f2e-4874-bf2c-99c3af896a41/resourceGroups/ConnectedMachinesRG/providers/Microsoft.HybridCompute/machines/azcm-ubuntu/overview
```

### 3.3. Verify connection in Azure

![image](https://github.com/user-attachments/assets/afc9827a-c442-4eab-84a6-61a2fe8d612b)

![image](https://github.com/user-attachments/assets/67601950-f731-43a0-93e3-24cdbb94484f)

## 4. Azure Arc machines

![image](https://github.com/user-attachments/assets/cd8e09e9-2c22-4d07-9401-8964e684a9c6)
