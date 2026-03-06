## Cooldown Info

| Key | Value |
|---|---|
| Cooldown ID | `cd001` |
| Date | 2026-03-06 |
| Fridge | your-cryo |

### Control

| Line ID | Qubit(s) | Atten (dB) | Gain (dB) | RT | 50K | 4K | Still | CP | MXC |
|---|---|---|---|---|---|---|---|---|---|
| C00 | Q00 | 50 | - | - | ATT 10dB | ATT 20dB | Lowpass | - | ATT 20dB, Eccosorb |
| C01 | Q01 | 50 | - | - | ATT 10dB | ATT 20dB | - | - | ATT 20dB, Eccosorb |
| C02 | Q02 | 50 | - | - | ATT 10dB | ATT 20dB | - | - | ATT 20dB, Eccosorb |
| C03 | Q03 | 40 | - | - | ATT 10dB | ATT 10dB | - | - | ATT 20dB |
| C04 | Q04 | 50 | - | - | ATT 10dB | ATT 20dB | - | - | ATT 20dB, Eccosorb |
| C05 | Q05 | 40 | - | - | ATT 10dB | ATT 10dB | - | - | ATT 20dB |
| C06 | Q06 | 50 | - | - | ATT 10dB | ATT 20dB | - | - | ATT 20dB, Eccosorb |
| C07 | Q07 | 50 | - | - | ATT 10dB | ATT 20dB | - | - | ATT 20dB, Eccosorb |

### Readout Send

| Line ID | Qubit(s) | Atten (dB) | Gain (dB) | RT | 50K | 4K | Still | CP | MXC |
|---|---|---|---|---|---|---|---|---|---|
| RS00 | Q00, Q01, Q02, Q03 | 20 | - | - | ATT 10dB | ATT 10dB | - | - | - |
| RS01 | Q04, Q05, Q06, Q07 | 20 | - | - | ATT 10dB | ATT 10dB | - | - | - |

### Readout Return

| Line ID | Qubit(s) | Atten (dB) | Gain (dB) | RT | 50K | 4K | Still | CP | MXC |
|---|---|---|---|---|---|---|---|---|---|
| RR00 | Q00, Q01, Q02, Q03 | - | 60 | RT +20dB | HEMT +40dB | - | - | ISO | - |
| RR01 | Q04, Q05, Q06, Q07 | - | 60 | RT +20dB | HEMT +40dB | - | - | ISO, ISO | - |