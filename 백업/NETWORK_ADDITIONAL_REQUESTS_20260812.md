# Network Backend 추가 수정 및 완료 조건

## 1. 사전·사후 Device Offset을 모두 보존한다

### 측정 요구사항

- 본 실험 전에 센서 5대를 같은 위치에서 5분간 측정한다.
- 본 실험 후에도 센서 5대를 다시 같은 위치에서 5분간 측정한다.
- 사전 측정값은 본 실험 RSSI 보정에 사용한다.
- 사후 측정값은 장비 편차가 실험 전후에 얼마나 변했는지 확인하는 QC 용도로만 사용한다.
- 사후 측정값으로 본 실험 데이터를 다시 보정하지 않는다.
- 사전·사후 원본과 계산 결과를 모두 남긴다.

### 저장 구조

기존 계획에는 `experiment_run.offset_run_id` 참조가 있지만, 대응하는 Offset Run 저장 구조가 빠져 있다. 최소한 다음 정보를 별도로 저장한다.

```text
offset_run_id
experiment_id
phase                 # pre | post
status                # running | completed | interrupted | discarded
started_at_ms
ended_at_ms
note
```

`device_offset`도 사전·사후 결과를 동시에 보존할 수 있어야 한다.

```text
offset_run_id
node_id
offset_median_dbm
device_offset_db
sample_count
std_db
calibrated_at_ms
```

권장 식별 기준:

```text
PRIMARY KEY (offset_run_id, node_id)
```

기존 `(experiment_id, node_id)` 기준만 유지하면 사후 계산이 사전 보정값을 덮어쓸 수 있으므로 그대로 사용하면 안 된다.

본 실험 Run에는 실제 적용한 사전 Offset의 출처를 남긴다.

```text
experiment_run.pre_offset_run_id
experiment_run.post_offset_run_id   # 사후 측정이 없으면 NULL
```

### Offset QC

Node별로 다음 값을 Export 또는 `qc_report.json`에 기록한다.

```text
pre_device_offset_db
post_device_offset_db
device_offset_drift_db = post_device_offset_db - pre_device_offset_db
```

- 임의의 합격 임계값을 새로 만들지 않는다.
- 사전 또는 사후 측정이 없으면 누락 사실을 명확히 경고한다.
- 반복 안정성이 낮은 경우에도 결과를 숨기거나 자동으로 정상 처리하지 않는다.

---

## 2. 실물 센서 5대 End-to-End 리허설을 완료한다

단위 테스트와 가상 센서 압축 리허설 통과만으로 작업 완료로 처리하지 않는다.

### 검증 순서

1. 단위 테스트와 Migration 테스트를 실행한다.
2. 가상 센서 5대로 압축 리허설을 실행한다.
3. 실물 센서 5대로 정방향 전체 Run을 최소 1회 실행한다.
4. 역방향은 최종 실험 일정에 맞춰 선택적으로 실행하되, 코드 경로는 가상 리허설로 반드시 검증한다.
5. 장애 복구 시험은 최종 측정이 아닌 리허설에서 별도로 수행한다.

### 실물 리허설 확인 항목

- C1~C4가 Test 이동·안정화 구간에도 계속 저장된다.
- T 데이터는 각 TestSegment의 실제 기록 구간에만 포함된다.
- 각 TestSegment와 C1~C4에 동일한 `segment_id`가 저장된다.
- 브라우저 새로고침 후 Run과 타이머가 복원된다.
- MQTT 재연결 횟수와 데이터 공백이 기록된다.
- Backend 중단 시 열린 Run과 Segment가 `completed`가 아니라 `interrupted`로 남는다.
- 정방향 T1과 역방향 T1 또는 재측정 T1이 서로 덮어써지지 않는다.

### 완료 증거

다음 결과를 한 묶음으로 제출한다.

