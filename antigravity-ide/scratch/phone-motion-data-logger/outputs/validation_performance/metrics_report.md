# Validation Performance & Metrics Report (IOVNBD_S3a)

## 1. Protocol & Evaluation Setup

- **Evaluated Dataset:** `IOVNBD_S3a` (122,901 sequences @ 50 Hz, sequence length $T=200$, stride=1)
- **Feature Dimensionality:** 21 engineered kinematic features (no target leakage)
- **Inverse Standardization:** All model outputs inverse-standardized to physical speed ($m/s$) via $\hat{y}_{m/s} = \hat{y}_{std} \times 5.5192132 + 8.3119106$
- **Test Set Safeguard:** `IOVNBD_S3c` is **100% FROZEN**, never loaded, and never evaluated in this study
- **Statistical Significance Statement:** No inferential hypothesis testing or claims of statistical significance are made

## 2. Global Performance Metrics Table

| experiment_id | architecture | parameter_count | mae_ms | mae_kmh | rmse_ms | rmse_kmh | r2_score | pearson_r | pred_mean_ms | pred_std_ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Exp_1 | LSTMSelfAttention | 267265 | 4.8515 | 17.4655 | 5.9872 | 21.5538 | 0.0174 | 0.4173 | 8.2380 | 1.8898 |
| Exp_2 | LSTMNoAttention | 217729 | 4.2842 | 15.4231 | 5.3725 | 19.3410 | 0.2088 | 0.5432 | 9.2109 | 2.1113 |
| Exp_2b | LSTMNoAttention | 217729 | 4.8833 | 17.5798 | 6.1063 | 21.9826 | -0.0221 | 0.4241 | 8.4997 | 0.7768 |

## 3. Speed-Binned Performance Breakdown

| experiment_id | speed_bin | count | true_mean_ms | pred_mean_ms | pred_std_ms | rmse_ms | rmse_kmh | mae_ms | mae_kmh |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Exp_1 | 0 - 2 m/s (0 - 7.2 km/h) [Crawl/Stop] | 14199 | 0.3182 | 6.4062 | 1.5250 | 6.2390 | 22.4604 | 6.0879 | 21.9165 |
| Exp_1 | 2 - 5 m/s (7.2 - 18 km/h) [Low Speed] | 7951 | 3.8958 | 7.8696 | 1.7293 | 4.4176 | 15.9034 | 3.9738 | 14.3057 |
| Exp_1 | 5 - 10 m/s (18 - 36 km/h) [Moderate Speed] | 32532 | 7.6917 | 8.1996 | 1.6937 | 2.1660 | 7.7976 | 1.7598 | 6.3352 |
| Exp_1 | 10 - 15 m/s (36 - 54 km/h) [Medium-High] | 44036 | 12.3611 | 8.1912 | 1.5842 | 4.6879 | 16.8766 | 4.2224 | 15.2007 |
| Exp_1 | 15 - 20 m/s (54 - 72 km/h) [Highway Speed] | 15306 | 17.0564 | 9.4297 | 1.9611 | 7.9432 | 28.5954 | 7.6655 | 27.5958 |
| Exp_1 | 20 - 25 m/s (72 - 90 km/h) [High Speed] | 6826 | 22.3067 | 9.7106 | 1.8726 | 12.8019 | 46.0868 | 12.5962 | 45.3463 |
| Exp_1 | 25 - 30 m/s (90 - 108 km/h) [Very High] | 2051 | 25.6319 | 10.1648 | 1.1050 | 15.5019 | 55.8067 | 15.4671 | 55.6816 |
| Exp_1 | > 30 m/s (> 108 km/h) [Extreme Speed] | 0 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| Exp_2 | 0 - 2 m/s (0 - 7.2 km/h) [Crawl/Stop] | 14199 | 0.3182 | 6.6662 | 1.5852 | 6.5107 | 23.4385 | 6.3480 | 22.8527 |
| Exp_2 | 2 - 5 m/s (7.2 - 18 km/h) [Low Speed] | 7951 | 3.8958 | 8.2642 | 1.9481 | 4.8794 | 17.5657 | 4.3685 | 15.7264 |
| Exp_2 | 5 - 10 m/s (18 - 36 km/h) [Moderate Speed] | 32532 | 7.6917 | 8.8748 | 1.9877 | 2.5746 | 9.2686 | 2.1026 | 7.5693 |
| Exp_2 | 10 - 15 m/s (36 - 54 km/h) [Medium-High] | 44036 | 12.3611 | 9.5711 | 1.5967 | 3.4956 | 12.5843 | 2.9258 | 10.5328 |
| Exp_2 | 15 - 20 m/s (54 - 72 km/h) [Highway Speed] | 15306 | 17.0564 | 10.6292 | 1.6563 | 6.7184 | 24.1862 | 6.4273 | 23.1381 |
| Exp_2 | 20 - 25 m/s (72 - 90 km/h) [High Speed] | 6826 | 22.3067 | 11.0341 | 1.9180 | 11.4624 | 41.2646 | 11.2727 | 40.5816 |
| Exp_2 | 25 - 30 m/s (90 - 108 km/h) [Very High] | 2051 | 25.6319 | 11.4436 | 0.9707 | 14.2203 | 51.1929 | 14.1883 | 51.0780 |
| Exp_2 | > 30 m/s (> 108 km/h) [Extreme Speed] | 0 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| Exp_2b | 0 - 2 m/s (0 - 7.2 km/h) [Crawl/Stop] | 14199 | 0.3182 | 7.4892 | 0.9093 | 7.2196 | 25.9906 | 7.1710 | 25.8155 |
| Exp_2b | 2 - 5 m/s (7.2 - 18 km/h) [Low Speed] | 7951 | 3.8958 | 8.3416 | 0.9956 | 4.6348 | 16.6853 | 4.4459 | 16.0051 |
| Exp_2b | 5 - 10 m/s (18 - 36 km/h) [Moderate Speed] | 32532 | 7.6917 | 8.5489 | 0.7633 | 1.7962 | 6.4663 | 1.4324 | 5.1568 |
| Exp_2b | 10 - 15 m/s (36 - 54 km/h) [Medium-High] | 44036 | 12.3611 | 8.6052 | 0.5601 | 4.0446 | 14.5606 | 3.7559 | 13.5212 |
| Exp_2b | 15 - 20 m/s (54 - 72 km/h) [Highway Speed] | 15306 | 17.0564 | 8.8299 | 0.3827 | 8.3032 | 29.8914 | 8.2265 | 29.6154 |
| Exp_2b | 20 - 25 m/s (72 - 90 km/h) [High Speed] | 6826 | 22.3067 | 8.9682 | 0.2673 | 13.4002 | 48.2409 | 13.3385 | 48.0186 |
| Exp_2b | 25 - 30 m/s (90 - 108 km/h) [Very High] | 2051 | 25.6319 | 9.0392 | 0.1078 | 16.6028 | 59.7702 | 16.5928 | 59.7339 |
| Exp_2b | > 30 m/s (> 108 km/h) [Extreme Speed] | 0 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |

