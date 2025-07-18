# Proposed Tech Stack & Repo Layout

• **Backend:** Python 3.12 + FastAPI – async-first, easy OpenAPI docs, good ecosystem.
• **Database:** PostgreSQL (via Supabase or self-hosted RDS) – reliable and SaaS-friendly.
• **Auth & Billing:** Clerk/NextAuth for auth, Stripe for subscriptions.
• **Frontend:** Next.js 14 (React-server components) with Tailwind CSS for rapid UI.
• **Infra:** Fly.io for MVP (simpler than AWS, global), Terraform for IaC once scaling.
• **CI/CD:** GitHub Actions – lint, type-check, run tests, build Docker, deploy.

Directory sketch:
```
/infra          → Terraform, Fly.io config, GitHub workflows
/backend        → FastAPI app (app/*, tests/*)
/frontend       → Next.js project
/docs           → Product & engineering docs
/scripts        → One-off tooling & migrations
```

These choices prioritise **developer velocity** and low ops overhead; everything can migrate to AWS/GCP later if needed.
