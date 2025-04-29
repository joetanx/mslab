## 1. Overview

### 1.1. SecOps objectives

1. Monitoring
2. Detection
3. Response

### 1.2. Challenges in SecOps

1. Alert fatigue
    - false positive
    - low priority alerts
2. Lack of skilled personnel
3. Evolving threat landscape
4. Tools integration
5. Incident response time
6. Maintaining compliance
7. Continuous monitoring
8. Lack of context
9. Limited budget

### 1.3. SecOps team structure tiers

#### Analysts

1. Tier 1: Alert Analysts - first line of defense, responsible for monitoring security alerts, filtering false positives, and escalating incidents that require deeper investigation
2. Tier 2: Incident Responsders (+ digital forensics) - conduct in-depth assessments of security incidents, analyze attack patterns, and implement containment and recovery strategies
3. Tier 3: Threat Hunters - most experienced analysts proactively hunt for threats, investigate complex incidents, and develop advanced detection techniques

#### Others

1. SOC Engineers - focus on designing, implementing, and maintaining the security infrastructure that supports the SOC team
2. SOC Managers - oversee the entire security operations team and ensure effective cybersecurity strategies

### 1.4. SecOps technologies

1. SIEM
2. SOAR
3. CTI
4. VM
5. XDR
6. CNAPP
7. NTA

### 1.5. Attack lifecycle

| Cyber Kill Chain Phase | MITRE ATT&CK Tactics |
|---|---|
| Reconnaissance | Reconnaissance |
| Weaponization | Resource Development |
| Delivery | Initial Access |
| Exploitation | Execution |
| Installation | Persistence,<br>Privilege Escalation |
| Command & Control | Defense Evasion,<br>Credential Access,<br>Discovery,<br>Lateral Movement,<br>Command and Control |
| Actions on Objectives | Collection,<br>Exfiltration,<br>Impact |

### 1.6. Incident response lifecycle

1. Triage
2. Investigation and analysis
3. Containment
4. Eradiction
5. Recovery
6. Lessons learned

#### Post-incident analysis: learning from experience to strengthen defenses

1. Analyzing root and contributing causes
2. Incorporating lessons into upgrades
3. Informing strategic decision-making

### 1.7. Cyber threat intelligence

- Increased situational awareness: Threat intelligence can help organizations to understand the threats they face and to prioritize their security efforts.
- Improved decision-making: Threat intelligence can help organizations to make better decisions about their security posture.
- Reduced risk: Threat intelligence can help organizations to reducetheir risk of being attacked.
- Enhanced security posture: Threat intelligence can help organizations to enhance their security posture by identifying and mitigating threats.

- Connecting detections to known campaigns
- Hunting with intelligence-derived context
- Adapting defenses with threat intelligence

### 1.8. Automation

1. Orchestrating alert enrichment
2. Automate routine containment
3. Operationalize threat hunting
4. Case management and response activities documentation

### 1.9. SOC KPIs

- Reduced mean time to detect threats signals enhanced vigilance in identifying malicious post-compromise activities faster amid the noise.
- A lower mean time to respond denotes improved prioritization and promptness in initiating investigations when novel alerts sound.
- Faster mean time to contain verifies upgraded protocols blocking wider adversarial spread after initial confirmations.
- Higher true positive rates over false positives indicate properly tuned analytics with minimized alarm fatigue.
- Wider containment automation coverage supplemented by human effort was still essential.
