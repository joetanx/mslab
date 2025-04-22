## 1. Create public VNet

![image](https://github.com/user-attachments/assets/8cdae168-dc6c-440f-be1b-12555925edf5)

### 1.1. Configure Firewall and Bastion in VNet security settings

![image](https://github.com/user-attachments/assets/3f2bb433-c219-416a-9b14-221fbbdafcac)

### 1.2. Configure subnets

![image](https://github.com/user-attachments/assets/b1745c64-979d-4b74-ad92-8eb3538560d4)

## 2. Create NAT gateway

![image](https://github.com/user-attachments/assets/69130f75-96ed-4f97-a8ac-9f7c8be73fae)

### 2.1. Configure outbound IP address

![image](https://github.com/user-attachments/assets/271d91c8-e027-4dde-a2da-1fea310d54e9)

### 2.2. Associate with firewall subnet

![image](https://github.com/user-attachments/assets/877e4f71-e2a1-4bd0-a7a4-11b25c2b549c)

## 3. Create private VNet

![image](https://github.com/user-attachments/assets/12dbe8bb-ddaa-42a5-8cbf-d2bb64734f1c)

### 3.1. VNet security settings

![image](https://github.com/user-attachments/assets/1e01a05f-5149-45cc-ae83-38431e88b137)

### 3.2. Configure subnets

![image](https://github.com/user-attachments/assets/2c62f992-f79a-46b1-ac64-d15397488248)

## 4. Create peering between public and private VNets

### 4.1. Configure peering settings

VNet peering can be initiated from either VNet:
- Remote VNet: the VNet peer (`PrvVNet` in this example) to be initiated towards
- Local VNet the current VNet (`PubNet` in this example) that the configuration is initiated from

![image](https://github.com/user-attachments/assets/23a1b9c1-44f4-4020-af57-367cfd230c11)

### 4.2. Verify peering sync status and peering state

![image](https://github.com/user-attachments/assets/a0a70c31-dd2f-48d7-9371-3850026d4b15)

![image](https://github.com/user-attachments/assets/6f2fa4e7-e416-441e-b571-87e8e3a96477)

## 5. Configure outbound routing from private subnet to internet via firewall

### 5.1. Create route table

![image](https://github.com/user-attachments/assets/07cc8bd6-07cb-4ec0-8e62-9fe9f95193bb)

### 5.2. Create route

### 5.2.1. Check firewall IP address

![image](https://github.com/user-attachments/assets/e01103d4-4ed5-4231-8573-ac42cda5faa1)

### 5.2.2. Add route

- Default (Internet) route: `0.0.0.0/0`
- Next hop address: firewall address `10.0.1.68`

![image](https://github.com/user-attachments/assets/7603eed0-2ddc-478e-8a71-ec2f0f65b132)

### 5.3. Associate route table to private subnet

![image](https://github.com/user-attachments/assets/654cb3de-3061-4b7b-87dc-7eff01957c28)

## 6. Configure firewall policy for public VNet

![image](https://github.com/user-attachments/assets/9dac4f2e-140a-4015-be14-b827faf80230)

## 7. Create VM to test outbound connectivity via NAT gateway

### 7.1. Configure instance details and credentials

![image](https://github.com/user-attachments/assets/2e3246d2-7c60-402b-9d87-1dbb53b922ed)

### 7.2. Configure networking

![image](https://github.com/user-attachments/assets/f46d3625-ef0d-450e-8552-8c4fea00ce92)

![image](https://github.com/user-attachments/assets/ed8a7016-34b9-4570-84f8-98cc007c76a4)

## 8. Test connection

### 8.1. Check NAT gateway public IP

![image](https://github.com/user-attachments/assets/c0f7af89-ef06-47ce-a869-72cd3251d2ae)

### 8.2. Check bastion subnet address range

![image](https://github.com/user-attachments/assets/3c3ed5c3-da5d-45cb-bc77-b9fbd3cff538)

### 8.3. Connect to VM

Verify that:
1. Outbound traffic to internet uses NAT gateway
2. SSH/RDP access to VM is established through bastion subnet address range

![image](https://github.com/user-attachments/assets/9cc963d3-b0ac-419d-88e2-e4cad53a2fbc)

> [!Tip]
> 
> The error below occurs if the allowing rule is not configured in the firewall policy:
> 
> `Action: Deny. Reason: No rule matched. Proceeding with default action.`
