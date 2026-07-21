# FAMS v2 — Final Prototype

The merged FAMS prototype built from `FAMS_Design_Requirements_v1.0.docx`:
Agriverse visual language (Inter, dark theme, Recharts, OpenLayers) over the
SRS v0.4 workflow, using the real 120-farm field-survey registry
(`Digitized Field Survey Form corrected.xlsx`) as sample data.

## Run

```bash
npm install
npm run dev      # http://localhost:3000
```

On `/login`, pick a role — no password.

## Screens

| Route | Screen | DRD § |
|---|---|---|
| `/login` | Role selection (from FAMS_Final) | 4 |
| `/dashboard` | Manager morning dashboard — KPI tiles, farm map + action queue, trends | 5 |
| `/advisories` | Farms table + general advisories strip | 6.1 |
| `/advisories/[farmId]` | Farm detail — satellite map w/ index overlay, imagery timeline, charts, advisory workflow, audit trail | 6.2, 8 |
| `/services` | Implement/drone request queue + manage sheet (base + petrol pricing) | 7 |
| `/agents` | Field agents with expandable tasks (from Fams) | 9 |
| `/overview` | Chief Agronomist portal — org KPIs, center comparison, trends | 10 |

## Business rules in the UI

- **BR-1** Forward is locked until a field agent verification is recorded.
- **BR-2** Verification requires mandatory feedback (both outcomes) before any terminal action.
- **BR-4** Closed advisories can never be sent; the action is removed.
- **BR-5** Every action appears in the audit timeline with actor + timestamp.
- **BR-6** Feedback shows a "returned to Agrobot" chip once recorded.

## Pricing model

- Advisories (farm-level and general): no charge.
- Implements: standard base price per service; petrol/transport cost is
  entered by the manager per request when accepting it. Total = base + petrol.
