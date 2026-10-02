# Burundi Regulatory & Compliance Notes — KwizeraGate

**Author:** Cynthia Moraa · Modus Chora Studio
**Region:** Burundi · **Sector:** Fintech / Payment Services
**Status:** Planning reference — verify all figures with the named authority before acting

> Citation: `[Country dossier: Burundi]` — Modus Chora Studio internal reference, 2026-07-31.

---

## 1. Central Bank — BRB (Banque de la République du Burundi)

**Role:** Primary regulator for all payment service providers (PSPs) on the BurundiPay network.

### Licensing Requirement

KwizeraGate is a **payment entry middleware** — it does not hold or transmit funds directly.
It authenticates payment instructions and routes them to the BurundiPay core switch. Under
current BRB guidance:

- **Payment System Participants** must be registered with BRB as a licensed PSP or
  technology service provider.
- KwizeraGate's operator must obtain a **PSP Technology Service License** before
  onboarding live merchants.
- Cross-border payments (EAC region — USD/EUR transfers) require additional BRB approval
  under the foreign exchange framework.

**Action item:** Submit a PSP technology service license application to BRB before
soft-launch. Engage a Burundian legal counsel familiar with BRB Regulation No. 01/2020
on payment systems.

---

## 2. Data Protection — ARCT (Agence de Régulation et de Contrôle des Télécommunications)

**Role:** Telecom and data regulator (verify current mandate scope before filing).

### Obligations for KwizeraGate

| Obligation | KwizeraGate Status |
|---|---|
| Data protection registration | Required before consumer-facing launch |
| Personal data minimization | Transaction logs store IP, device_id, wallet address — no name/NIN stored |
| Data localisation | Logs must be stored within Burundi or EAC-recognised jurisdiction |
| Breach notification | Mandatory notification to ARCT within 72 hours of a confirmed breach |
| Cross-border data flows | QRadar cloud instance must be in an approved jurisdiction |

### What KwizeraGate Logs (and Why It Is Compliant by Design)

```
Stored: merchant_id, transaction_id, ip_address, device_id,
        amount, currency, status, risk_level, timestamp
NOT stored: merchant name (in Transaction table), NIN, phone number,
            full card numbers, biometric data
```

IBM QRadar receives the same minimal fields. No PII beyond IP address is streamed.
IP address is treated as personal data under ARCT guidance.

---

## 3. AML/CFT Compliance

**Framework:** Burundi is a member of ESAAMLG (Eastern and Southern Africa Anti-Money
Laundering Group). Financial institutions must implement:

- Customer Due Diligence (CDD) on merchant onboarding
- Transaction monitoring for suspicious patterns
- Suspicious Transaction Reports (STRs) filed with the Financial Intelligence Unit (FIU)

### KwizeraGate's AML Controls

| Control | Implementation |
|---|---|
| Merchant CDD | `api_key` issuance gated on offline KYC process (future Phase 3) |
| Transaction monitoring | IBM QRadar CRE rules flag rapid back-to-back transfers |
| Automatic suspension | `/webhook/qradar-suspend` freezes merchant on anomaly detection |
| Audit trail | Every transaction persisted with IP, device_id, amount, timestamp |
| STR readiness | `qradar_logs.json` / QRadar dashboard exports can be filed with FIU |

**Threshold to note:** ESAAMLG recommends enhanced monitoring for transactions above
the equivalent of **USD 10,000** in a single day per merchant. KwizeraGate's QRadar
rule for `amount > 10,000,000 BIF` (≈ USD 3,400 at mid-2026 rates) is intentionally
conservative — adjust per BRB guidance.

---

## 4. Currency Handling — BIF (Burundian Franc)

All transactions default to **BIF** in the KwizeraGate data model:

```python
# schemas.py — TransferRequest
currency: Literal["BIF", "USD", "EUR"] = "BIF"

# models.py — Transaction
currency = Column(String(10), nullable=False, default="BIF")
```

### Accepted Currencies

| Currency | Use Case |
|---|---|
| **BIF** | All domestic BurundiPay transfers (default) |
| **USD** | EAC cross-border transfers (requires BRB foreign exchange approval) |
| **EUR** | EAC cross-border transfers (requires BRB foreign exchange approval) |

Any `currency` value other than `BIF`, `USD`, or `EUR` is rejected by Pydantic validation
at the API layer before touching the database — satisfying data-integrity requirements.

---

## 5. EAC Cross-Border Data Flows

Burundi is a member of the **East African Community (EAC)**. The EAC framework is
harmonising data protection and financial regulations across member states (Kenya, Tanzania,
Uganda, Rwanda, Burundi, South Sudan, DRC, Somalia).

**Implications for KwizeraGate:**

- Cross-border USD/EUR transfers may be processed under EAC payment interoperability rules.
- QRadar log data flowing to a cloud-hosted QRadar instance must comply with EAC data
  residency guidance — prefer IBM Cloud regions within EAC jurisdiction.
- The `BUJUMBURA_SUBNETS` configuration can be extended to include trusted EAC mobile
  network operator subnets when expanding to Rwanda, Tanzania, or Uganda.

---

## 6. Tax

| Item | Rate | Authority |
|---|---|---|
| Corporate Income Tax | 30% | OBR (Office Burundais des Recettes) |
| VAT / Sales Tax | 18% | OBR |
| Withholding tax on dividends | 5–15% (verify per treaty) | OBR |

*All rates require verification against the current national finance act before filing.*

---

## 7. Investment Promotion

**Agency:** Investments Promotion Agency of Burundi (API-B).

Digital financial infrastructure projects may qualify for investment code incentives.
Engage API-B early for potential tax holidays on technology imports and reduced CIT
during the first operating years.

---

## 8. Compliance Checklist (Pre-Launch)

- [ ] Obtain BRB PSP Technology Service License
- [ ] Register with ARCT for data protection
- [ ] Complete AML/CFT programme documentation
- [ ] Establish FIU reporting channel for STRs
- [ ] Confirm QRadar data residency within approved jurisdiction
- [ ] Legal review of merchant onboarding agreements under Burundian law
- [ ] Confirm VAT applicability on software services (18%)

---

*KwizeraGate · Burundi Regulatory Compliance Notes · Modus Chora Studio · 2026*
*This document is a planning baseline — not legal, tax or financial advice.*
*Verify each item with the named authority before commitment.*
