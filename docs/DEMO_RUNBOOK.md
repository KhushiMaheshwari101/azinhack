# ReadyCheck demo runbook

## Prepare

1. Open PowerShell in the ReadyCheck project directory.
2. Activate the existing environment and install any new dependencies:

   ```powershell
   .\tinyfish\Scripts\Activate.ps1
   python -m pip install -r requirements.txt
   ```

3. Keep `DEMO_MODE=true` in `.env` for a safe, no-provider-call demo. Do not display a real API key or a real customer's complaint details.
4. Optional local QA before presenting:

   ```powershell
   python -m unittest discover -s backend\tests -v
   node --check frontend\app.js
   ```

5. Start the server:

   ```powershell
   python -m uvicorn backend.app.main:app --reload
   ```

6. Open `http://127.0.0.1:8000` and confirm the page says Demo mode. Check `/api/health` if the status is unclear.

## 90-second walkthrough

1. **Problem:** A shopper should not have to hunt through a long help site to find a company's grievance contact or escalation instructions.
2. **Audit:** Enter `Sample Store` and `example.com`; submit. Explain that demo mode shows a synthetic, labeled example and does not call TinyFish.
3. **Evidence:** Show the field statuses, source quote, source link, checked timestamp, and explainable checklist. A verified value must remain visible with its quote; unknown values stay unclear.
4. **ML:** Expand page classification to show the label, confidence, and method. Explain that it prioritizes pages and does not decide legal compliance. The checked-in training fixtures are synthetic, so their report is not a real-world accuracy claim.
5. **Change monitoring:** Explain that live mode allows a user to save a public-page baseline, schedule daily/weekly checks, inspect before/after excerpts and category, and pause while keeping history. Do not attempt to add a monitor in demo mode because provider calls are intentionally disabled.
6. **Draft:** Create a draft from fictional facts, edit it in place, and copy it. Emphasize that it is a template the user reviews before sending.
7. **Close:** ReadyCheck is a research aid for human review, not a legal opinion or compliance certification.

## Live demo gate

Use live mode only if a TinyFish key and wallet/limits have been confirmed. Set `DEMO_MODE=false`, set `TINYFISH_API_KEY` only in the server-side `.env`, restart the app, and verify `/api/health` reports monitoring available. Choose a public test company, keep the configured result/step/time bounds, and avoid personal data. When finished, stop the server and restore demo mode. Search/Fetch/Agent usage may consume account quota or credits.

## If something fails

- **Page does not open:** check the uvicorn console and confirm the server is running on port 8000.
- **Mode text does not load:** call `/api/health`, then refresh the browser.
- **Live audit returns a provider error:** return to demo mode; do not retry repeatedly until the account limit and provider status are checked.
- **Monitor check fails:** show the saved history and explain that a fetch failure is recorded as failed, not as “no change.”
- **Browser UI appears stale:** hard refresh after the server reload completes.
