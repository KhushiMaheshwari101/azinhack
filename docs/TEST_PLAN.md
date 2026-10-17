# QA and acceptance plan

## Automated checks

Run from the project root in the existing virtual environment:

```powershell
.\tinyfish\Scripts\python.exe -m unittest discover -s backend\tests -v
node --check frontend\app.js
```

The standard-library `unittest` suite covers domain normalization and lookalike-domain rejection, synthetic demo output, obfuscated-email extraction, quote grounding rejection, classifier provenance, and unchanged/changed policy diffs. It makes no TinyFish network calls. The JavaScript syntax check catches broken frontend bundles before a demo.

## Manual end-to-end acceptance

1. Start the app with `DEMO_MODE=true`; confirm `/api/health` says demo mode and the audit displays a clearly synthetic sample.
2. Confirm demo audit does not require a TinyFish key and displays source quote, status, disclaimer, and model mode.
3. Try malformed and local/private domains; confirm backend rejects them before provider use.
4. In a controlled live run, check that only same-domain pages appear in the audit and that every verified value appears in its visible evidence quote.
5. Select an official source page and save a monitor baseline; confirm a real recheck is available only in live mode.
6. Recheck an unchanged page; confirm the UI reports no content change. Change a controlled fixture page and recheck; inspect both excerpts, category, category method, and confidence in history.
7. Pause the monitor and confirm the history remains readable and checks are disabled.
8. Create a complaint draft, edit it in the textarea, copy it, and verify the copy includes no invented order/customer facts.
9. At mobile width, keyboard-tab through the forms, buttons, evidence links, and history controls; verify focus is visible and errors are announced.

## Provider failure cases for a live sandbox

Record input, expected output, observed output, pass/fail, and notes for: no search results, off-domain search result, redirected off-domain URL, fetch timeout, rate-limit/provider error, no grievance page, unsupported Agent value, source quote mismatch, scheduler restart, and provider quota exhaustion. A failed fetch must never be represented as unchanged. Use a throwaway controlled domain and do not submit personal complaint/order data.

## Reporting limits

Synthetic unit tests establish basic behavior, not production security or model quality. Record manual samples and provider spend separately. Evaluate classification and field extraction on manually reviewed real public pages before making accuracy or compliance claims. See `EVALUATION.md` for a dataset protocol.
