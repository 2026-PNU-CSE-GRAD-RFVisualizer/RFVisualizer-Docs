# KMMS 논문 1~2일차 실험 근거 정본

- 확정일: 2026-08-10
- 목적: 재측정 없이 현재 복도 실험에서 논문에 사용할 입력, 좌표, 지표와 한계를 고정한다.
- 상태: **예비 복도 평가 근거로 사용 가능**. 반복 안정성이 확인된 최종 정확도 근거는 아니다.

## 1. 이번 논문에 사용할 실험

| 구분 | 선택 | 이유 |
| --- | --- | --- |
| 사용 실행 | `Test_1_004838`, `Test_2_010416` | 같은 Proxy 문 상태에서 측정한 두 반복 |
| 제외 실행 | `Test_3_011702` | 현장 기록상 철문 상태가 Proxy와 달라 동일 조건 비교가 아님 |
| 주 Sionna 조건 | `doors_glass_diffraction_scattering_authored_100m_d5` | 기존에 주 조건으로 고정한 회절·산란 포함 조건 |
| 주 평가 단위 | `repeat_mean_6` | 같은 위치의 두 반복을 먼저 평균한 6개 독립 Test 위치 |
| Calibration/Test | 4개/6개 | Calibration만 보정에 사용하고 Test는 평가에만 사용 |

Test 3 제외 사유는 현재 세션 원본의 `note`가 아니라 프로젝트 현장 기록에 남아 있다. 논문에는 “환경 조건 불일치로 사전 제외”라고 쓰고, 원본 로그 자체에 문 상태가 기록된 것처럼 표현하지 않는다.

## 2. 원본 데이터에서 확인한 제한

| 항목 | 확인 결과 | 논문 처리 |
| --- | --- | --- |
| Backend `points.csv` | Test 1·2 모두 헤더만 있고 좌표 행이 없음 | 기존 장치 배치 계약으로 좌표·역할을 복원했다고 명시 |
| 원본 Backend QC | 좌표 미등록과 Calibration 개수 불일치로 `ok=false` | 원본 Export가 완전했다고 주장하지 않음 |
| BSSID | Test 1·2 원본의 모든 행이 비어 있음 | “고정 BSSID 확인”이라고 쓰지 않고 미기록 한계로 보고 |
| 채널 | Test 1·2 원본의 모든 행이 비어 있음 | “채널 고정 확인”이라고 쓰지 않고 미기록 한계로 보고 |
| 유효 Test 표본 | Test 1은 위치당 29~30개, Test 2는 25~29개 | 목표 최소 표본 수는 충족 |
| 좌표 복원 후 분할 | 각 실행마다 Calibration 4개, Test 6개 | 복원된 분석 입력에서 분할 확인 |

따라서 현재 결과는 **실제 측정값을 사용한 예비 평가**이지만, 원본 Export만으로 좌표와 현장 무선 조건이 완전히 재현되는 최종 데이터는 아니다.

## 3. 논문에 사용할 좌표

| 역할 | 지점 | 장치 | X (m) | Y (m) | Z (m) |
| --- | --- | --- | ---: | ---: | ---: |
| 실측 TX | `tx-01` | AP | 3.13 | 0.50 | 0.45 |
| Calibration | `cal-01` | `gw-01` | 3.13 | 3.93 | 0.45 |
| Calibration | `cal-02` | `node-01` | 8.08 | 3.93 | 0.45 |
| Calibration | `cal-03` | `node-03` | 10.56 | 10.68 | 0.45 |
| Calibration | `cal-04` | `node-04` | 8.69 | 15.01 | 0.45 |
| Test | `test-01` | `node-02` | 0.65 | 3.93 | 0.45 |
| Test | `test-02` | `node-02` | 5.60 | 3.93 | 0.45 |
| Test | `test-03` | `node-02` | 10.56 | 3.93 | 0.45 |
| Test | `test-04` | `node-02` | 6.42 | 11.20 | 0.45 |
| Test | `test-05` | `node-02` | 6.92 | 15.01 | 0.45 |
| Test | `test-06` | `node-02` | 10.56 | 15.01 | 0.45 |

Sionna TX는 X=3.15 m로 설정되어 실측 TX의 X=3.13 m와 0.02 m 차이가 있다. 이 차이는 숨기지 않고 좌표 한계에 포함한다.

## 4. 논문에 사용할 네 방법 결과

두 반복의 같은 Test 위치를 먼저 평균한 6개 독립 위치 기준이다.

| 방법 | MAE (dB) | RMSE (dB) | ME (dB) | 최대 절대오차 (dB) | Pearson r |
| --- | ---: | ---: | ---: | ---: | ---: |
| Raw Sionna RT | 14.90 | 15.54 | 14.90 | 20.98 | 0.970 |
| Plain IDW | 13.05 | 16.22 | 13.05 | 26.64 | 0.475 |
| Sionna RT + Residual IDW | 10.10 | 12.68 | 10.10 | 21.41 | 0.709 |
| Sionna RT + Global Bias | **7.48** | **8.58** | **7.37** | **13.45** | **0.970** |

