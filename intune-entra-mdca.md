## 1. How Intune, Entra (Conditional Access) and MDCA (Conditional Access App Control) work

### 1.1. Intune - Device Compliance Signal

- Role: Intune is the endpoint management solution that evaluates whether a device meets compliance policies you define (e.g., encryption, OS version, patch level, jailbroken/rooted status).
- Integration:
  - Devices are registered or enrolled in Intune.
  - Compliance policies are defined and assessed on the device.
  - Intune sends the device compliance state (Compliant, Noncompliant, Not evaluated) to Entra ID (Azure AD).
- Output: Device compliance is surfaced as a signal that Entra can consume in conditional access.

### 1.2. Entra Conditional Access - Access Control Engine

- Role: Entra (Azure AD Conditional Access) is the decision-making layer that evaluates user, device, app, and risk signals to determine access to resources.
- Integration:
  - It consumes device compliance signals from Intune.
  - It can enforce conditions like:
    - Require device to be marked as compliant by Intune.
    - Require MFA.
    - Block/allow based on location, risk score (from Entra ID Protection), or platform.
  - CA policies apply at the authentication stage (pre-access).
- Output: Access is either allowed, blocked, or redirected (for example, to MDCA session control).

### 1.3. Defender for Cloud Apps (MDCA) - Session and Activity Control

- Role: MDCA extends conditional access beyond the point of login to control what users do inside a session (granular, real-time activity and data protections).
- Integration:
  - Entra CA policies can be configured to route a session through MDCA by choosing "Use Conditional Access App Control".
  - This allows you to apply MDCA session policies, such as:
    - Monitor/download/upload/clipboard control.
    - Block download of sensitive files unless the device is compliant.
    - Apply watermarking to documents in-session.
  - MDCA leverages both Entra signals (user identity, risk, app) and Intune signals (device compliance, managed/unmanaged device) to decide session enforcement.
- Output: Granular, real-time controls *after access is granted*.

### 1.4. How They Work Together (Flow Example)

1. User signs in → Entra Conditional Access policy triggers.
2. CA checks signals:
   - User risk (Entra ID Protection).
   - Device compliance (from Intune).
   - Application (cloud app, SaaS, etc.).
3. Decision:
   - If conditions aren’t met → block or require MFA.
   - If compliant but session needs monitoring → route to MDCA session control.
4. In-session (via MDCA reverse proxy):
   - Controls download/upload actions based on device compliance, data sensitivity, or session context.

In summary:
- Intune = evaluates and provides device compliance.
- Entra Conditional Access = central decision point, enforcing pre-access conditions and routing to MDCA.
- MDCA = applies post-access, real-time session and activity controls for deeper protection.

## 2. Entra Conditional Access vs MDCA Session / Activity Policies

### 2.1. Entra Conditional Access (CA)

- Stage: Enforced at authentication / pre-access (when a user tries to sign in).
- Scope: Controls whether and how access is granted.
- Signals evaluated:
  - User (identity, role, risk score, group membership).
  - Device (Intune compliance, Hybrid-joined, OS/platform).
  - Location (IP, country, trusted network).
  - Application (specific app or all apps).
  - Session risk (via Entra ID Protection).
- Controls available:
  - Grant/Block access.
  - Require MFA.
  - Require compliant device.
  - Require app protection policy.
  - Route session through MDCA (`Use Conditional Access App Control`).
- Think of it as: The gatekeeper - deciding whether the user can get in, and under what conditions.

### 2.2. MDCA (Microsoft Defender for Cloud Apps) Session / Activity Policies

- Stage: Enforced in-session / post-access (after the user has already logged in).
- Scope: Controls what the user can do inside the app session.
- Signals evaluated:
  - User identity (from Entra).
  - Device compliance / managed vs unmanaged (from Intune + Entra).
  - Session context (browser, IP, download attempt, upload attempt).
  - Data sensitivity (integrates with Microsoft Purview Information Protection for labels).
- Controls available:
  - Block download/upload/copy/paste/print.
  - Apply real-time monitoring and alerts.
  - Require documents to be protected (e.g., encrypted) before download.
  - Watermark documents viewed in browser.
  - Govern file sharing (e.g., external sharing restrictions).
- Think of it as: The security guard inside the building - watching user actions and stopping risky behavior in real time.

### ️2.3. Quick Comparison

| Feature | Entra Conditional Access (CA) | MDCA Session/Activity Policies |
|---|---|---|
| Timing | Before access (authentication stage) | After access (in-session, real-time) |
| Decision | Allow / Deny / Require MFA / Require compliance | Allow / Block / Restrict actions (download, upload, etc.) |
| Focus | Who can access, from what device, under what conditions | What the user can do once inside the app |
| Example Use Case | "Only compliant devices can access SharePoint" | "Block download of sensitive files from SharePoint on unmanaged devices" |

In short:
- Entra CA = "Should you get in, and how?"
- MDCA policies = "Now that you’re in, what can you do?"
