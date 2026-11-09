# SecureDocs – Secure Document Sharing Platform

## 1. The Problem Solved

I built SecureDocs, a secure document-sharing platform that helps organizations protect sensitive documents while sharing them with authorized users.

Traditional document-sharing systems often lack proper encryption, granular access permissions, and detailed activity tracking. SecureDocs addresses these problems through encrypted file storage, three levels of access permissions, automatic share expiry, and an audit trail that records both successful and denied access attempts.

## 2. What Actually Works Right Now

- **Authentication:** User registration, login, password validation, rate limiting, and account lockout after five failed attempts.
- **File Encryption:** Documents are encrypted using Fernet before being stored on disk. Decryption happens in memory after authorization.
- **Document Management:** Upload, view, rename, delete, restore, and replace documents.
- **Access Permissions:** Three permission levels – View Only, View & Download, and Full Access.
- **Document Sharing:** Share documents with specific users, set expiry dates, and revoke access.
- **Audit Trail:** Records login, upload, download, sharing, permission changes, and unauthorized access attempts.
- **Admin Dashboard:** Activity statistics, user management, access revocation, and audit monitoring.
- **CSV Export:** Export audit records for further analysis.
- **Testing:** 26 automated tests passing using Pytest.

## 3. How to Run It

**Windows PowerShell:**

```powershell
git clone YOUR_GITHUB_REPOSITORY_URL
cd securedocs

python -m venv venv
.\\venv\\Scripts\\activate

pip install -r requirements.txt

flask seed-demo

pytest -v

python run.py
```

Open the application at:

[http://127.0.0.1:5000](http://127.0.0.1:5000)

**Demo Accounts:**

| Role      | Email                                                   | Password        |
| --------- | ------------------------------------------------------- | --------------- |
| Admin     | [admin@securedocs.local](mailto:admin@securedocs.local) | AdminSecure123! |
| Owner     | [alice@securedocs.local](mailto:alice@securedocs.local) | AlicePass123!   |
| Recipient | [bob@securedocs.local](mailto:bob@securedocs.local)     | BobPass123!     |

Configure the required environment variables in `.env` before running the application.

## 4. AI Tools I Used

- **Google Antigravity:** Used for project development, code generation, debugging, and testing.
- **Claude:** Used for exploring implementation approaches and resolving technical challenges.
- **ChatGPT:** Used for prompt preparation, understanding concepts, troubleshooting, and improving documentation.

I used these tools as development assistants and reviewed and tested their suggestions during implementation.

## 5. What the AI Got Wrong, and What I Fixed Myself

1. **Broken Navigation Links:** Some AI-generated links did not connect correctly to the corresponding application pages. I explored alternative linking options, made the necessary changes, and tested the navigation to resolve the issue.
2. **Command Execution Issues:** Sometimes the suggested commands and development steps did not connect clearly with the previous steps. I checked the existing project state, explored the related options, and adjusted the workflow instead of blindly following every suggestion.
3. **Code Validation:** I learned that AI-generated code does not always work correctly when integrated with an existing project. I checked the functionality and tested the application after making changes.

This experience helped me understand that AI is a development assistant, but reviewing, debugging, and validating the final implementation are still important responsibilities.

## 6. What Is Not Finished

- **Cloud Storage:** Documents are currently stored as encrypted files on the local server instead of cloud object storage such as AWS S3.
- **Advanced Key Management:** The application uses a single Fernet encryption key. Enterprise-level key management using AWS KMS or HashiCorp Vault is not implemented.
- **Large File Handling:** Files are decrypted in memory, which may not be suitable for handling very large documents.
- **Email Notifications:** Sharing a document does not currently send an email notification to the recipient.
- **Password Recovery:** Automated email-based password reset functionality is not implemented.
- **Multi-Factor Authentication:** TOTP-based two-factor authentication is not yet available.
- **Advanced File Validation:** Binary magic-byte inspection is not implemented; validation currently relies on extensions and MIME information.

These are the main areas I would improve before using SecureDocs in a larger production environment.
