# 그래픽스 파트 작업 목록 — corridor3f_20260820

- 대상 저장소: `RFVisualizer` (로컬 `/data/RFVisualizer_Workspace/RFVisualizer`)
- 작성일: 2026-08-21
- 전제: 대상 AP는 인터넷에 연결되어 있다.

## 사람이 볼 요약

**측정을 막는 건 없습니다. 대신 "측정한 데이터를 계획서대로 계산할 준비"가 아직 안 돼 있습니다.**

1. ~~분석기가 계획서와 다른 파일을 읽습니다.~~ → **2026-08-21 해결.** `analyze --test-points ... --calibration-window ...` 로 Segment 단위 평가와 정/역 분리 지표가 나옵니다. 아래 1번 항목에 결과를 정리했습니다.
2. **Scene이 아직 draft**(장애물·재질 미반영) → 현재 Sionna 값은 `paper_evidence_eligible: false`. 논문 수치로 쓰려면 재실행이 필요합니다.
3. **측정 뒤에 반드시 할 것**: 줄자 실측 길이 1개로 배율 재보정 → 좌표 15개 재생성 → Sionna 재실행.

**측정 전에 할 수 있는 코드 작업은 1번·3번으로 끝났습니다.** 남은 4·5·6번은 각각
GUI 배치 작업, 현장 상황, 측정 결과가 있어야 합니다.

| # | 할 일 | 언제 | 크기 |
|---|---|---|---|
| 1 | ~~`analyze` 입력을 Segment 단위로 확장~~ **완료 (2026-08-21)** | — | 완료 |
| 2 | 좌표 CSV를 네트워크에 전달 | 지금 | 완료(아래 첨부) |
| 3 | ~~미수신·절단 지점 처리 규칙 결정~~ **완료 (2026-08-21)** | — | 완료 |
| 4 | 장애물·재질 반영 후 Sionna 재실행 | 측정 전이 이상적 | 대 |
| 5 | 현장에서 좌표가 바뀌면 재생성 절차 | 현장 | 명령 3개 |
| 6 | 실측 길이로 배율 재보정 | 측정 후 | 명령 2개 |

---

# 상세 (에이전트용)

## 1. `analyze` 입력이 계획서 §7 규칙과 맞지 않는다 — **완료 (2026-08-21)**

### 문제(당시)
계획서 §7의 데이터 사용 규칙은 다음과 같다.

- 각 Test는 **같은 `segment_id`, 같은 2분 시간대의 C1~C4**와 비교한다.
- C1~C4의 전체 Run 평균 하나를 모든 Test에 공통 적용하지 **않는다.**
- 정방향·역방향을 한 Run으로 합치지 **않는다.**

백엔드는 정확히 그 용도로 두 파일을 만든다.

| 파일 | 내용 |
|---|---|
| `processed/test_points.csv` | Segment별 Test 대표값 (`run_id`, `direction`, `segment_id`, `attempt_index` 포함) |
| `processed/calibration_by_test_window.csv` | 각 Segment와 **동일 시간창**의 C1~C4 |

그런데 현재 분석기는 `measurements_summary.csv` **하나만** 받는다.

- `tools/rf_experiment/main.py:69` — `analysis.add_argument("--summary", required=True)`
- `tools/rf_experiment/analysis.py:30` — `run_analysis(summary_path, ...)`
- `tools/rf_experiment/analysis_inputs.py:51` — `load_summary()`, 필수 열
  `point_id, point_role, node_id, x, y, z, corrected_rssi`, **`point_id` 중복 금지**

`measurements_summary.csv`는 백엔드에서 `(point_id, node_id)`로 묶은 **실험 전체 집계**다
(`backend/export.py:96 summarize()`). 따라서
**정방향과 역방향이 한 행으로 합쳐지고**, `segment_id`·`direction`이 없다.
지금 그대로 돌리면 계획서가 금지한 "전체 평균 방식"으로 계산된다.

### 선택지
**A. 분석기 확장 (권장, 논문 서술과 일치)**
- `analyze`에 `--test-points`, `--calibration-window` 인자 추가
- `load_summary()` 옆에 `load_test_points()` / `load_calibration_window()` 추가
  - 키: `(run_id, segment_id)` — `point_id` 중복 금지 규칙을 여기서는 적용하면 안 된다
  - 좌표는 `x, y, z`, 값은 `corrected_rssi`
- `analysis_compute.py:69 compare_methods()`를 Segment 단위로 호출:
  Segment마다 그 창의 C1~C4로 IDW/Residual을 fitting하고 해당 Test 1점을 평가
