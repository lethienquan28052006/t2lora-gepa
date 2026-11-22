Wall time covers search + final test. Tokens are metered for the final greedy test pass only (search rollouts are not metered). `search calls` are optimiser rollouts; `test calls` are the held-out evaluations every arm performs.

| arm | task | wall s | final-test tokens | search calls | test calls | reflection |
|---|---|---|---|---|---|---|
| base | gsm8k | 333 | 245509 | 0 | 1000 | 0 |
| base | arc_challenge | 140 | 98399 | 0 | 1000 | 0 |
| base | boolq | 73 | 44737 | 0 | 1000 | 0 |
| base | hellaswag | 165 | 116450 | 0 | 1000 | 0 |
| base | winogrande | 87 | 60411 | 0 | 1000 | 0 |
| icl3 | gsm8k | 344 | 245960 | 0 | 1000 | 0 |
| icl3 | arc_challenge | 125 | 86272 | 0 | 1000 | 0 |
| icl3 | boolq | 75 | 43920 | 0 | 1000 | 0 |
| icl3 | hellaswag | 110 | 70876 | 0 | 1000 | 0 |
| icl3 | winogrande | 128 | 88920 | 0 | 1000 | 0 |
| t2l | gsm8k | 226 | 123871 | 0 | 1000 | 0 |
| t2l | arc_challenge | 52 | 22111 | 0 | 1000 | 0 |
| t2l | boolq | 32 | 8588 | 0 | 1000 | 0 |
| t2l | hellaswag | 59 | 25783 | 0 | 1000 | 0 |
| t2l | winogrande | 20 | 6405 | 0 | 1000 | 0 |
| t2l_icl | gsm8k | 261 | 141121 | 0 | 1000 | 0 |
| t2l_icl | arc_challenge | 68 | 31238 | 0 | 1000 | 0 |
| t2l_icl | boolq | 31 | 7656 | 0 | 1000 | 0 |
| t2l_icl | hellaswag | 36 | 12110 | 0 | 1000 | 0 |
| t2l_icl | winogrande | 31 | 12030 | 0 | 1000 | 0 |
| gepa_3shot | gsm8k | 901 | 247291 | 1248 | 1000 | 8 |
| gepa_3shot | arc_challenge | 327 | 57502 | 1278 | 1000 | 13 |
| gepa_3shot | boolq | 376 | 45000 | 1302 | 1000 | 17 |
| gepa_3shot | hellaswag | 419 | 70457 | 1230 | 1000 | 5 |
| gepa_3shot | winogrande | 334 | 94137 | 1260 | 1000 | 10 |
| t2l_gepa_opt | gsm8k | 679 | 142117 | 1242 | 1000 | 7 |
| t2l_gepa_opt | arc_challenge | 300 | 53208 | 1230 | 1000 | 5 |
| t2l_gepa_opt | boolq | 112 | 2574 | 1308 | 1000 | 18 |
| t2l_gepa_opt | hellaswag | 218 | 11704 | 1332 | 1000 | 22 |
| t2l_gepa_opt | winogrande | 166 | 11613 | 1332 | 1000 | 22 |
