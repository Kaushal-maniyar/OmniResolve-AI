---
product: P003
product_name: SIP Trunk
category: voice
issue_id: SIP-001
title: SIP Trunk Call Quality and Registration Diagnostics
audience: customer
difficulty: intermediate
source: approved_product_documentation
version: "1.0"
---

# SIP Trunk (Product P003)

## A. Product Overview
SIP Trunk delivers digital voice trunking over IP infrastructure supporting concurrent voice channels, G.711 / G.729 codecs, and Direct Inward Dialing (DID).

- **Prerequisites**: IP-PBX system (Asterisk, Avaya, Cisco CUCM), UDP port 5060, RTP ports 10000-20000.
- **Common Symptoms**: One-way audio, call drops at 32 seconds, SIP 403 Forbidden, SIP 503 Service Unavailable.

## B. Troubleshooting Procedures

### Issue SIP-001: SIP Trunk Call Quality Degradation (Audio Distortion / Mute)
**Symptoms**: Voice robotic distortion, 1-way audio, jitter on outbound calls.

#### Diagnostic Steps:
1. **Codec Matching**:
   - Verify PBX codec configuration matches provider order (G.711u / G.711a preferred).
   - *Expected Result*: Codec negotiation succeeds without transcoding mismatch.
2. **NAT / ALG Inspection**:
   - Ensure SIP ALG (Application Layer Gateway) is DISABLED on local firewall/router.
   - *Expected Result*: SIP headers retain original public IP addresses without NAT rewrite errors.
3. **RTP Port Verification**:
   - Verify firewall allows UDP RTP media port range 10000-20000 inbound and outbound.
   - *Expected Result*: Two-way audio flow established on SIP session ACK.

#### Escalation Criteria:
- If 1-way audio persists with SIP ALG disabled or SIP trunk shows 408 Request Timeout, escalate to Voice Engineering team.

## C. FAQs
- **Q: Why do SIP calls disconnect automatically after 32 seconds?**
  - *Answer*: 32-second disconnection occurs when ACK message is not received by SBC due to NAT firewall blocking UDP 5060 return packets.
