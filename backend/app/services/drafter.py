def draft_message(company: str, officer_name: str | None, issue_summary: str, desired_resolution: str) -> str:
    recipient = officer_name or "Grievance Officer"
    return f"""To: {recipient}
Subject: Request for assistance with {company}

Dear {recipient},

I am contacting you about this issue:
{issue_summary.strip()}

I request that you review the matter and provide this resolution:
{desired_resolution.strip()}

Please share an acknowledgement and next steps. I have retained the relevant order and correspondence.

Regards,
[Your name]
[Order/reference number]
[Contact details]

Please review and edit before sending."""
