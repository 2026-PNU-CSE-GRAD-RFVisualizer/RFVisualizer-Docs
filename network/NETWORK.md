# Network / Backend 파트

- 코드 저장소: [Network-Backend-Article](https://github.com/2026-PNU-CSE-GRAD-RFVisualizer/Network-Backend-Article)
- 담당 범위: MQTT 수집, 데이터 검증·저장, 실험 관리(Run/TestSegment), 장치 Offset(사전·사후),
  CSV Export, 실시간 WebSocket 인터페이스

## 1. 실행 모드

| 구분 | 논문·측정 실험 경로 | 졸업작품 실시간 경로 |
|---|---|---|
| 현재 기본 상태 | 활성 | 비활성 |
| 설정 | `ENABLE_REALTIME=false` | `ENABLE_REALTIME=true` |
| 측정 방식 | 위치별 정지 측정(Run/TestSegment) | 이동 단말 실시간 추적 |
| 기준 저장소 | SQLite + JSONL | PostgreSQL 선택 |
| 파트 간 전달 | CSV/JSON Export | WebSocket |
| 시간 동기화 | 측정시각 기준 Window+유예 | 200 ms Window |

## 2. 전체 구조

```text
ESP32 / Serial-MQTT Bridge → MQTT Broker → MQTT Bridge → Payload Parser
   → Node Registry / Metrics
   ├─ Experiment Store (JSONL Raw · SQLite · Device Offset · CSV/JSON Export)
   └─ Realtime Window (측정시각 Bucket · Missing Node · WebSocket /frames)
```

## 3. MQTT 수집

구독 Topic: `rssi/#`, `gateway/#`, `status/+/lwt`

개별 RSSI 예시:

```json
{"node_id":"node-01","timestamp":1785720000000,"rssi":-61,"rssi_raw":-62,
 "seq":15234,"ap_bssid":"AA:BB:CC:DD:EE:FF","status":0}
```

## 4. Payload Parser (`backend/parsing.py`)

Broker 없이 단위 테스트 가능. 호환 필드:

| 의미 | 허용 필드 |
|---|---|
| Filtered RSSI | `rssi_filtered_dbm`, `rssi_filtered`, `rssi` |
| Raw RSSI | `rssi_raw_dbm`, `rssi_raw` |
| Channel | `ap_channel`, `channel` |
| Error | `error_flags`, `status` |

`rssi`=Filtered dBm, `rssi_raw`=Raw dBm. 독립 `ParseConfig()`와 실제 MQTT 경로의
유효 범위는 모두 `-110 ≤ RSSI ≤ -10`으로 일치한다.
구조 손상 메시지만 버리고, 값이 비정상이면 `valid=false, invalid_reason`으로 보존(분석에서만 제외).
Node/Server 시각 차가 허용 범위를 크게 벗어나면 Server 수신 시각으로 교체.

## 5. Node 상태 관리

마지막 수신 시각·Seq·Packet Loss·중복·Online/Offline·Heartbeat·수집지연 관리.
Endpoint: `GET /nodes/status` `/metrics` `/monitor`.

## 6. 실험 모델 (Run / TestSegment)

기존 단일 세션 모델을 **두 상태로 분리**한다.

```text
OffsetRun  (phase: pre | post)         # 본 실험과 분리
ExperimentRun (direction, pass_index)  # running → completed | interrupted | discarded (자동 종료 없음)
  └─ TestSegment (order_index, attempt_index, [rec_start, rec_end))
                 stabilizing → recording → completed | interrupted | discarded
```

- 한 번에 활성 Run 1개, 활성 TestSegment 1개. 상태 위반 요청은 **HTTP 409**.
- **C1~C4(고정)**: Run 시작~종료까지 끊기지 않고 저장. **T(이동)**: 각 TestSegment 기록 구간에만 저장.
- 샘플 소속은 in-memory 포인터가 아니라 **저장된 시간 범위**로 판정:
  `recording_started_at_ms ≤ server_ts_ms < recording_ended_at_ms`.
  MQTT 지연이 있어도 올바른 Segment 로 저장된다.
- 재측정: 이전 Segment `superseded=1`, 새 Segment `attempt_index+1`.
  다른 위치·회차·C1~C4 연속 원본은 삭제하지 않는다.
- 정방향(T1→T10)·역방향(T10→T1)은 서로 다른 `run_id`.

Point Role: `offset`(편차 측정) · `calibration`(RF 보정) · `test`(평가 전용).

## 7. Device Offset (사전·사후)

같은 위치에 5대를 모아 측정한 OffsetRun 으로 장치 편차를 계산한다.

- **사전(pre)**: 본 실험 보정에 사용. `corrected_rssi = median_filtered + device_offset_db`.
- **사후(post)**: 실험 전후 편차 변화(drift) 확인용. **재보정하지 않는다.**
- 사전·사후는 서로 다른 `offset_run_id` 로 저장하여 사후가 사전값을 덮어쓰지 않는다.
  (`device_offset` PK = `(offset_run_id, node_id)`)
- `experiment_run.pre_offset_run_id` = 적용한 사전, `post_offset_run_id` = 사후(없으면 NULL).
- QC/`device_offsets.json`에 node별 `pre_device_offset_db`, `post_device_offset_db`,
  `device_offset_drift_db = post - pre`. 임의 합격 임계값은 만들지 않으며, 누락 시 경고.

## 8. 데이터 저장 (SQLite, user_version 2)

- 기준 저장소 `data/experiment.db`. 원본 백업 `data/ingest_raw.jsonl`. Postgres 는 실시간 경로 선택.
- 신규 테이블: `experiment_run`, `test_segment`, `offset_run`.
- `measurement.run_id`, `measurement.segment_id` 열.
  - C1~C4 이동 구간: `run_id` 있음 / `segment_id=NULL`
  - Test 동시간(C1~C4·T): 둘 다 있음
  - Offset: `run_id=offset_run_id`, `point_role='offset'`
  - **Legacy(구 DB)**: 둘 다 NULL
- **마이그레이션**: v0→v1(measurement 열), v1→v2(offset_run·device_offset 재구성·experiment_run pre/post).
  구 device_offset 은 `offset_run_id='legacy:<experiment_id>'` 로 보존. DB 삭제 불필요.

## 9. Experiment API

```text
상태        GET /health · /nodes/status · /metrics · /monitor
Experiment  POST /experiment/start · /end · /assign · /tx · /points/import · /export
Offset      POST /offset-run/start {phase} · /stop · /experiment/offsets/compute {phase|offset_run_id}
            POST /run/attach-post-offset {offset_run_id}
Run         POST /run/start {direction, pass_index} · /run/end · GET /run/current
TestSegment POST /test-segment/prepare {point_id, order_index, stabilization_seconds, recording_seconds}
            POST /test-segment/stop · /discard · GET /test-segment/current
다운로드     GET /experiment/download/{which}
```

**구 `/session/start` `/stop` `/current` 는 제거되어 HTTP 410 Gone 을 반환한다.**
단일 세션 경로로는 새 실험 데이터를 만들 수 없다.

## 10. Export (`backend/export.py`)

```text
experiments/<experiment_id>/
├── raw/measurements_raw.csv                # + run_id, segment_id, direction, pass_index
├── processed/
│   ├── measurements_summary.csv
│   ├── test_points.csv                     # TestSegment 대표값(평가 전용)
│   ├── calibration_by_test_window.csv      # 각 Test 와 동일 시간대 C1~C4 (IDW 입력)
│   └── calibration_points.csv              # Run 전체 진단용(동시간 아님)
├── config/
│   ├── points.csv · tx_rx.json
│   ├── device_offsets.json                 # pre / post / drift
│   ├── runs.json · test_segments.json
├── qc_report.json
└── README.md
```

- **동시간 매칭**: MQTT 저장 단계에서 기록창의 C1~C4 에 그 Test 의 `segment_id` 가 붙는다.
  `test_points.csv.segment_id ↔ calibration_by_test_window.csv.segment_id` 로 연결.
- `corrected_rssi = median_filtered + device_offset_db`(그 Run 의 **사전** offset).
- 정방향 T1·역방향 T1·재측정(attempt_index)은 별도 행 — 합치지 않는다.
- `calibration_points.csv`(전체 평균)를 모든 Test 에 공통 적용하지 않는다.

## 11. Quality Check

Run 별 검사: Offset(사전) 계산 여부, C1~C4 4대·이동 T 1대, Run별 Test 위치 수(기본 10),
정/역 순서, TestSegment 시간 겹침, Run 시간 포함, 각 Segment 의 T·C1~C4 존재, 동시간 범위 일치,
좌표·BSSID·샘플 수, 사전/사후 offset drift. **Run 이 30분을 넘었다는 이유로 실패시키지 않는다.**
기대 Test/Calibration 수는 config(`expected_test_points`, `expected_calibration_nodes`)로 분리.

## 12. 실시간 경로 (`ENABLE_REALTIME=true`)

`backend/realtime/window.py`. 버킷 기준을 **측정 시각(node timestamp)** 으로 하고,
늦은 도착 **유예(`window_grace_ms`)** 구간을 둔다(전문가 자문 반영: 수집지연 p95 > window 대비).
`WS /frames` 로 `rssi_frame` push, `GET /position/latest` 는 인터페이스만.

## 13. Handheld Control

Handheld 경로는 RSSI 실험 모드와 독립적으로 켤 수 있으며 기본값은 비활성이다.

```text
Handheld RFHC v1 ─UDP 9200─▶ Parser/Session Tracker
                                  ├─ 500 ms stale 판정
                                  ├─ 텔레포트·Height-cycle 버튼 레벨 상태 그대로 전달
                                  └─ WS /handheld/control ─▶ Graphics
```

**2026-09-01 기획 변경 반영 완료(GitHub `main` `a9789d9` 확인, `pytest tests/` 57 passed
1 skipped 재현 확인).** RFHC bit1·bit2를 텔레포트·Height-cycle 버튼 레벨 상태로 재정의하고
`handheld_state`에 `teleport_button_held`·`height_cycle_button_held`로 그대로 실어 보낸다.
`event_seq` 기반 Event 중복 제거와 `position_update` Message는 코드에서 완전히 제거했다
(부재를 확인하는 회귀 테스트 포함). `PositionProvider`/`ConfiguredPositionProvider`와
REST API는 지우지 않고 그대로 남겨 관리용으로 쓴다.

구현된 항목:

- RFHC v1 52-byte Parser, CRC와 Quaternion norm 검증, Reserved bit(4~7) 거부
- Device/Session/Sample Sequence 통계(중복·누락·out-of-order)
- UDP `9200` Listener와 500 ms stale 전환(재전환 시 마지막 상태를 `stale=true`로 재방송)
- `PositionProvider`와 설정 좌표 기반 `ConfiguredPositionProvider` — 버튼과 분리된 관리용
- `WS /handheld/control` — 접속 즉시 최신 상태 1개 전송, Graphics는 Message를 보내지 않음
- `GET /handheld/status`, `GET /handheld/positions`, `POST /handheld/position/active`
- 공유 CRC Test Vector(`0x0AE927E5`) 일치 확인, `device_id`/`source_ip` 필터 테스트

현재 설정 좌표는 `pnu_3f_corridor_metric_v1`의 `demo-1=(21.40, 17.80, 1.60)`이다.
이는 1차 통합 시연용 고정 좌표이며 실제 위치 추정 알고리즘이 아니다.

현재 제한:

- `handheld_enabled=false`가 기본값
- 실제 ESP32-S3 UDP 송신 미연결(Embedded 쪽 버튼 GPIO·펌웨어 통합 대기)
- Graphics의 `/handheld/control` Consumer는 새 규격으로 구현·C++ Test 통과했으나 실제
  BNO085 축·실기기 버튼·실행 화면 미검증
- Camera 축·텔레포트·Height-cycle 실기기 종단 시험 미완료

## 14. 설정 (`config.py` / `.env`)

```text
test_stabilization_seconds = 20      test_recording_seconds = 120
expected_test_points = 10            expected_calibration_nodes = 4
window_size_ms = 200                 window_grace_ms = 300
ENABLE_REALTIME = false
handheld_enabled = false              handheld_udp_port = 9200
scene_frame_id = pnu_3f_corridor_metric_v1
```

전체 Run 종료 시간은 설정하지 않는다(사용자가 종료).

## 15. 테스트 / 리허설

```powershell
py tests\test_migration.py        # 스키마 마이그레이션(기존 DB 보존)
py tests\test_run_flow.py         # 상태 규칙·시간 매칭
py tests\test_pipeline_run.py     # 종단 저장(C1~C4 연속·T 기록창)
py tests\test_export_run.py       # Export/QC·동시간 매칭·폐기 제외
py tests\test_offset_prepost.py   # 사전/사후 offset 분리·drift
py rehearsal.py --reverse         # 사전·사후 offset + 정+역 in-process 리허설(브로커 불필요)
```

실물 MQTT 자체 테스트: 브로커 + 백엔드 + `load_test.py --nodes 5` + 브라우저 UI.

저장소 최신 기록은 전체 65개 통과이며, 이 중 Handheld 관련 단위·통합 테스트가 16개다.
이번 공통 문서 갱신에서는 Network 테스트를 다시 실행하지 않았다.

## 16. 재시작 처리

- 브라우저 새로고침: Backend 의 Run/Segment 를 `/run/current` 로 복원(타이머 재시작 안 함).
- Backend 재시작: 열린 Run/Segment 를 `interrupted` 로 표시(정상 완료로 숨기지 않음). SQLite·JSONL 보존.
- 측정 중 `uvicorn --reload` 금지.

## 17. 현재 구현 상태

- **로직 검증 완료**: 마이그레이션·상태관리·MQTT 저장 분기·시간매칭·사전사후 offset·Export/QC.
- **Handheld Backend 구현 완료(2026-09-01, 텔레포트·Height-cycle 버튼 규격)**: RFHC Parser·UDP Listener·버튼 레벨 상태 그대로 전달·PositionProvider(관리용, 버튼과 분리)·Graphics WebSocket. 기본 비활성이고 실기기 종단은 미검증.
- **실물 확인 완료**: MQTT 수신(브로커+load_test+백엔드), 새 UI 로드.
- **미검증**: 실센서 5대 정방향 전체 리허설, 브라우저 새로고침/MQTT 재연결/Backend 중단의 실동작.
- **별도 구현·검증 완료**: RFJF 22-byte Frame 기반 `image_relay`와 Host Test 8개.
- **미구현·미통합**: 실제 Position 추정, Handheld 실기기 UDP 송신, 전체 Viewer 종단 통합.
- **Graphics 영상 경로 갱신(2026-08-27)**: RFJF Producer C++ 소스는 Git에 반영됐고,
  `flags=1`(RGB332)·`flags=2`(팔레트256, 현재 기본) 모두 Graphics→Relay→ESP32-S3 LCD
  실기기 종단 출력을 확인했다. 300초 지속 성능은 아직 계측하지 않았다.

## 18. 공통 계약

파트 간 계약(Export Schema·Run/Segment 모델·사전사후 Offset·시간 범위 규칙)은
`RFVisualizer-Docs/INTERFACE.md` 를 기준으로 한다. 변경은 §13 절차(그래픽스 합의)를 따른다.
코드 저장소에는 `README.md`, `TESTING.md`, `RUN_EXPERIMENT.md` 를 유지한다.