- 지표를 `direction`별(정/역)로 나눠 산출 → 계획서 §2-4 "반복성 확인" 충족
- `--summary` 경로는 진단용으로 남겨둔다(하위 호환)

**B. 어댑터 스크립트 (최소 노력)**
`test_points.csv` + `calibration_by_test_window.csv`를 읽어 Segment별로
`summary` 형식 CSV를 만들어 기존 `analyze`를 Segment 수만큼 돌린다.
빠르지만 Segment마다 출력 디렉터리가 생겨 집계를 따로 합쳐야 한다.

### 실제로 한 것 (A안, 2026-08-21)

| 파일 | 변경 |
|---|---|
| `analysis_inputs.py` | `load_segments()` 추가. `test_points.csv` + `calibration_by_test_window.csv` 를 `segment_id` 로 짝지어 읽는다. Test 행이 없는 Segment(= 그 위치 미수신)는 실패가 아니라 목록으로 반환한다 |
| `analysis_compute.py` | `compare_methods_by_segment()` 추가. Segment 마다 **그 시간창의 calibration 만** 으로 Plain/Residual IDW 를 구성하고 Test 1점을 평가. `direction` 별 지표를 따로 산출 |
| `analysis_export.py` | `comparison_results.csv` 에 `run_id/direction/segment_id/attempt_index` 열 추가, `metrics_by_direction.csv` 신규, 보고서에 `evaluation_mode`·`heatmap_calibration_source` 추가, README 에 방향별 표 추가 |
| `analysis.py` | `run_segment_analysis()` 추가. 출처 기록 로직은 `_input_provenance()` 로 공용화 |
| `main.py` | `analyze` 에 `--test-points` / `--calibration-window` 추가. `--summary` 는 선택(진단용)으로 바뀌었고, 둘 중 하나는 반드시 지정해야 한다 |
| `tests/test_analysis.py` | Segment 단위 테스트 5개 추가 |
| `tools/rf_experiment/README.md` | 두 입력 경로 문서화 |

핵심 판단 두 가지를 기록해 둔다.

- **히트맵은 지점별 전체 시간창 평균 calibration을 쓴다**
  (`heatmap_calibration_source = mean_of_test_segment_windows`).
  Segment 마다 히트맵을 20장 만드는 것은 의미가 없어서다.
  **그림 전용이며 MAE/RMSE 계산에는 쓰이지 않는다**는 사실을 보고서와 README 에 남긴다.
- **좌표 검증을 유지했다.** 측정 좌표와 Sionna 예측 좌표가 1 µm 이상 다르면 즉시 실패한다.
  현장에서 예비 좌표로 옮겼다면 `run-sionna` 를 다시 돌려야 통과한다(5번 절차).

### 검증 (완료)
- `pytest tools/rf_experiment/tests` — 30개 통과 (신규 5개 포함)
- Segment 마다 편차가 다른 합성 입력에서, 같은 시간창 보정을 쓸 때만
  Residual IDW MAE 가 0 이 되는 것을 확인 (Run 전체 평균을 쓰면 오차가 남는다)
- 한 Segment 의 calibration 을 바꿔도 **다른 Segment 예측은 변하지 않음**을 확인
- Test 실측값을 100 dB 흔들어도 예측이 변하지 않음(fitting 미사용) 확인
- 실제 `processed/sionna_points.csv`·`sionna_grid.csv` 와 합성 Segment CSV 로 CLI 종단 실행:
  20 Segment(정 10 + 역 10), Segment 당 calibration 4대, 방향별 지표 산출,
  Scene 이 draft 라 `paper_evidence_eligible: false` 가 그대로 전파됨을 확인

### 실제 Backend Export 로 확인 (2026-08-21, 완료)
Backend 저장소에서 `python rehearsal.py --reverse` 를 돌려 나온 **실물 Export** 로 검증했다.

```
segments: 20 | by direction: {'forward': 10, 'reverse': 10}
  raw_sionna    MAE 0.570   plain_idw MAE 4.359   residual_idw MAE 0.227
forward residual MAE 0.211 / reverse residual MAE 0.243
evaluation_mode: per_test_segment_window
```

BOM(`utf-8-sig`) 붙은 Backend CSV 를 그대로 읽고, `run_id`·`direction`·`segment_id` 가
비교 CSV 에 실리는 것까지 확인했다. (Sionna 입력은 리허설 좌표에 맞춰 합성한 값이다.)

