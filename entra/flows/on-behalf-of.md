## 1. Authorization code flow

### 1.1. Setup listener to capture authorization code

### 1.2. Trigger authorization code request with client app

### 1.3. Authorize permissions requested

![](https://github.com/user-attachments/assets/f3f68c41-f7f5-45c0-824a-3085365c5fd9)

![](https://github.com/user-attachments/assets/d6cf0615-3d85-41b9-8311-ce217da2798e)

![](https://github.com/user-attachments/assets/7aea210a-074e-48b0-a670-2d796ba5626a)

### 1.4. Redeem authorization code flow for client app token

```json
{
  "aud": "api://05417710-613b-483c-a5d6-f7a4120da964",
  "iss": "https://sts.windows.net/323626f5-1bfe-48cd-8902-ddfdfd44e1ce/",
  "iat": 1779062556,
  "nbf": 1779062556,
  "exp": 1779068202,
  "acr": "1",
  "aio": "AZQAa/8cAAAAYoxhWVZMRsiWkS/T7QN+eNzpM+2pwcpKan/xsGmZ8agYk/vxpiG/iT+pJHAMdn5HhRVByWL27u1C0amvN7WmJUXjMVGOF1sKYLyKRUSV6bgX7R50bfbaV31ru+v/fihW7+i7tppwea5uHLUw/ip7B0INCVFTYK9+zFO+aLiQbGKQyXlsl1sSvjK9/IimuzDp",
  "amr": [
    "pwd",
    "mfa"
  ],
  "appid": "629f37fd-84c5-411c-b04d-a0ffb3ef56a1",
  "appidacr": "1",
  "family_name": "Administrator",
  "given_name": "System",
  "ipaddr": "175.156.72.120",
  "name": "System Administrator",
  "oid": "38acbfa6-2f1f-46c1-a0ca-a4cf4eb6d55e",
  "rh": "1.AWMB9SY2Mv4bzUiJAt39_UThzhB3QQU7YTxIpdb3pBINqWQAALtjAQ.",
  "scp": "access",
  "sid": "004dd9ca-7ceb-cd96-5c0a-a8bca2c0c706",
  "sub": "HkG_Q72XzGnZwGG48RkR0vtWboYx3jYZqT7nbM1L1Dk",
  "tid": "323626f5-1bfe-48cd-8902-ddfdfd44e1ce",
  "unique_name": "admin@MngEnvMCAP398230.onmicrosoft.com",
  "upn": "admin@MngEnvMCAP398230.onmicrosoft.com",
  "uti": "fUhpqjW7KEmuIqkhTwCIAA",
  "ver": "1.0",
  "xms_ftd": "zc2jyt1D027H2PMinxjCneS31T8-EZc90Y36HFekUw8BdXNub3J0aC1kc21z"
}
```

## 2. Exchange client app token for middle app token

```json
{
  "aud": "https://graph.microsoft.com",
  "iss": "https://sts.windows.net/323626f5-1bfe-48cd-8902-ddfdfd44e1ce/",
  "iat": 1779062576,
  "nbf": 1779062576,
  "exp": 1779066490,
  "acct": 0,
  "acr": "1",
  "acrs": [
    "p1"
  ],
  "aio": "AcQAO/8cAAAAeWQ0tvL9HaypLcliYpMD42hroEYOvbm6MH0kFWGcgxk28EVeO6f8mWE7P2qCt6C2lyooIp6Gl5Zos6C8uyh+maegNHqCH9hBg0fsAh+dOFZ9xUgFqE/gASgjh5ydeKLkRhFurJ9WB8a9DF9GaRAYh0k9pEwe4e7t7resN6qjLBT37fNHtbkYzkmyrPp7isJAMwMxXWXt0+X1HIzXSxk/DmdoWJrNIonSnEwYyp0FRejP4GmWMETRqmmW67UHCa4E",
  "amr": [
    "pwd",
    "mfa"
  ],
  "app_displayname": "obo-middle-app",
  "appid": "05417710-613b-483c-a5d6-f7a4120da964",
  "appidacr": "1",
  "family_name": "Administrator",
  "given_name": "System",
  "idtyp": "user",
  "ipaddr": "175.156.72.120",
  "name": "System Administrator",
  "oid": "38acbfa6-2f1f-46c1-a0ca-a4cf4eb6d55e",
  "platf": "3",
  "puid": "10032004E18EB399",
  "rh": "1.AWMB9SY2Mv4bzUiJAt39_UThzgMAAAAAAAAAwAAAAAAAAAAAALtjAQ.",
  "scp": "SecurityAlert.Read.All SecurityIncident.Read.All ThreatHunting.Read.All profile openid email",
  "sid": "004dd9ca-7ceb-cd96-5c0a-a8bca2c0c706",
  "sub": "o-YHRzN55wxQ5HolG1SS2jCEYS-30KeFqtVlJDH45UQ",
  "tenant_region_scope": "NA",
  "tid": "323626f5-1bfe-48cd-8902-ddfdfd44e1ce",
  "unique_name": "admin@MngEnvMCAP398230.onmicrosoft.com",
  "upn": "admin@MngEnvMCAP398230.onmicrosoft.com",
  "uti": "A36ReTUXbEy7KP_pSQKVAA",
  "ver": "1.0",
  "wids": [
    "f2ef992c-3afb-46b9-b7cf-a126ee74c451",
    "194ae4cb-b126-40b2-bd5b-6091b380977d",
    "b79fbf4d-3ef9-4689-8143-76b194e85509"
  ],
  "xms_acd": 1771468171,
  "xms_act_fct": "3 9",
  "xms_ftd": "p3pDkzwyiL-HBfQMX9vGIAoFp2wBZvapnTlsiuj0WpwBdXNub3J0aC1kc21z",
  "xms_idrel": "1 16",
  "xms_pftexp": 1779152890,
  "xms_st": {
    "sub": "HkG_Q72XzGnZwGG48RkR0vtWboYx3jYZqT7nbM1L1Dk"
  },
  "xms_sub_fct": "3 6",
  "xms_tcdt": 1752658764,
  "xms_tnt_fct": "3 16"
}
```
