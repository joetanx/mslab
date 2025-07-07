## 0. Overview

|Feature|Description|
|---|---|
|Sensitive Information Types|Predefined or custom patterns to detect sensitive data.|
|DLP|Prevent data leaks or exposure by setting policies for sensitive data handling.|
|Sensitivity Labels|Classify data based on its sensitivity, applying protection and controls automatically or manually.|
|Retention Labels|Manage data lifecycle by retaining or deleting data based on compliance policies.|
|Insider Risk Management|Monitor and mitigate risks posed by insiders through behavior monitoring.|
|eDiscovery|Conduct legal investigations by identifying and preserving data for review.|
|Data Security Posture Management|Continuously monitor and improve the security of your data against internal and external threats.|

## 1. Sensitive Information Type

Sensitive Information Types (SITs) are predefined or custom templates in Microsoft Purview that identify and classify data that may contain sensitive information. These could include personal data, credit card numbers, national identification numbers, health information, etc.

### 1.1. Key features

- **Predefined types**: Includes things like Social Security numbers, credit card numbers, passport numbers, and more.
- **Customizable**: You can define your own sensitive information types tailored to your specific business needs.
- **Detection**: When data is scanned by Purview, the system can automatically identify sensitive information types within your data.

## 2. Data Loss Prevention (DLP

Data Loss Prevention (DLP) is a security feature that helps prevent sensitive information from being accidentally shared or exposed. Purview provides DLP tools to protect your data by identifying potential risks and blocking or restricting actions.

### 2.1. Key features

- **Rules**: DLP policies can be created to prevent sensitive data from being shared externally or with unauthorized users.
- **Notifications**: Alerts and notifications can be set up to inform administrators about potential violations.
- **Integration**: DLP can be integrated with Microsoft 365 apps, SharePoint, Teams, OneDrive, etc., ensuring that sensitive data isn't shared or accessed inappropriately.

## 3. Information Protection (Sensitivity Labels

Sensitivity Labels allow you to classify and protect data based on its sensitivity level. You can assign labels to files, emails, or other data types, which apply security controls like encryption, watermarking, or access restrictions.

### 3.1. Key Features

- **Protection**: Applying a sensitivity label can trigger encryption, preventing unauthorized access to data.
- **Visibility**: Labels help users identify how sensitive a piece of information is, improving data handling practices.

### 3.2. Automatic vs. Manual Labeling**

- **Manual Labeling**: Users manually apply sensitivity labels to documents and emails based on the perceived sensitivity level (e.g., Confidential, Highly Confidential). This approach gives users control but can be prone to human error.
- **Automatic Labeling**: This is a policy-driven approach where sensitivity labels are automatically applied based on predefined conditions, such as the presence of sensitive information types (e.g., credit card numbers or personal identifiers). For example, if a document contains a credit card number, a "Confidential" label can be automatically applied.

## 4. Data Lifecycle Management (Retention Labels

Retention Labels manage how long data is kept and what happens to it when it is no longer needed. Retention labels can be applied to documents, emails, and other records to ensure compliance with regulations by retaining data for a specified time period or deleting it after a certain duration.

### 4.1. Key Features

- **Retention Period**: Set how long data must be retained based on compliance or business requirements.
- **Disposition**: Automatically delete or move data to lower-cost storage after a certain retention period.
- **Legal Holds**: Prevent deletion of specific records if they are under legal investigation or litigation.

## 5. Insider Risk Management

Insider Risk Management (IRM) helps detect and mitigate risks posed by insiders (employees, contractors, etc.) who might inadvertently or maliciously expose data. The goal is to protect against threats without compromising user privacy.

### 5.1. Key Features

- **Risk Indicators**: Use machine learning to monitor behaviors (such as copying sensitive data to external devices or sharing files with unauthorized users) that could indicate risky actions.
- **Case Management**: Create cases for investigation and track the resolution of potential risks.
- **Policies**: Configure risk policies based on user behaviors and sensitive actions, like excessive sharing of files or downloading sensitive data.

## 6. eDiscovery (Investigations)

eDiscovery (electronic discovery) allows organizations to identify, preserve, and collect data for legal and regulatory investigations. It is crucial for organizations that need to manage legal compliance, particularly around data privacy.

### 6.1. Key Features

- **eDiscovery cases**: Allow you to collect, hold, and analyze data for investigations, and manage litigation processes efficiently.
- **Audit Trails**: Track and review actions for compliance audits or legal investigations.

### 6.2. eDiscovery vs. Data Security Investigations

- **eDiscovery**: Primarily focused on retrieving and preserving data for legal proceedings. It’s about identifying potentially relevant data that might be required in litigation or legal cases.
  - **Search & Hold**: Allows the legal team to perform searches across data sources and place data on hold to prevent it from being deleted or altered.
  - **Export**: After identifying relevant data, eDiscovery allows you to export it for further analysis or legal review.

- **Data Security Investigations**: These focus more on security incidents, such as potential breaches or unauthorized access to data. While eDiscovery looks at legal requirements, data security investigations look at preventing or responding to security incidents.
  - **Audit Logs**: Examine who accessed what data, when, and for what purpose.
  - **Risk Mitigation**: Investigate anomalies that could be indicative of security threats.

## 7. Data Security Posture Management

Data Security Posture Management (DSPM) helps you continuously monitor the security of your organization's data and mitigate potential risks. It's part of an overall strategy to ensure that your data is protected from both internal and external threats.

### 7.1. Key Features

- **Assessment**: Continuously assess the state of your data security by evaluating permissions, vulnerabilities, and potential exposure risks.
- **Remediation**: Automated recommendations or tools to fix security posture issues, such as overly broad permissions or access controls.
- **Compliance**: Helps ensure that data security controls align with industry regulations, such as GDPR, HIPAA, or CCPA.