## 2. 좌표 CSV를 네트워크 파트에 전달 (완료)

백엔드는 실험 시작 시 `POST /experiment/points/import`로 좌표를 등록해야 하고,
이 좌표가 Export의 **유일한** 출처다(network.md 3번). 등록하지 않으면 전 좌표가 빈다.
등록용 CSV 와 절차는 `network.md` 3번에 정리해 두었다.
`configs/tx_rx.json`에서 생성했으며 계획서 §5 표와 일치한다.

```csv
point_id,point_role,pos_x,pos_y,pos_z,note
cal-01,calibration,34.9,18.7,0.45,C1
cal-02,calibration,24.02,6.31,0.45,C2
cal-03,calibration,16.07,6.31,0.45,C3
cal-04,calibration,5.86,18.56,0.45,C4
test-01,test,12.57,17.83,0.45,T1
test-02,test,1.8,17.8,0.45,T2
test-03,test,1.76,6.9,0.45,T3
test-04,test,5.17,5.31,0.45,T4
test-05,test,10.9,5.31,0.45,T5
test-06,test,20.04,5.31,0.45,T6
test-07,test,31.57,5.31,0.45,T7
test-08,test,37.93,6.9,0.45,T8
test-09,test,37.93,16.88,0.45,T9
test-10,test,30.1,17.83,0.45,T10
```

좌표가 바뀌면 `tx_rx.json` → 이 CSV → 백엔드 등록 순서로 함께 갱신한다(5번 참고).

## 3. 미수신·절단 지점 처리 규칙 — **완료 (2026-08-21)**

### 배경
임베디드·백엔드의 유효 하한이 -100 → -110으로 바뀌어도(embedded.md 1·2, network.md 1),
**ESP32 실제 수신 감도(-95 ~ -100 dBm 부근) 아래는 여전히 못 잡는다.**
게다가 4층 실험에서 Sionna 원본이 실측보다 평균 14.9 dB 높게 나왔으므로
cal-02(-106.7), cal-03(-105.3), test-05(-101.1), test-06(-106.7), test-07(-97.7)은
실제로 더 낮을 가능성이 크다.

### 정해야 할 것
- **Test 미수신**을 MAE/RMSE에서 어떻게 다룰지: 제외 / 감도 한계값으로 대입(censored) / 별도 표로 보고
  → 제외한다면 "몇 개를 왜 제외했는지"를 지표 표에 반드시 병기한다.
- **경계 지점의 절단 편향**: -100 부근 샘플이 잘리면 중앙값이 위로 치우친다.
  하한을 -110으로 내리면 완화되지만, 감도 한계 자체는 남는다는 점을 논문 한계로 기록한다.
- **Calibration 미수신은 대체 불가** — cal-02/cal-03이 안 잡히면 계획서 §8의 예비 좌표로 옮긴다
  (현장 판단, 5번 절차).

### 정한 규칙 (`configs/method_config.json` 의 `evaluation.missing_measurement_policy`)

```json
{
  "rule": "exclude_and_report",
  "imputation": "none",
  "receiver_sensitivity_floor_dbm": -100.0,
  "report_field": "input_provenance.segments_without_test_measurement"
}
```

- **미수신 Test 는 MAE/RMSE 에서 제외하고, 제외한 Segment 를 보고서에 남긴다.**
  분석기가 이미 그렇게 동작한다(`load_segments()` 가 Test 행 없는 Segment 를 목록으로 반환).
- **값을 대입(imputation)하지 않는다.** 감도 한계값을 넣으면 그 값이 MAE 를 좌우한다.
  설정이 대입을 요구하면 조용히 무시하지 않고 **실패**시킨다(`_evaluation_policy()`).
- 절단 편향(감도 부근에서 약한 표본이 잘려 중앙값이 위로 치우침)은 논문 한계로 기록한다.
- **Calibration 미수신은 제외 대상이 아니다.** 보정을 못 하므로 계획서 §8 예비 좌표로 옮긴다.

규칙은 `analysis_report.json` 의 `evaluation_policy` 에 그대로 실린다.
설정에만 있고 코드가 읽지 않는 죽은 값이 되지 않도록, 지원하지 않는 규칙이면 분석이 멈춘다.
테스트 2개로 확인한다.

## 4. Scene draft 해소 (장애물·재질)

### 현재 상태
- `configs/scene.json` → `"status": "draft"`, `proxy_scene.status = "pending_obstacle_placement"`
- `sionna_rssi_report.json` → `draft_execution_allowed: true`, **`paper_evidence_eligible: false`**
  (즉 현재 `processed/sionna_points.csv`는 `--allow-draft`로 뽑은 값이다)