```text
실행한 run_id와 segment_id 목록
SQLite 백업
JSONL 원본
전체 Export 디렉터리
qc_report.json
Run 진행 화면 캡처
C1~C4 Node별 누적 Sample 수
Node별 최대 수신 공백
MQTT 연결 해제·재연결 기록
실행한 테스트 명령과 통과 결과
```

실물 리허설을 실행하지 못했다면 `미검증`으로 보고하고, 가상 테스트 결과를 실물 검증 완료로 표현하지 않는다.

---

## 3. 기존 Session API와 공통 데이터 계약을 정리한다

### Legacy API

다음 기존 API가 새 Run 구조와 동시에 정상 동작하도록 남아 있으면 안 된다.

```text
POST /session/start
POST /session/stop
GET  /session/current
```

필수 조치:

1. `rg`로 UI, 리허설, 테스트, 문서의 모든 호출자를 찾는다.
2. 모든 내부 호출자를 새 Run·TestSegment API로 변경한다.
3. 기존 API는 제거하거나 명시적인 Legacy 오류를 반환하도록 한다.
4. 기존 API가 단일 `ActiveSession` 경로로 새 Measurement를 생성하지 못하게 한다.
5. 처리 방침과 마이그레이션 영향을 README에 기록한다.

권장 방식은 내부 호출자 변경이 끝난 뒤 기존 API에 명확한 사용 중단 오류를 반환하는 것이다. 요청을 성공시킨 뒤 아무 동작도 하지 않는 방식은 사용하지 않는다.

### 공통 문서 갱신

Export Schema와 Experiment 모델은 Graphics 파트에도 영향을 주므로 다음 중앙 문서를 함께 갱신하거나 변경안을 제출한다.

```text
RFVisualizer-Docs/INTERFACE.md
RFVisualizer-Docs/network/NETWORK.md
```

문서에 최소한 다음 내용을 반영한다.

- `ExperimentRun`과 `TestSegment` 관계
- 사전·사후 `OffsetRun` 의미
- `[recording_started_at_ms, recording_ended_at_ms)` 시간 범위
- 구간 매칭은 `server_ts_ms` 기준이라는 점
- `run_id`, `segment_id`, `direction`, `pass_index`, `attempt_index`
- `test_points.csv`와 `calibration_by_test_window.csv`의 연결 기준
- `calibration_points.csv`는 전체 Run 진단용이라는 점
- Legacy Measurement와 새 Measurement의 구분 방법

Graphics 파트가 다음 연결을 실제로 수행할 수 있는지 샘플 Export로 확인한다.

```text
test_points.csv.segment_id
        ↕
calibration_by_test_window.csv.segment_id
```

---

## 최종 완료 체크리스트

- [ ] 사전·사후 Offset Run이 서로 다른 ID로 저장된다.
- [ ] 사후 Offset 계산이 사전 적용값을 덮어쓰지 않는다.
- [ ] Node별 Offset Drift가 QC에 기록된다.
- [ ] 기존 DB Migration 전후 데이터가 유지된다.
- [ ] 기존 `/session/*` 경로로 새 실험 데이터를 만들 수 없다.
- [ ] 가상 센서 5대 전체 리허설이 통과한다.
- [ ] 실물 센서 5대 정방향 전체 리허설 결과가 남아 있다.
- [ ] 브라우저 새로고침·MQTT 재연결·Backend 중단 처리가 검증됐다.
- [ ] Segment별 Test와 동시간 Calibration Export가 생성된다.
- [ ] Graphics 파트가 `segment_id`로 두 파일을 연결할 수 있다.
- [ ] README, TESTING 및 공통 계약 문서가 현재 동작과 일치한다.

## 제출 시 보고 형식

```text
1. 구현 완료 항목
2. 실물 검증 완료 항목
3. 아직 미검증인 항목
4. Migration 또는 Legacy 호환 위험
5. 생성한 Export와 QC 위치
6. 실행한 테스트 명령과 결과
```

구현 완료와 실물 검증 완료를 같은 상태로 표시하지 않는다.
