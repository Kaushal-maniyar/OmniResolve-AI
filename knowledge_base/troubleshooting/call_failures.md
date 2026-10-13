---
category: voice
issue_id: GEN-VOICE-001
title: Voice Trunk Call Disconnection and Quality Analysis
audience: customer
difficulty: intermediate
source: approved_product_documentation
version: "1.0"
---

# Voice Call Disconnection Diagnostics

## Overview
Diagnostic procedures for voice trunk disconnections, SIP registration drops, and audio codec errors.

## Diagnostic Steps
1. **Verify SIP Transport**: Ensure UDP/TCP port 5060 is accessible to SBC gateway.
2. **Jitter Buffer Configuration**: Check PBX jitter buffer settings (recommended 20ms - 50ms adaptive).
