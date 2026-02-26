## 1. Objects in Entra agent identity

|Object|`@odata.type`|Inherits from|Description|
|---|---|---|---|
|Agent identity blueprint|[agentIdentityBlueprint](https://learn.microsoft.com/en-us/graph/api/resources/agentidentityblueprint)|[application](https://learn.microsoft.com/en-us/graph/api/resources/application)|Serves as a template for creating agent identities within the Microsoft Entra ID ecosystem.|
|Agent identity blueprint principal|[agentIdentityBlueprintPrincipal](https://learn.microsoft.com/en-us/graph/api/resources/agentidentityblueprintprincipal)|[servicePrincipal](https://learn.microsoft.com/en-us/graph/api/resources/serviceprincipal)|• Instantiated from agentIdentityBlueprintPrincipal object<br>• Used to create agent identities within a Microsoft Entra ID tenant<br>• Used to perform various identity management operations that affect all agent identities created|
|Agent identity|[agentIdentity](https://learn.microsoft.com/en-us/graph/api/resources/agentidentity)|[servicePrincipal](https://learn.microsoft.com/en-us/graph/api/resources/serviceprincipal)|Account used by AI agents to authenticate within the Microsoft Entra ID ecosystem.|
|Agent User|[agentUser](https://learn.microsoft.com/en-us/graph/api/resources/agentuser)|[user](https://learn.microsoft.com/en-us/graph/api/resources/user)|• Specialized subtype of user identity in Microsoft Entra ID designed for AI-powered applications (agents) that need to function as digital workers.<br>• Agent users enable agents to access APIs and services that specifically require user identities, receiving tokens with `idtyp=user` claims.<br>• Agent users are distinct from human [users](https://learn.microsoft.com/en-us/graph/api/resources/user) and they only interlinked to users through relationships such as owner, sponsor, and manager.|

## 2. APIs and permissions requried to provision Entra agent identity objects

|API|Minimum permission<br>([Entra permission reference](https://learn.microsoft.com/en-us/graph/permissions-reference))|Remarks|
|---|---|---|
|Create agent identity blueprint[🔗](https://learn.microsoft.com/en-us/graph/api/agentidentityblueprint-post)|`AgentIdentityBlueprint.Create`|
|Create agent identity blueprint principal[🔗](https://learn.microsoft.com/en-us/graph/api/agentidentityblueprintprincipal-post)|`[AgentIdentityBlueprintPrincipal.Create`||
|Add client secret to agent identity blueprint[🔗](https://learn.microsoft.com/en-us/graph/api/agentidentityblueprint-addpassword)|`AgentIdentityBlueprint.AddRemoveCreds.All`||
|Remove client secret from agent identity blueprint[🔗](https://learn.microsoft.com/en-us/graph/api/agentidentityblueprint-removepassword)|`[AgentIdentityBlueprint.AddRemoveCreds.All`||
|Add federated identity credential (FIC) to agent identity blueprint[🔗](https://learn.microsoft.com/en-us/graph/api/federatedidentitycredential-post)|`Application.ReadWrite.OwnedBy`<br>`Application.ReadWrite.All]` (preferred)|The application performing this action is unlikely to be the owner of the agent identity blueprint; hence, `Application.ReadWrite.All` is preferred|
|Remove federated identity credential (FIC) from agent identity blueprint[🔗](https://learn.microsoft.com/en-us/graph/api/federatedidentitycredential-delete)|`Application.ReadWrite.OwnedBy`<br>`Application.ReadWrite.All` (preferred)|The application performing this action is unlikely to be the owner of the agent identity blueprint; hence, `Application.ReadWrite.All` is preferred|
|Create agent identity[🔗](https://learn.microsoft.com/en-us/graph/api/agentidentity-post)|`AgentIdentity.CreateAsManager`<br>`AgentIdentity.Create.All`|Performed by agent identity blueprint; `AgentIdentity.CreateAsManager` is automatically granted to the agent identity blueprint|
|Grant application permission (appRole) to agent identity blueprint[🔗](https://learn.microsoft.com/en-us/graph/api/serviceprincipal-post-approleassignments)|`AppRoleAssignment.ReadWrite.All`<br>`Application.Read.All`||
|Create agent user[🔗](https://learn.microsoft.com/en-us/graph/api/agentuser-post)|`AgentIdUser.ReadWrite.IdentityParentedBy`|Performed by agent identity blueprint; `AgentIdUser.ReadWrite.All` is needed if using another application to create agent user|
|List agent identity blueprint[🔗](https://learn.microsoft.com/en-us/graph/api/agentidentityblueprint-list)|`Application.Read.All`||
|List agent identity blueprint principal[🔗](https://learn.microsoft.com/en-us/graph/api/agentidentityblueprintprincipal-list)|`Application.Read.All]`||
|List agent identity[🔗](https://learn.microsoft.com/en-us/graph/api/agentidentity-list)|`Application.Read.All]`||
|List agent user[🔗](https://learn.microsoft.com/en-us/graph/api/agentuser-list)|`User.ReadBasic.All`|
|Delete agent identity blueprint[🔗](https://learn.microsoft.com/en-us/graph/api/agentidentityblueprint-list)|`AgentIdentityBlueprint.DeleteRestore.All`|Agent identity blueprint principal is deleted when agent identity blueprint is deleted|
|Delete agent identity[🔗](https://learn.microsoft.com/en-us/graph/api/agentidentity-list)|`AgentIdentity.DeleteRestore.All`||
|Delete agent user[🔗](https://learn.microsoft.com/en-us/graph/api/agentuser-list)|`AgentIdUser.ReadWrite.IdentityParentedBy`||
|[🔗]()|``||
|[🔗]()|``||
|[🔗]()|``||
|[🔗]()|``||
|[🔗]()|``||
|[🔗]()|``||
|[🔗]()|``||
|[🔗]()|``||
|[🔗]()|``||
|[🔗]()|``||
