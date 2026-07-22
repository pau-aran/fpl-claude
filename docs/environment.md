# Claude Code on the web — environment setup

State of the remote environment as tested on 2026-07-22, and what to change to
unblock the season workflows.

## What already works (no action needed)

- **Package registries** (PyPI etc.) — dependency install works under any policy.
  The SessionStart hook (`.claude/hooks/session-start.sh`) installs the package
  with `dev`, `models` and `optimize` extras plus `penaltyblog`, so every
  session starts with the full test suite green (29 tests) — no manual setup.
- **github.com / raw.githubusercontent.com** — reachable. The vaastav
  historical dataset and FPL-Core-Insights (backtest gate, PLAN §4) can be
  pulled today.
- **WebSearch** — runs server-side, outside the sandbox egress, so news/rules
  research works even while direct fetches are blocked. WebFetch does NOT
  (it goes through the sandbox proxy and gets the same 403s).

## What is blocked (needs a network-policy change)

The environment's egress policy returns 403 for every non-GitHub project
domain. Fix: in the environment's settings on claude.ai/code, either switch to
trusted network access or add this allowlist:

| Domain | Needed for |
|---|---|
| `fantasy.premierleague.com` | FPL API snapshots (`/fpl-refresh`) — **highest priority** |
| `www.football-data.co.uk` | Dixon-Coles training data |
| `www.premierleague.com` | Official fixtures/news |
| `understat.com` | xG rates (later phase) |
| `www.premierinjuries.com` | Injury table (`/fpl-news-sweep`) |
| `www.fantasyfootballscout.co.uk` | Team news, strategy consensus |
| `www.livefpl.net` | Price predictions, EO |
| `fplreview.com` | Projection benchmarks |
| `www.bbc.com`, `www.skysports.com` | Press conferences, team news |
| `www.reddit.com` | r/FantasyPL sentiment |

(Full curated source list with tiers: `config/sources.yaml`.)

## Re-testing after a policy change

```bash
curl -sS -o /dev/null -w "%{http_code}\n" https://fantasy.premierleague.com/api/bootstrap-static/
# 200 → unblocked; 000 → still policy-blocked (proxy 403 on CONNECT)
curl -sS "$HTTPS_PROXY/__agentproxy/status"   # recentRelayFailures names blocked hosts
```
