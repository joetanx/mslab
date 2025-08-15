## 1. Configure Active Directory forest discovery

ConfigMgr console → Administration → Hierachy Configuration → Discovery Methods

![](https://github.com/user-attachments/assets/fff3ac6c-dc1e-4c85-89ee-c14a5819f96e)

![](https://github.com/user-attachments/assets/d7376225-b21c-4624-a345-ad6bf52d014b)

## 2. Verify boundary created from discovery

ConfigMgr console → Administration → Hierachy Configuration → Boundaries

![](https://github.com/user-attachments/assets/457593d2-8e62-424c-bc09-e43279d9436f)

## 3. Create boundary group to associate boundary and site server

ConfigMgr console → Administration → Hierachy Configuration → Boundary Groups → Create Boundary Group

![](https://github.com/user-attachments/assets/edc40cdf-cb2a-4b50-991d-a3f8fc9c234d)

General → Boundaries → Add... → select the Active Directory boundary:

![](https://github.com/user-attachments/assets/e7745143-eb57-447f-9c96-40b34fb0ab4c)

![](https://github.com/user-attachments/assets/92f0ffcb-e6cc-4d33-868b-2b1a7293d322)

References → Select site system servers → Add... → select the site system:

![](https://github.com/user-attachments/assets/c0afd6c1-884e-4378-a61f-31c1d268b3cf)

![](https://github.com/user-attachments/assets/393cc69e-ea19-40f6-bc2c-d74f565100de)

![](https://github.com/user-attachments/assets/12798d4c-0c02-4172-b7fa-4ee2813732c9)
