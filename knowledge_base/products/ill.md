---
product: P002
product_name: Internet Leased Line
category: connectivity
issue_id: ILL-001
title: Internet Leased Line Performance and Packet Loss Troubleshooting
audience: enterprise
difficulty: intermediate
source: approved_product_documentation
version: "1.0"
---

# Internet Leased Line (Product P002)

## A. Product Overview
Internet Leased Line (ILL) provides dedicated 1:1 unthrottled internet bandwidth with guaranteed SLA (99.95% uptime) and static public IPv4/IPv6 blocks.

- **Prerequisites**: Cisco / Juniper Managed Customer Edge Router, SFP transceiver.
- **Dependencies**: Dual-homed fiber path, BGP routing peering.
- **Known Limitations**: Requires active BGP session; single fiber cut without protection path degrades to backup path.

## B. Troubleshooting Procedures

### Issue ILL-001: High Packet Loss and Latency Spikes
**Symptoms**: Packet drop > 5%, high ping jitter (> 50ms) to public gateway, file transfer slowdowns.

#### Diagnostic Steps:
1. **Interface Error Check**:
   - Check SFP interface error counters on Customer Edge (CE) router.
   - *Expected Result*: Zero CRC errors, zero input/output frame drops.
2. **Execute MTR / Path Trace**:
   - Run path trace from CE router to edge gateway `ping -c 100 <gateway_ip>`.
   - *Expected Result*: 0% packet loss to carrier edge gateway.
3. **Verify Link Utilization**:
   - Check router interface bandwidth utilization graph.
   - *Expected Result*: Traffic is below 95% of contracted CIR (Committed Information Rate).

#### Escalation Criteria:
- If packet loss originates at carrier hop 2/3 or SFP reports optical signal decay below -20 dBm, escalate to Carrier NOC (Tier-3) immediately.

## C. FAQs
- **Q: What is the SLA guarantee for Internet Leased Line packet loss?**
  - *Answer*: ILL SLA guarantees < 0.5% packet loss and < 20ms round-trip latency to regional core router.
