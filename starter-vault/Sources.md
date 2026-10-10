---
created: 2026-10-10
---
# Sources

Every place material comes into this vault from: what it brings, how it gets here, and how
often. The `harvest` skill fills this in with you. `bin/ingest.py add --via "<Source>"` stamps
**Last pulled** on the matching row (and adds the row if it is new), and
`bin/ingest.py report` says which sources are due and which ones you actually use.

- **Cadence**: once (a backfill), daily, weekly, monthly, or as it comes.
- **Keep?**: yes, trial (new, judge it after a month), or no (stopped; the row stays so you
  remember why).

| Source | What comes from it | How | Cadence | Last pulled | Keep? |
|---|---|---|---|---|---|

## Not brought in, on purpose

What was considered and left out, and why, so it is not reconsidered every month.

- 
