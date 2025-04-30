## 1. Key SecOps Functions

1. Monitoring
2. Detection
3. Response

### 1.1. Challenges in SecOps

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

### 1.2. SecOps team structure

#### Alert Analysts (Tier 1)

First line of defense, responsible for monitoring security alerts, filtering false positives, and escalating incidents that require deeper investigation

#### Incident Responsders (+ digital forensics) (Tier 2)

Conduct in-depth assessments of security incidents, analyze attack patterns, and implement containment and recovery strategies

#### Threat Hunters (Tier 3)

Most experienced analysts proactively hunt for threats, investigate complex incidents, and develop advanced detection techniques

#### SOC Engineers (and SOC Architects)

Focus on designing, implementing, and maintaining the security infrastructure that supports the SOC team

### 1.3. SecOps technologies

1. SIEM
2. SOAR
3. CTI
4. VM
5. XDR
6. CNAPP
7. NTA

## 2. Incident Response

### 2.1. Attack Lifecycle

| Cyber Kill Chain Phase | MITRE ATT&CK Tactics |
|---|---|
| Reconnaissance | Reconnaissance |
| Weaponization | Resource Development |
| Delivery | Initial Access |
| Exploitation | Execution |
| Installation | Persistence,<br>Privilege Escalation |
| Command & Control | Defense Evasion,<br>Credential Access,<br>Discovery,<br>Lateral Movement,<br>Command and Control |
| Actions on Objectives | Collection,<br>Exfiltration,<br>Impact |

### 2.2. Incident Response Lifecycle

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

### 2.3. Automation and Orchestration (9. Incident Response Automation and Orchestration)

1. Orchestrating alert enrichment
2. Automate routine containment
3. Operationalize threat hunting
4. Case management and response activities documentation

## 3. Security Analytics

### 3.1. Analysis Techniques (4. Log and Event Analysis)

### 3.2. AIML Advanced Analytics (8. Security Analytics and Machine Learning in SOC)

## 4. Threat Intelligence and Threat Hunting (13. Threat Intelligence and Advanced Threat Hunting)

- Increased situational awareness: Threat intelligence can help organizations to understand the threats they face and to prioritize their security efforts.
- Improved decision-making: Threat intelligence can help organizations to make better decisions about their security posture.
- Reduced risk: Threat intelligence can help organizations to reducetheir risk of being attacked.
- Enhanced security posture: Threat intelligence can help organizations to enhance their security posture by identifying and mitigating threats.

- Connecting detections to known campaigns
- Hunting with intelligence-derived context
- Adapting defenses with threat intelligence

## 5. SOC Engineering (7. Security Information and Event Management (SIEM))

### 5.1. SOC and mulit-tenant architecture

### 5.2. Capacity and data retention planning

## 6. Performance Metrics (10. SOC Metrics and Performance Measurement)

- Reduced mean time to detect threats signals enhanced vigilance in identifying malicious post-compromise activities faster amid the noise.
- A lower mean time to respond denotes improved prioritization and promptness in initiating investigations when novel alerts sound.
- Faster mean time to contain verifies upgraded protocols blocking wider adversarial spread after initial confirmations.
- Higher true positive rates over false positives indicate properly tuned analytics with minimized alarm fatigue.
- Wider containment automation coverage supplemented by human effort was still essential.
