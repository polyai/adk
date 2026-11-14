def map_contacts(contacts: list[dict], outbound_campaign: OutboundCampaign):
    return {"contacts": [
        {
            "external_id": row["id"],
            "phone": row["phone"],
            "first_name": row["first_name"],
            "last_name": row["last_name"],
            "consent_given": True,
            "consent_at": row["consent_at"],
        }
        for row in contacts
    ]}
