# Minutes v2 — LightGBM vs the v1 heuristic (A6)

*Generated 2026-07-25 by `PYTHONPATH=src python notebooks/minutes_v2_eval.py --data-root db/vaastav --model db/models/minutes_v2.joblib`.
Train 2022-23 → 2024-25 (vaastav), holdout 2025-26, seed fixed. Raw numbers in
`minutes-v2-metrics.json`; the artifact is gitignored under `db/models/` and regenerable
with `python -m fpl_claude.models.minutes_v2 --train`.*

```
model meta: {'seed': 20262027, 'train_rows': 67529, 'valid_rows': 6292, 'train_seasons': ['2022-23', '2023-24', '2024-25'], 'best_iteration': {'p_start': 107, 'p_play': 111, 'p60': 121, 'mins_given_start': 92}}
cameo minutes constant: 18.35
cold-start rows excluded (v2 declines, v1 prior path used): 429 of 29,757
==============================================================================
HEADLINE — 2025-26 holdout, n=29,328 player-fixtures
==============================================================================
 target  base_rate  v1_logloss  v2_logloss  v1_brier  v2_brier  v1_auc  v2_auc
p_start    0.28311     0.45412     0.24574   0.11155   0.07590 0.90605 0.95414
    p60    0.26463     0.38608     0.25233   0.10952   0.07881 0.90521 0.94908

expected minutes
model     mae    rmse   bias
   v1 18.7503 26.4526 0.7967
   v2 12.3964 21.3330 0.0553

==============================================================================
CALIBRATION BY DECILE of predicted probability (p_start)
==============================================================================

v1
 decile    n  mean_pred  actual
      1 2933     0.0000  0.0331
      2 2933     0.0000  0.0119
      3 2933     0.0000  0.0109
      4 2932     0.0000  0.0044
      5 2933     0.0209  0.0518
      6 2933     0.1753  0.2543
      7 2932     0.3570  0.3786
      8 2933     0.5595  0.5138
      9 2933     0.7744  0.6966
     10 2933     0.9688  0.8756

v2
 decile    n  mean_pred  actual
      1 2933     0.0030  0.0003
      2 2933     0.0038  0.0000
      3 2933     0.0050  0.0027
      4 2932     0.0086  0.0061
      5 2933     0.0309  0.0331
      6 2933     0.1048  0.1207
      7 2932     0.2876  0.2834
      8 2933     0.6138  0.6038
      9 2933     0.8425  0.8445
     10 2933     0.9363  0.9362

==============================================================================
CALIBRATION BY DECILE (p60)
==============================================================================

v1
 decile    n  mean_pred  actual
      1 2933     0.0000  0.0269
      2 2933     0.0000  0.0095
      3 2933     0.0000  0.0106
      4 2932     0.0000  0.0034
      5 2933     0.0190  0.0433
      6 2933     0.1637  0.2237
      7 2932     0.3364  0.3428
      8 2933     0.5331  0.4695
      9 2933     0.7442  0.6611
     10 2933     0.9425  0.8554

v2
 decile    n  mean_pred  actual
      1 2933     0.0021  0.0003
      2 2933     0.0028  0.0000
      3 2933     0.0041  0.0024
      4 2932     0.0076  0.0044
      5 2933     0.0264  0.0310
      6 2933     0.0913  0.1057
      7 2932     0.2591  0.2435
      8 2933     0.5619  0.5503
      9 2933     0.7953  0.8012
     10 2933     0.9102  0.9073

==============================================================================
SLICES — where the decisions actually get made
==============================================================================
                           slice     n    base  v1_ll_start  v2_ll_start  v1_ll_p60  v2_ll_p60  v1_mae_min  v2_mae_min
                             ALL 29328 0.28311      0.45412      0.24574    0.38608    0.25233     18.7503     12.3964
       congested (<=4 rest days)  4146 0.28075      0.41629      0.24583    0.37647    0.25377     18.8276     12.3866
          normal rest (5-8 days) 14591 0.28264      0.43647      0.23007    0.36935    0.23994     18.3231     11.7146
             long rest (>8 days)  7624 0.28069      0.50574      0.26362    0.41028    0.26337     18.7105     12.9739
        3+ fixtures in prior 14d  2056 0.28259      0.37115      0.22520    0.34911    0.23406     18.6370     11.9835
                 midweek kickoff  4533 0.27620      0.42728      0.24517    0.38442    0.25072     19.2900     12.3409
                    AFCON window  4888 0.28294      0.45254      0.24608    0.41242    0.25482     19.7120     12.6485
Euro-week clubs (in UEFA period)  7200 0.29000      0.49813      0.28209    0.40852    0.28438     18.9837     13.8841
        post international break  2658 0.28819      0.59974      0.26884    0.45423    0.26938     18.1568     13.1113
    nailed (start share5 >= 0.8)  6315 0.81758      0.76253      0.38324    0.56007    0.43620     27.6257     19.9348
        rotation-prone (0.3-0.8)  4098 0.47584      0.75481      0.53048    0.73139    0.53709     35.0719     26.6558
                  fringe (< 0.3) 18915 0.06291      0.28601      0.13815    0.25318    0.12926     12.2510      6.7903
                             GKP  3364 0.22414      0.27516      0.11661    0.23634    0.12203     13.8879      5.9098
                             DEF  9610 0.32945      0.51431      0.27972    0.43781    0.29000     21.4379     14.6979
                             MID 13120 0.27119      0.45230      0.25602    0.38251    0.25924     18.4348     12.5608
                             FWD  3234 0.25510      0.46882      0.23742    0.40263    0.24791     17.1020     11.6380

==============================================================================
BENCH-ORDER READ — within-gameweek ranking of P(plays 60+)
==============================================================================
model  gws  mean_within_gw_auc  worst_gw_auc
   v1   38              0.9032        0.7659
   v2   38              0.9457        0.7695

Top-ownership decile only (n=2,933) — the pool our XI comes from
model  log_loss   brier     auc  mean_pred  base_rate
   v1   0.53452 0.16668 0.74818    0.80060    0.73645
   v2   0.39514 0.12231 0.84474    0.73901    0.73645

Confident-and-wrong rate (p_start > 0.5 but 0 minutes played)
model  confident_rows  blanked   rate
   v1            7868     1417 0.1801
   v2            8354      809 0.0968

==============================================================================
FEATURE IMPORTANCE (gain) — p_start head, top 20
==============================================================================
  mins_last                    279,721   63.3%
  mins_mean_3                   76,435   17.3%
  mins_mean_5                   14,024    3.2%
  mins_mean_10                  14,023    3.2%
  started_last                  12,982    2.9%
  prior_mins_per_game            5,878    1.3%
  days_since_prev                3,897    0.9%
  start_share_season             3,795    0.9%
  selected_log                   3,372    0.8%
  p60_rate_season                3,193    0.7%
  price_share_team_pos           2,665    0.6%
  price                          2,454    0.6%
  days_to_next                   2,356    0.5%
  cameo_rate                     2,271    0.5%
  hist_games                     1,608    0.4%
  gw                             1,526    0.3%
  price_rank_team_pos            1,433    0.3%
  prior_start_share              1,337    0.3%
  benched_streak                 1,180    0.3%
  element_type                   1,105    0.2%

(analysis complete)
```
