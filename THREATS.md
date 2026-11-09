# SecureDocs – Threat Model

## 1. Overview

SecureDocs is a secure document-sharing platform built using Flask. It allows users to upload, store, share, and access sensitive documents with controlled permissions.

The application uses Fernet encryption to protect stored files, authentication controls to prevent unauthorized access, and audit logging to track document-related activities.

This document describes the major security threats considered in SecureDocs, the protections currently implemented, and the remaining security limitations.

## 2. Identified Threats and Mitigations

### 2.1 Unauthorized Access

**Threat:**  
An attacker may try to access private documents or user accounts without permission.

**Mitigation:**

- User authentication is required to access protected features.
- Password complexity rules are enforced during registration.
- Login attempts are rate-limited.
- Accounts are temporarily locked after five consecutive failed login attempts.
- Deactivated or revoked accounts are denied access.

**Status:** Implemented.

### 2.2 Data Exposure at Rest

**Threat:**  
If an attacker gains access to the server's file storage, uploaded documents could be exposed.

**Mitigation:**

- Uploaded files are encrypted using Fernet before being stored.
- Encrypted files are saved with UUID-based filenames.
- Original plaintext files are not stored on disk.
- Files are decrypted in memory only after authorization.

**Status:** Implemented.

### 2.3 Unauthorized Document Sharing

**Threat:**  
A user may attempt to access a document that has not been shared with them or perform actions beyond their granted permissions.

**Mitigation:**

- Document owners can share files with specific users.
- Three permission levels are supported:
  - **View Only:** Allows viewing but blocks downloading and editing.
  - **View & Download:** Allows viewing and downloading.
  - **Full Access/Edit:** Allows viewing, downloading, and replacing documents.
- Unauthorized operations are rejected.
- Owners and administrators can revoke individual shares.

**Status:** Implemented.

### 2.4 Expired or Revoked Access

**Threat:**  
A recipient may continue accessing a document after the sharing period ends or access is revoked.

**Mitigation:**

- Document shares can have an optional expiration date and time.
- Expired shares are denied access.
- Owners and administrators can revoke document-sharing permissions.
- Revoked or deactivated user accounts are prevented from accessing protected resources.

**Status:** Implemented.

### 2.5 Session Hijacking and CSRF Attacks

**Threat:**  
An attacker may try to misuse an authenticated session or trick a logged-in user into performing unwanted actions.

**Mitigation:**

- HttpOnly cookies help prevent JavaScript from reading session cookies.
- SameSite cookie settings help reduce cross-site request risks.
- Session expiration is configured.
- Flask-WTF CSRF protection is used for supported form submissions.

**Status:** Basic protections implemented.

### 2.6 Malicious File Uploads

**Threat:**  
Attackers may upload unsupported, oversized, or potentially harmful files.

**Mitigation:**

- Only approved file extensions are accepted.
- File uploads are limited to 16 MB.
- UUID filenames help prevent filename collisions and path manipulation.
- Uploaded files are encrypted before storage.

**Status:** Basic validation implemented. File signature inspection and advanced malware scanning are not currently integrated.

### 2.7 Audit Log Tampering

**Threat:**  
An attacker or unauthorized person may attempt to modify or delete activity records to hide suspicious actions.

**Mitigation:**

- The application records important events, including login attempts, uploads, views, downloads, edits, sharing, revocation, and unauthorized access.
- Audit records include user ID, document ID, IP address, user agent, timestamp, and operation status.
- Document owners can review document activity.
- Administrators can access global audit records, apply filters, and export logs as CSV.

**Status:** Application-level append-only logging implemented. The logs are not yet protected by an external immutable storage system or cryptographic tamper-evident mechanism.

### 2.8 Encryption Key Exposure

**Threat:**  
If the Fernet encryption key is exposed, an attacker who obtains encrypted files may be able to decrypt them.

**Mitigation:**

- The encryption key is configured through an environment variable rather than hardcoded in application source code.
- The `.env` file should not be committed to GitHub.
- Access to the server environment should be restricted.

**Status:** Basic key protection implemented. Centralized key management and key rotation are not currently integrated.

### 2.9 Denial-of-Service Attacks

**Threat:**  
An attacker may send excessive requests or repeated login attempts to affect application availability.

**Mitigation:**

- Flask-Limiter is used to restrict request frequency.
- Login attempts are limited.
- File uploads have a maximum size of 16 MB.

**Status:** Basic protections implemented. Advanced network-level DDoS protection is not integrated.

## 3. Current Security Limitations

The following improvements are planned for future versions:

- Cloud object storage integration is not currently available. Files are stored locally in encrypted form.
- A single application-wide Fernet key is used. Envelope encryption and centralized key management are not implemented.
- Large files are decrypted in memory, which may affect scalability.
- Email notifications for document sharing are not integrated.
- Password reset through email verification is not implemented.
- Multi-factor authentication (MFA) is not currently available.
- File validation does not include binary file signature inspection or advanced malware scanning.
- Audit logs are not stored in a separate immutable logging service.

## 4. Future Security Improvements

Future versions of SecureDocs may include:

- Multi-factor authentication using TOTP.
- Secure password reset using email verification tokens.
- Cloud-based encrypted storage.
- Key rotation and centralized key management using a KMS.
- File signature validation and malware scanning.
- Cryptographically verifiable audit logs.
- Monitoring and alerting for suspicious activities.
- Advanced protection against automated and distributed attacks.

## 5. Conclusion

SecureDocs focuses on protecting sensitive documents through encryption, controlled sharing permissions, authentication security, and activity tracking.

Although the current implementation provides several important security protections, additional improvements such as MFA, centralized key management, malware scanning, and immutable audit storage would strengthen the platform further.