- 문·계단·금속문 배치와 재질 실측이 남아 있다.
- `materials.*.scattering_coefficient = 0.3`은 문헌 중간값이며 실측이 아니다.

### 할 일
1. `tools.proxy_placement_editor.main edit`로 장애물 배치 (README §10 명령)
2. `configs/scene.json`의 `status`를 `ready`로 올리고 `validate-contracts --require-ready` 통과 확인
3. `run-sionna`를 `--allow-draft` **없이** 재실행 → `paper_evidence_eligible: true` 확인
4. `processed/sionna_points.csv`, `figures/raw_sionna_rssi_map.png` 재생성

### 주의
회절·산란 설정(`max_depth=5`, `enable_diffraction/scattering=true`, `samples 8M / paths 40M`)을
바꾸지 않는다. 정반사만 쓰던 이전 조건과 **결과를 섞어 비교하지 않는다.**
깊은 그림자 지점은 8M 샘플에서도 약 ±3 dB 흔들리므로 그 불확실성을 달고 해석한다.

## 5. 현장에서 좌표가 바뀌었을 때 (예비 좌표 사용 시)

계획서 §8 예비 좌표: C2 → `(34.40, 6.60, 0.45)`, C3 → `(8.10, 6.60, 0.45)`,
둘 다 실패 시 `(37.40, 1.38, 0.45)`.

### 절차 (순서 중요)
1. `scripts/make_markers.py`의 `MARKERS` 표(50행)를 수정하고 실행
   → `configs/tx_rx.json`과 도면이 함께 갱신되고, 배치 규칙 3종
   (실내·벽 여유 0.5 m / 보정-Test 3 m / 보정 집합 LOS·NLOS 혼합)을 자동 검사한다
2. 2번의 좌표 CSV를 다시 뽑아 **백엔드에 재등록**한다 (`POST /experiment/points/import`)
3. `validate-contracts` + `proxy_placement_editor validate` 재실행
4. `run-sionna` 재실행 (예측값이 바뀌므로 Raw Sionna 지표가 달라진다)
5. `Embedded/node_positions.json`은 **건드리지 않는다** (좌표 출처를 하나로 유지)

### 알고 쓸 것 — 예비 좌표의 부작용
예비 좌표를 **둘 다** 쓰면 보정점이 C2b `X=34.4`, C3b `X=8.1`로 좁은 복도 **양 끝**에만 남는다.
그 사이(X 10~31)에 보정점이 하나도 없어 **T5·T6·T7이 전부 외삽**이 된다.
LOS/NLOS 혼합 원칙은 지켜지지만 공간 커버리지는 나빠진다. 사용했다면 결과 해석에 명시한다.

## 6. 측정 후: 실측 길이로 배율 재보정

현재 미터 배율은 **층고 3.0 m 가정 하나**에만 의존한다(`4.252497 m / 장면단위`).
도면 정합 IoU 0.74, 좌표 불확실성 약 ±0.5 m.

현장에서 긴 수평 길이 하나(넓은 복도 벽-벽 거리 또는 T1–T10 거리)를 줄자로 재 오면:

1. `scripts/build_complex_proxy.py --ceiling-height-m <보정값>`으로 Proxy Mesh 재생성
2. `make_markers.py` 재실행 → 좌표 15개 재생성
3. `run-sionna` 재실행
4. 계획서·README·배치도 갱신

실측 길이를 못 얻으면 **좌표를 "측량값"이 아니라 "도면 기반 계획값"으로 보고**한다.
2.7 m 가정으로 만든 옛 수치(현재 값의 9/10배)와 절대 섞지 않는다.

## 7. 참고: raw CSV 검증과 `ap_channel`

`tools/rf_experiment/contracts.py:432`의 `_validate_raw_row()`는
`ap_channel`을 유한한 숫자로 요구한다. 그런데 임베디드 패킷 구조체
(`espnow_packet.h`)에는 채널 필드가 없어 현재는 항상 빈 값이다.
→ `validate-csv --kind raw`가 **모든 행에서 실패**한다.

**해결 방법 확정(2026-08-21):** `embedded.md` 3번의 브릿지 `--ap-channel` 수정이 payload 에 채널을 채운다.
**그래픽스 쪽 변경은 필요 없다.** 임베디드 수정이 측정 전에 못 들어가는 경우에만
`ap_channel` 을 선택 항목으로 완화한다.
