---
product: P001
product_name: Business Broadband
category: connectivity
issue_id: BB-001
title: Business Broadband Overview and Diagnostics
audience: customer
difficulty: basic
source: approved_product_documentation
version: "1.0"
---

# Business Broadband (Product P001)

## A. Product Overview
Business Broadband provides high-speed symmetrical internet connectivity for SMB and Enterprise offices over high-performance optical fiber and copper infrastructure.

- **Prerequisites**: Active ONT modem, power supply (12V DC), RJ45 ethernet cable.
- **Dependencies**: Ground fiber drop line and local optical distribution node.
- **Common Symptoms**: No internet light on ONT, red power/status LED, intermittent dropouts during peak load.

## B. Troubleshooting Procedures

### Issue BB-001: No Internet Connectivity (RED Alarm LED)
**Symptoms**: All devices lose internet access; optical modem shows RED 'LOS' or 'Alarm' LED.
**Possible Causes**: Fiber patch cable disconnect, physical fiber drop cut, optical signal attenuation below -28 dBm.

#### Diagnostic Steps:
1. **Inspect Fiber Cable**:
   - Check the thin yellow fiber patch cord connected to the ONT modem.
   - *Expected Result*: Cable is firmly clicked into the green SC/APC optical port.
2. **Reboot ONT Modem**:
   - Power off the modem using the rear power button, wait 30 seconds, and turn back on.
   - *Expected Result*: Power LED turns solid GREEN; wait 2 minutes for optical sync.
3. **Verify Signal LED**:
   - Observe the 'PON' / 'LOS' indicator.
   - *Expected Result*: 'PON' LED becomes solid GREEN, 'LOS' light turns completely OFF.

#### Escalation Criteria:
- If 'LOS' LED remains RED after cable check and modem reboot, optical fiber signal is lost. Log a field engineer dispatch ticket under priority High.

> [!CAUTION]
> **Warning**: Do not look directly into the optical fiber connector port. Infrared laser radiation can cause irreversible eye injury.

## C. FAQs
- **Q: What is the normal optical power range for Business Broadband?**
  - *Answer*: Normal optical power ranges between -12 dBm and -24 dBm. Anything below -28 dBm indicates optical attenuation or physical fiber bend.
