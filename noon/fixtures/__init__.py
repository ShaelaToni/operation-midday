"""Fixture generators: one per source. Each emits that platform's REAL raw export/response
shape (honest field names and quirks - micros, nested actions, 'spent', etc.) with Faker
values. Generators produce raw dicts ONLY; adapters normalize, the seeder/command persists.
"""
