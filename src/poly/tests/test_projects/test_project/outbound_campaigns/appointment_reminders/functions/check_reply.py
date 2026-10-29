def check_reply(outbound_contact: OutboundContact, outbound_campaign: OutboundCampaign):
    if outbound_contact.metadata.get("confirmed"):
        return {"branch": "confirmed"}
    return {"branch": None}
