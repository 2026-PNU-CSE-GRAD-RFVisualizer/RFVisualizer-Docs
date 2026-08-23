# 네트워크·백엔드 파트 작업 목록 — corridor3f_20260820

- 대상 저장소: [Network-Backend-Article](https://github.com/2026-PNU-CSE-GRAD-RFVisualizer/Network-Backend-Article)
- 확인 기준 커밋: `c7a8ce0` (2026-08-21 19:00)
- 작성일: 2026-08-21 (수정 확인 후 갱신)

## 사람이 볼 요약

**3개 중 2개 완료. 남은 건 2줄인데, 그게 제일 중요한 것입니다.**

| # | 항목 | 상태 |
|---|---|---|
| 1 | **`rssi_min` -100 → -110** | 🔴 **안 됨 — 이것만 하면 됨** |
| 2 | QC 정/역 순서 검사 | ✅ 완료 |
| 3 | 좌표 등록 절차 + `points.csv` | ✅ 완료 (15개 계획서와 일치) |
| 4 | 실센서 5대 리허설 | ⬜ 장비 필요 |

확인해 본 것: `pytest tests` 43 passed, `rehearsal.py --reverse` QC 통과.

### 지금 상태로 측정하면 어떻게 되나

임베디드는 -110까지 내려서 신호가 백엔드까지 **도달은 합니다.** 그런데 백엔드가 여기서 버립니다.

```
현재 settings.rssi_min=-100 → valid=False, reason=rssi_out_of_range(-105.0)
```

cal-02(-106.7), cal-03(-105.3), test-05(-101.1), test-06(-106.7)이 전부 무효 처리되고,
QC의 "Segment마다 C1~C4 4대" 조건 때문에 **정·역방향 20개 Segment가 전부 실패**합니다.

### 참고 — 좌표 join 코드는 안 넣어도 됐습니다 (제 잘못된 보고 탓)

`9e15075`에 들어간 `export.py`의 좌표 덮어쓰기는 **동작에 영향이 없는 no-op**입니다.
`store.py:477`의 SQL이 이미 `point` 테이블을 join하고 있습니다.
**해는 없으니 그냥 두셔도 되고, 지우셔도 됩니다.** 자세한 근거는 아래 3번에 있습니다.

---

# 상세 (에이전트용)

## 1. `rssi_min` -100 → -110 — 남은 유일한 코드 작업

### 문제
Sionna 예측: cal-02 -106.7, cal-03 -105.3, test-05 -101.1, test-06 -106.7 dBm.

`backend/parsing.py:67`에서 범위를 벗어나면 `valid=false`가 되고,
`backend/export.py:75`의 `_valid_filtered()`가 이를 제외한다.
유효 표본이 하나도 남지 않으면 `_repr()`이 `None`을 반환해 **그 지점 행이 아예 사라진다.**

연쇄 피해: `quality_check()`(`export.py:266~277`)는 각 완료 Segment에 C1~C4가
모두 있을 것을 요구한다 → cal-02/cal-03이 죽으면 20개 Segment 전부 `problems`.

### 수정
```
backend/config.py:36     rssi_min: int = -100      →  -110
backend/parsing.py:12    rssi_min: float = -100.0  →  -110.0
```

`rssi_max`(-10)는 그대로 둔다. 범위 밖 값은 버리지 않고 `valid=false`로 보존한다
(원본은 남고 분석에서만 제외되는 기존 정책 유지).

`.env`에 `rssi_min=-110`을 넣는 방법도 있지만, `.env` 없이 실행하면 조용히 -100으로
돌아가므로 **기본값 자체를 바꾸는 쪽을 권한다.** `parsing.py`의 값은 단위 테스트 기본값이라
`mqtt_bridge.py:227`이 settings로 덮어쓰지만, 두 값이 다르면 테스트와 실제가 어긋난다.

### 체인 확인 (네 곳이 모두 -110이어야 한다)
| 위치 | 상태 |
|---|---|
| 노드 펌웨어 `RSSI_VALID_MIN_DBM` | ✅ (Embedded `3bbd984`) |
| 게이트웨이 `GATEWAY_RSSI_VALID_MIN_DBM` | ✅ |
| 브릿지 `RSSI_VALID_MIN_DBM` | ✅ |
| **Backend `rssi_min`** | 🔴 **남음** |

### 검증
```bash
python -m pytest tests -q
```

그리고 -105 dBm 샘플이 살아남는지 직접 확인한다.

```python
from backend.parsing import parse_measurement, ParseConfig
from backend.config import settings
out = parse_measurement(
    {"node_id": "node-03", "timestamp": 1787307387859, "rssi": -105, "seq": 1,
     "ap_channel": 6, "status": 0},
    1787307387859,
    ParseConfig(rssi_min=settings.rssi_min, rssi_max=settings.rssi_max),
)
assert out["valid"] is True, out["invalid_reason"]
```

## 2. QC 정/역 순서 검사 — 완료 확인

`export.py:246`이 `int(p[1:])`를 쓰던 것을 끝자리 숫자 파싱으로 고쳤다.

```python
nums = [int(m.group()) for p in pts if (m := re.search(r"\d+$", p))]
```

`test-01` 형식에서 검사가 항상 통과하던 문제가 해결됐다. `T1` 형식도 그대로 동작한다.

## 3. 좌표 — 완료. 다만 추가된 join 코드는 불필요하다

### 확인된 동작
`store.py:477`
```sql
LEFT JOIN point p ON p.experiment_id = m.experiment_id AND p.point_id = m.point_id
```
그리고 SQLite `measurement` 테이블에는 **좌표 열 자체가 없다**(`db/schema_experiment.sql:80`).
센서 payload의 `pos_x/y/z`는 저장되지 않는다(실시간 경로 전용).

실측 확인: payload가 `(0,0,0)`이어도 `measurements_for_export()` 결과는
등록 좌표 `12.57, 17.83, 0.45`가 나온다. 따라서 `9e15075`가 추가한

```python
coords = {p["point_id"]: p for p in points if p["pos_x"] is not None}
for r in rows: ...
```

는 같은 값을 다시 덮어쓰는 no-op다. QC의 `registered` 검사도 `x is None` 검사와 결과가 같다.
**둘 다 무해하므로 유지·삭제 어느 쪽이든 상관없다.** 다만 "왜 있는지 모를 코드"로 남기지 말고,
지울 거면 지우고 남길 거면 주석을 "이중 안전장치"로 바꿔 두는 편이 낫다.

### 진짜 중요한 것 — 등록을 빠뜨리면 좌표가 전부 빈다
`POST /experiment/points/import`로 등록한 좌표가 **유일한 출처**다.
`points.csv`(15개, 계획서 §5와 일치)가 저장소에 들어왔고 `RUN_EXPERIMENT.md`에 절차도 있다.

현장에서 C2/C3을 예비 좌표로 옮기면 **이 CSV를 고쳐 다시 등록한다.**
`Embedded/node_positions.json`은 건드리지 않는다(좌표 출처를 하나로 유지).

## 4. `ap_channel` — 임베디드 쪽 해결됨, 확인만

브릿지가 `--ap-channel`(기본 6)로 payload에 `ap_channel`을 채우도록 수정됐다(Embedded `3bbd984`).
현재 리허설에 남아 있는 경고는 가상 센서가 채널을 안 보내서이며, 실장비에서는 사라져야 한다.

```
경고: 모든 측정에 AP 채널이 비어 있습니다(센서 payload 확인 필요).
```

`POST /experiment/tx`에는 현장 AP의 실제 채널을 함께 등록한다(완료 조건 §10-3).
그래픽스의 `validate-csv --kind raw`도 `ap_channel`을 필수로 요구하므로 실장비 리허설에서 확인한다.

## 5. 실센서 5대 리허설 — 남은 항목

`NETWORK.md` §16 기준 미검증: 실센서 5대 정방향 전체 리허설,
브라우저 새로고침 / MQTT 재연결 / Backend 중단 실동작.

in-process 리허설은 통과했다.
```
QC: 통과 | counts={'raw_rows': 1300, 'runs': 2, 'completed_segments': 20,
                    'test_points': 20, 'calibration_windows': 80}
```

실장비 절차:

1. **`rssi_min` 수정 먼저 반영한다.** 안 하면 리허설로 약전계 문제를 못 잡는다
2. pre-offset OffsetRun (5대 같은 위치) → `POST /experiment/offsets/compute {phase: "pre"}`
3. `POST /experiment/points/import` (points.csv 15개) + `POST /experiment/tx` (좌표 + 채널)
4. `POST /run/start {direction: "forward", pass_index: 1}`
5. TestSegment 2~3개만 짧게 (`stabilization 5s / recording 10s`)
6. `POST /experiment/export` 후 확인
   - `processed/test_points.csv`의 x,y,z가 위치별로 다른가
   - `raw/measurements_raw.csv`에 `ap_channel`이 채워졌는가
   - **-100보다 낮은 값이 `valid=1`로 남는가**
   - `qc_report.json`의 `problems`가 비었는가
7. 측정 중 `uvicorn --reload` 금지(`NETWORK.md` §15)

### 확인해둔 값 (변경 불필요)
- 샘플 기대치는 `test_recording_seconds`(=120)를 그대로 쓴다(`main.py:409`).
  노드 publish 주기 1초 → 120초 기록 = 약 120 샘플, QC 실패선은 60%인 72개.
- `expected_test_points=10`, `expected_calibration_nodes=4`는 계획서와 일치.
