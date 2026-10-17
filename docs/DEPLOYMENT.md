# Deployment checklist

- [ ] Confirm the target host supports Python and the selected framework.
- [ ] Set DEMO_MODE=true for judging unless live calls are required.
- [ ] If live: configure TINYFISH_API_KEY only in server secrets; review wallet/limits first.
- [ ] Set tight TinyFish step, time, and request limits.
- [ ] Run the hackathon scheduler in one server worker only; keep the process online for daily/weekly checks.
- [ ] Keep `DEMO_MODE=true` for synthetic demos; monitoring endpoints require live mode and a server-side TinyFish key.
- [ ] Turn off debug mode; configure HTTPS and allowed origins.
- [ ] Add rate limiting, health checks, error reporting, backups, and spend alerts.
- [ ] Review data retention and privacy notice before real user data.
- [ ] Check hosting free-tier eligibility/terms; no always-on production guarantee on a free plan.
