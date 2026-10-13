---
category: connectivity
issue_id: GEN-CONN-001
title: General Connectivity and Physical Layer Diagnostics
audience: customer
difficulty: basic
source: approved_product_documentation
version: "1.0"
---

# General Connectivity Troubleshooting

## Overview
This guide covers general physical layer and IP stack troubleshooting applicable to broadband, leased lines, and corporate network interfaces.

## Step-by-step Diagnostics
1. **Physical Cable Health**: Ensure all RJ45 ethernet and optical patch cords are undamaged and fully seated.
2. **IP Assignment Verification**: Run `ipconfig /all` (Windows) or `ifconfig` (Linux/Mac) to confirm valid IP address assignment (not `169.254.x.x` APIPA address).
3. **DNS Gateway Test**: Test DNS resolution using `nslookup google.com` or `ping 8.8.8.8`.
