# Privacy and security notes

Hackathon mode should use synthetic/sample inputs and public company pages. Do not upload order emails, phone numbers, addresses, screenshots, or identity documents to this scaffold. The local monitoring prototype stores fetched public page snapshots and change history in SQLite without authentication or encryption; treat that database as temporary hackathon data. Provider requests are external when live mode is enabled; review provider terms and data handling before sending any personal data.

Before a public pilot: add consent and privacy notice, auth, access control, file type/size validation, malware scanning, encryption, delete/export controls, retention limits, secret rotation, server-side rate limits, SSRF defenses, safe logging, incident response, and legal/security review.
