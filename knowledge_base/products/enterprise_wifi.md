---
product: P005
product_name: Enterprise WiFi
category: connectivity
issue_id: WIFI-001
title: Enterprise WiFi 802.1X Authentication and Portal Troubleshooting
audience: customer
difficulty: basic
source: approved_product_documentation
version: "1.0"
---

# Enterprise WiFi (Product P005)

## A. Product Overview
Enterprise WiFi provides managed wireless campus networking featuring 802.1X RADIUS authentication, captive portal login, and seamless AP roaming.

- **Prerequisites**: WPA2/WPA3 Enterprise profile, RADIUS server credentials, valid 802.1X user certificate.
- **Common Symptoms**: RADIUS authentication timeout, captive portal page fails to redirect, 802.1X certificate error.

## B. Troubleshooting Procedures

### Issue WIFI-001: Enterprise WiFi 802.1X Portal Authentication Error
**Symptoms**: Laptop / mobile device fails to connect to Enterprise SSID; error "Authentication Server Unavailable".

#### Diagnostic Steps:
1. **Forget WiFi Network**:
   - Go to device Network Settings -> Select Enterprise SSID -> Choose 'Forget Network'.
   - *Expected Result*: Saved profile and old cached certificate are cleared.
2. **Re-select EAP Method**:
   - Re-connect to SSID, select EAP Method: `PEAP` or `EAP-TLS`, Phase 2 Authentication: `MSCHAPv2`.
   - *Expected Result*: Credentials prompt displays username/password input fields.
3. **Verify User Credentials & Certificate**:
   - Enter domain credentials `<username>@company.com` and accept corporate Root CA certificate.
   - *Expected Result*: Device receives IP address via DHCP and status shows 'Connected, Secure'.

#### Escalation Criteria:
- If RADIUS authentication fails for multiple users on the same Access Point, escalate to IT Network Administrator.
