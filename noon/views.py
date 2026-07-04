"""Noon views. The report view ties the seam: read_profit_facts (ORM, in noon/reporting.py) ->
build_report (pure) -> template. NO ProfitFact.objects query logic lives here - the view delegates
the ORM read to the reader and the logic to the pure builder."""
from django.shortcuts import render

from application.report import build_report
from noon.models import Account
from noon.reporting import read_profit_facts


def report(request):
    """The Noon Report digest. Reads the demo account's reconciled facts through the reader,
    builds the pure report payload, renders it. Read-only: if the demo account does not exist yet
    (unseeded), renders the graceful empty state rather than creating data or erroring."""
    account = Account.objects.filter(name="Demo Account").first()
    facts = read_profit_facts(account) if account is not None else []
    data = build_report(facts)
    return render(request, "noon/report.html", {"report": data})