- Residual IDW는 Plain IDW보다 MAE를 22.62%, RMSE를 21.83% 줄였다.
- 따라서 H3은 **6개 위치의 예비 평가 범위에서 지지**된다.
- 가장 단순한 Global Bias가 가장 낮은 오차를 보였다. 이를 숨기지 않고 네 번째 기준선으로 제시한다.
- Global Bias MAE의 위치 bootstrap 95% 구간은 3.91~10.64 dB다.

## 5. 반복 안정성 판정

| 항목 | 결과 | 판정 |
| --- | ---: | --- |
| Calibration 반복 차이 | 평균 10.25 dB, 최대 16.00 dB | 불안정 |
| Test 반복 차이 | 평균 6.08 dB, 최대 13.00 dB | 제한적 |
| 5 dB 이내 Calibration | `cal-04` 1개 | 부족 |
| Test 1 장치 보정 전/후 범위 | 14.0 → 0.0 dB | 같은 보정 측정 안에서는 정렬됨 |
| Test 2 장치 보정 전/후 범위 | 19.0 → 0.0 dB | 같은 보정 측정 안에서는 정렬됨 |
| 실행 간 장치 Offset 변화 | 평균 5.9 dB, 최대 15.0 dB | 반복 안정성 미확보 |

원시 `median_filtered`의 두 실행 간 평균 차이는 Calibration 4.13 dB, Test 3.42 dB였다. 실행별 Device Offset을 적용한 뒤에는 각각 10.25 dB와 6.08 dB로 커졌다. 따라서 H2는 “한 번의 공통 위치 측정 안에서 장치 중앙값을 정렬한다”는 범위에서는 성립하지만, 같은 Offset이 반복 실행에서도 안정적이라는 근거는 없다.

## 6. 논문 가설 최종 판정

| 가설 | 판정 | 논문에서 사용할 표현 |
| --- | --- | --- |
| H1: Proxy 차폐 구조가 Sionna RT에 반영됨 | 지지 | 합성 기능 검증 범위에서 직접 경로와 Coverage 변화 확인 |
| H2: Device Offset이 장치 편차를 줄임 | 부분 지지 | 실행 내부 정렬은 확인했지만 실행 간 안정성은 확인하지 못함 |
| H3: Residual IDW가 Plain IDW보다 오차가 낮음 | 지지 | 6개 독립 Test 위치의 예비 평가에서 MAE/RMSE 모두 감소 |

## 7. 재계산 검증

2026-08-10에 현재 저장소의 원본으로 분석을 다시 실행했다.

- `metrics.csv`: 기존 산출물과 바이트 단위 일치
- `calibration_qc.csv`: 기존 산출물과 바이트 단위 일치
- `repeatability.csv`: 기존 산출물과 바이트 단위 일치
- `measurements_reconstructed.csv`: 기존 산출물과 바이트 단위 일치
- `analysis_report.json`: 수치와 SHA-256은 일치하며, 저장소 재배치로 기록된 상대 경로만 달라짐

주 근거:

- `../../../RFVisualizer/scenes/pnu_4f_corridor/rf_experiment/spreadsheet/doors_glass_100m_d5_tests_1_2/processed/analysis_report.json`
- `../../../RFVisualizer/scenes/pnu_4f_corridor/rf_experiment/spreadsheet/doors_glass_100m_d5_tests_1_2/processed/metrics.csv`
- `../../../RFVisualizer/scenes/pnu_4f_corridor/rf_experiment/spreadsheet/doors_glass_100m_d5_tests_1_2/processed/measurements_reconstructed.csv`
- `../../../RFVisualizer/scenes/pnu_4f_corridor/rf_experiment/spreadsheet/doors_glass_100m_d5_tests_1_2/RESULTS_SUMMARY.md`

## 8. 주장 경계

### 말할 수 있는 것

- 실제 복도에서 3D 장면, Sionna RT와 ESP32 RSSI를 같은 좌표로 비교했다.
- 제한된 예비 평가에서 Residual IDW가 Plain IDW보다 낮은 오차를 보였다.
- Global Bias가 네 방법 중 가장 낮은 오차를 보였다.

### 말하면 안 되는 것

- 반복 측정에서도 7.48 dB 정확도가 안정적으로 재현됐다.
- 회절·산란 설정이 Base보다 우수하다.
- BSSID와 채널이 원본 데이터로 확인됐다.
- 좌표가 Backend 원본 Export에 완전하게 포함돼 있었다.
- 현재 재질 계수가 실제 복도 물성을 정확히 나타낸다.
