> [!Tip]
>
> Service connection point is required for updates to work

## 1. Initiate update

ConfigMgr console → Administration → Updates and Servicing

Check for updates, select the desired update, then `Run prerequisite check` followed by `Install Update pack`

![](https://github.com/user-attachments/assets/fd98dad8-9b47-4b87-9b7f-5acf32c686cb)

![](https://github.com/user-attachments/assets/c1363463-f4a6-4253-98be-698759a05765)

![](https://github.com/user-attachments/assets/fe9d8104-3670-4b1e-8426-883c8d76d5fc)

![](https://github.com/user-attachments/assets/82506fe4-1154-4f9f-9a06-c6f7f885837a)

![](https://github.com/user-attachments/assets/353866e8-3a3a-4f1c-9c99-a70276f40e82)

![](https://github.com/user-attachments/assets/b40c2331-1d97-400f-8fc5-e4e7b17a176c)

![](https://github.com/user-attachments/assets/2c17f9c8-89fb-4b91-aa7a-a2865d706a36)

![](https://github.com/user-attachments/assets/8df915b1-d75a-4488-a68c-d481fc8ceb3f)

## 2. Monitor update progress

Check status of the update installation: ConfigMgr console → Monitoring → Updates and Servicing Status → Show Status

![](https://github.com/user-attachments/assets/b63e17d0-7733-4b5d-ad1c-a49729b68f99)

![](https://github.com/user-attachments/assets/70682128-af3f-4133-b4f8-124fd3e07f4d)

The update will take some time and it would look like the machine is idling at times, click on the step to see more task details:

![](https://github.com/user-attachments/assets/0db3d54a-ada9-49e6-b300-1530c718bc49)

The `SMS_EXECUTIVE` service will be stopped and disabled after some time as part of the update, and the ConfigMgr console will disconnect

![](https://github.com/user-attachments/assets/06ee8154-4389-4a4a-8b63-dcc7ebda5091)

Monitor the `C:\Program Files\Microsoft Configuration Manager\Logs\CMUpdate.log` file for upgrade progress

## 3. Update ConfigMgr console

![](https://github.com/user-attachments/assets/8ed826ed-8efa-4905-ac89-7375a038c181)

## 4. Update complete

- Microsoft Configuration Manager Version: 2503
- Console Version: 5.2503.1083.1000
- Site Version: 5.0.9135.1000

![](https://github.com/user-attachments/assets/e48960f6-daf1-4872-b553-af9225979aef)
