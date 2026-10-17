def build_checklist(fields: dict) -> list[dict]:
    items = []
    for key,label in [("officer_name","Named grievance officer"),("designation","Officer designation"),("email","Email contact"),("phone","Phone contact")]:
        finding = fields.get(key,{})
        items.append({"label":label,"status":finding.get("status","unclear"),
        "explanation":"Found in cited source." if finding.get("status")=="verified" else "Not established from checked source; manual review needed.",
        "evidence":finding.get("evidence")})
    return items
