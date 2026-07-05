"""Noon views. The report view ties the seam: read_profit_facts (ORM, in noon/reporting.py) ->
build_report (pure) -> template. NO ProfitFact query logic lives here - the view delegates the ORM
read to the reader and the logic to the pure builder, then curates top-N moves for the digest
(a presentation choice - the builder returns the full ranked list; the full list lives at a future
/moves route)."""
from django.http import HttpResponse
from django.shortcuts import render

from application.report import build_report
from noon.models import Account
from noon.reporting import read_profit_facts

_TOP_FUEL = 3      # winners to feature (feed these)
_TOP_FREE_UP = 5   # biggest drainers to feature (reclaim these)


def report(request):
    """The Noon Report digest. Reads the demo account's reconciled facts through the reader,
    builds the pure report payload, curates the top money moves for the hero digest, renders it.
    Read-only and empty-state safe."""
    account = Account.objects.filter(name="Demo Account").first()
    facts = read_profit_facts(account) if account is not None else []
    data = build_report(facts)

    # Curate top-N for the digest (presentation): winners are already ranked highest-profit first;
    # drainers rank lowest-profit last, so the biggest drainers are the tail, reversed to lead with
    # the largest reclaimable spend.
    fuel = [m for m in data.moves if m.action == "fuel"][:_TOP_FUEL]
    drainers = [m for m in data.moves if m.action == "free_up"]
    top_free_up = sorted(drainers, key=lambda m: m.amount, reverse=True)[:_TOP_FREE_UP]

    return render(request, "noon/report.html", {
        "report": data,
        "top_fuel": fuel,
        "top_free_up": top_free_up,
    })


def health(request):
    """Liveness check - plain 200, no DB. The box is up if this responds."""
    return HttpResponse("ok", content_type="text/plain")