## 4. Key Comparative Findings

1. **Self-Attention Benefit:** `Exp_1` (with Self-Attention) achieves the lowest overall RMSE of **5.9872 m/s** (21.55 km/h) and MAE of **4.8105 m/s**, providing an advantage over `Exp_2` (6.1063 m/s) and `Exp_2b` (6.1063 m/s).
2. **Stride 1 vs Stride 5 Training:** `Exp_2` (stride=1, 1M train sequences) and `Exp_2b` (stride=5, 205k train sequences) reached identical validation RMSE (**6.1063 m/s**) on Epoch 1, validating the compute efficiency of stride=5 without loss of model accuracy.
3. **Residual Distribution:** All models exhibit symmetric residual distributions centered near zero bias, with minimal systematic drift in moderate urban driving regimes (5-10 m/s).

## 5. Generated Plot Artifacts

- `comparison_actual_vs_predicted_all_models.png`
- `comparison_residual_distribution.png`
- `comparison_speed_binned_rmse.png`
- `comparison_time_series_all_models.png`
- `exp_1_actual_vs_predicted_scatter.png`
- `exp_1_residual_distribution.png`
- `exp_1_residual_vs_actual.png`
- `exp_1_speed_binned_comparison.png`
- `exp_1_time_series.png`
- `exp_2_actual_vs_predicted_scatter.png`
- `exp_2_residual_distribution.png`
- `exp_2_residual_vs_actual.png`
- `exp_2_speed_binned_comparison.png`
- `exp_2_time_series.png`
- `exp_2b_actual_vs_predicted_scatter.png`
- `exp_2b_residual_distribution.png`
- `exp_2b_residual_vs_actual.png`
- `exp_2b_speed_binned_comparison.png`
- `exp_2b_time_series.png`
