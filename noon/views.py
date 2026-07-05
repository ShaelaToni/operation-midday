"""Noon views. report + refresh both build the digest via a shared helper: read (ORM, in the
reader) -> build_report (pure) -> curated top-N -> render. No ProfitFact query logic here."""
from datetime import datetime

from django.http import HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from application.report import build_report
from noon.models import Account
from noon.reporting import read_profit_facts

_TOP_FUEL = 3
_TOP_FREE_UP = 5


def _digest_context():
    """Build the full digest context (shared by report GET and refresh POST). Read-only,
    empty-state safe. The 'recomputed_at' stamp makes a refresh visibly do something."""
    account = Account.objects.filter(name="Demo Account").first()
    facts = read_profit_facts(account) if account is not None else []
    data = build_report(facts)
    fuel = [m for m in data.moves if m.action == "fuel"][:_TOP_FUEL]
    drainers = [m for m in data.moves if m.action == "free_up"]
    top_free_up = sorted(drainers, key=lambda m: m.amount, reverse=True)[:_TOP_FREE_UP]
    return {
        "report": data,
        "top_fuel": fuel,
        "top_free_up": top_free_up,
        "recomputed_at": datetime.now().strftime("%H:%M:%S"),
    }


def report(request):
    """The Noon Report digest."""
    return render(request, "noon/report.html", _digest_context())


@require_POST
def refresh(request):
    """Re-run the report live and re-render. Honest motion: the recomputed-at stamp updates,
    proving the pipeline ran, not a static screenshot."""
    return render(request, "noon/report.html", _digest_context())


def health(request):
    """Liveness check - plain 200, no DB."""
    return HttpResponse("ok", content_type="text/plain")
