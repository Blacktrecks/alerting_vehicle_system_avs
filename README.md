# Proximity and Impact Warning System

University embedded-systems project (course "Proiectarea sistemelor incorporate", labs L1-L5).

The README is rewritten in phase P6 (see AGENTS.md for the project rules).

Quick check on a laptop (no hardware):

    python -m venv .venv && . .venv/bin/activate
    pip install -r requirements.txt
    MCD_SIMULATE=1 python manage.py test
    DJANGO_DEBUG=1 MCD_SIMULATE=1 python manage.py runserver
