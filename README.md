# Noon

**Your team makes high-stakes calls every morning on numbers that were never real. Noon hands them the truth - so instead of guessing in the fog, they walk in knowing where the profit is and where to move it.**

---

## The morning this is built for

A media buyer opens five dashboards before the coffee's cold. Google says one thing, Meta another, Taboola and TikTok each claim the same conversions, and the affiliate network - the one that actually pays - won't settle the real number for days. So the team decides in the fog: scale what looks like a winner, keep feeding what's quietly bleeding.

One morning tells the whole story. An offer looked like a winner all week, so budget got scaled into it. Then the leads got scrubbed - the tracker showed forty, the network paid a handful, and the real payout landed far under what every dashboard had promised. Money already spent, chasing a number that was never real. Meanwhile a genuinely good offer sat starved, because its true payout was invisible under the platform's under-reporting.

That's the problem Noon exists to end. Not because the team isn't sharp - they're working as hard as anyone can. It's that every optimization they make is only as good as the numbers underneath it, and those numbers are late, scattered, and inflated. A team working this hard deserves to see the truth before they bet real money on it.

With the truth in front of them, the morning inverts: money leaves what's failing and feeds what's working. The team stops betting on the lie and starts compounding on the real number - not by working harder, but by seeing clearly before they commit. The hero here is the buyer. Noon is just the tool that hands them the truth.

---

## What it does

Noon pulls ad spend from every platform (Google, Meta, Taboola, TikTok) and the real revenue from the affiliate/lead system, reconciles them into one profit-per-offer view, and every morning tells the team exactly where to move money to grow profit - one number and one ranked list. The calls they used to make on gut and lag, they now make on the real number, first thing, before a dollar is wasted.

It replaces the manual, days-late, five-dashboards-and-a-spreadsheet reconciliation that every lean performance team does by hand.

## Why this one

Platform-reported ROAS over-claims credit. Spend and revenue live in separate systems. Stitching them is manual and late - so teams optimize against a distorted picture and burn budget on it. Noon makes blended profit-per-offer the single source of truth, because **you cannot build anything durable on a false foundation.** Get the foundation right and it opens doors: the same clean data stream is what powers the learning engine (next) and a licensable market-intelligence layer (after that).

## What's next

- **V1 (this):** reconcile spend + revenue into one honest profit truth; deterministic money-move rules (fuel / free up); The Noon Report digest; a self-manageable backend.
- **V2 - the learning engine:** the clean data Noon collects from day one becomes training signal - learning which angle x offer x geo x placement patterns predict profit, forecasting fatigue before it shows, recommending reallocation. Built on V1's foundation, no re-architecture.
- **V3 - the licensable market-intelligence API:** package the engine for other performance shops; aggregated, anonymized, opt-in market signal. A moat and a revenue line.

The through-line: V1's clean foundation is what makes V2 possible and V3 valuable. Build the foundation right once; everything above it compounds.

---

## How it works, in plain English

Every ad platform tells you how you're doing - but each takes credit for sales, counts the same conversion twice, and reports before the money is real. The affiliate network is the one that actually pays you, and its number lands days later and can even reverse (a lead gets disqualified, a charge gets refunded).

Noon does what a person would do by hand, correctly and instantly:

1. It reads each platform's export in that platform's own format (Google's numbers arrive in millionths; Meta buries conversions in a nested list; Taboola calls spend "spent" and reports in its own timezone; TikTok lags and shuffles its columns). Noon handles each quirk.
2. It matches the money you actually earned back to the ad that earned it, using the tracking token that follows a click from the ad to the payout.
3. It shows you the gap - "platforms claim $X, you made $Y" - and where the profit actually is. Feed the winners. Pull budget off what's failing and put it where it earns. The team acts on what's real instead of defending what looked good, and the number underneath always stays exact.

No spreadsheets. No waiting days. No guessing which dashboard to believe.

---

## Get started (under 5 minutes)

Requirements: Python 3.12, Docker (for local Postgres).

```bash
# 1. Clone and enter
git clone <repo-url> operation-midday
cd operation-midday

# 2. Python environment
python3.12 -m venv venv
./venv/bin/pip install -r requirements.txt

# 3. Local database (Postgres 15 in Docker)
#    Create db.env with POSTGRES_DB=noon / POSTGRES_USER=noon / POSTGRES_PASSWORD=<pick one>
docker compose up -d db

# 4. App config
cp .env.example .env
#    Set SECRET_KEY and DB_PASSWORD in .env (DB_PASSWORD must match db.env's POSTGRES_PASSWORD)

# 5. Migrate, seed the demo, reconcile
./venv/bin/python manage.py migrate
./venv/bin/python manage.py seed_demo      # four story cases + 12 months of realistic filler
./venv/bin/python manage.py reconcile      # derive the profit facts (idempotent - safe to re-run)

# 6. Run it
./venv/bin/python manage.py runserver
#    Open http://localhost:8000/  ->  The Noon Report
```

You'll land on the gap headline, the "still yours to reclaim this week" total, and the ranked Fuel / Free-up moves - all computed by the real pipeline on seeded synthetic data. Nothing is hardcoded; every number is produced by the same reconciliation code that would run on real exports.

### Run the tests

```bash
./venv/bin/python -m pytest -q
```

### How the demo data works

The demo runs on engineered synthetic fixtures shaped like real platform exports - no live accounts, no credentials. The seeder writes only raw inputs (spend rows, conversion/postback rows in each platform's real shape); every profit number and money-move is produced by the real pipeline. Demo data and real data enter through the same door, so a shop can drop in its own export and watch its own numbers run the identical code.

The demo is intentionally open on synthetic data so anyone can click and see it. Production access is invite-only, with admin and member roles - reserved for the next version.

Four story cases are planted in the data: a hidden winner the platform under-credits, an obvious zombie (spend, no payout), an overnight reversal that flips an offer from profit to loss, and one tracking-token mismatch the reconciler resolves by falling back to offer + geo + date.

---

## Architecture, briefly

Clean, layered, and boundary-enforced:

- `domain/` - pure Python reconciliation and records. No framework imports (a test enforces this).
- `application/` - use-cases orchestrating the domain (the report builder). Also pure.
- `noon/` - the Django app: models, the ORM reader, views, templates, the seed/reconcile commands.

Money is always Decimal, never float. The reconciliation core is covered by strict TDD plus a golden-dataset eval that asserts the whole pipeline's decisions against the known-truth seed data. The reconciliation logic never touches Django; a single command maps database rows to plain records and back, so the money math is framework-independent and fully testable.

---

## Built AI-first

Noon V1 is a deterministic reconciliation + rules engine - no LLM at runtime, so it is cheap to run and scales without per-query AI cost. It was built AI-first, with a disciplined direct-and-verify workflow, and the V2 learning layer plus its evals are the AI roadmap the clean V1 data stream unlocks.

## Licenses

All dependencies are permissive (MIT / BSD / Apache-2.0 / PSF). The self-hosted display and body typefaces (Fraunces, IBM Plex Sans) are SIL OFL, with their license notices retained alongside the font files. No copyleft (GPL / AGPL / LGPL) anywhere in the tree.
