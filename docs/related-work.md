# Related work

Records what was checked about similar projects, so the gap claim in the README can be defended.

## Aperio and open-SSPM: verified

Both repositories were downloaded and checked: their README, their database schema, and a search of the full source for vendor-assurance terms (SOC 2, ISO 27001, questionnaire, data processing agreement, data residency, POPIA, GDPR, "vendor risk", "third-party risk", supplier). Main-branch snapshots, October 2026. They may have changed since.

| | Aperio (`writer/aperio`) | open-SSPM (`open-sspm/open-sspm`) |
|---|---|---|
| Purpose | Find SaaS posture risks and OAuth apps, send findings to a SIEM | "Who has access to what" across an identity provider and apps |
| Stack | Mostly Go, with a Next.js console and a Prisma schema | Go, Postgres, server-rendered pages |
| Size of data model | 38 models in `schema.prisma` | About 60 generated tables and views |
| App record | `SecurityAsset` (including an OAuth app type) and `OauthAppGrant` | `saas_apps` with sources, events and bindings |
| Vendor record | **None.** The word "vendor" in the code refers to SIEM products. | **Text label only** (`vendor_name`), taken from the connector or derived from the domain |
| Owner, criticality, sensitivity | Technical and business owner, criticality, exposure, sensitive-data flag | Owner and review owner, business criticality and data classification (suggested versus effective) |
| Risk score | Integer on assets, grants and findings | 0 to 100 with a documented formula |
| Review workflow | Risk exceptions (rationale, controls, expiry, approver) | Review decisions (disposition, due date, ticket, replacement app) |
| Operator agreements, assurance evidence, hosting location | **None found** | **None found** |
| Vendor-level score | **None** | **None** |

## What this does and does not show

- It shows that neither project models a vendor, tracks a POPIA operator agreement, or scores a vendor.
- It does **not** show that the idea is valuable to a small business. That needs the interviews and the usability test.
- Only the features found by reading the schema and searching the code are claimed. Anything not found is described as "not found", and not as "does not exist".

## CISO Assistant: you must complete this

The README claims CISO Assistant was reviewed "at feature-list level only". Before you submit, read its third-party risk documentation (repository: `intuitem/ciso-assistant-community`) and answer these, with a link for each answer:

| Question | Answer and link |
|---|---|
| What does a third-party or vendor record contain? | |
| Can it import or discover SaaS applications? | |
| Can it match an application to a vendor automatically? | |
| Does it track personal-information handling per vendor? | |
| Does it track a signed operator or data processing agreement? | |
| Does it record where a vendor hosts data? | |
| Does it calculate a score per vendor, and can you see why? | |
| How much setup does a small business need (accounts, frameworks, hosting)? | |
| Who is it designed for (security teams, auditors, small businesses)? | |

Then update the gap table in the README. If CISO Assistant already covers a row, change that row and say so. A narrower, honest claim is stronger than a broad one that a marker can disprove.

## Other things worth a line

You did not research commercial vendor-risk platforms (for example Vanta, Drata or UpGuard). Either spend an hour on their public pages and say what you found, or say plainly in your limitations that you did not.
