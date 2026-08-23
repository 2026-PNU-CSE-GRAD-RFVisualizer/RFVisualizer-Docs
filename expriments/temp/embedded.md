# 임베디드 파트 작업 목록 — corridor3f_20260820

- 대상 저장소: [Embedded](https://github.com/2026-PNU-CSE-GRAD-RFVisualizer/Embedded)
- 작성일: 2026-08-21 (2026-08-21 갱신: 좌표 항목 정정)
- 전제: 대상 AP(`바부바부쟝`)는 인터넷에 연결되어 있다.

## 사람이 볼 요약

**코드 4줄 + 브릿지 옵션 1개입니다. 고치고 5대 다시 플래시하면 코드 작업은 끝입니다.**

1. **-100 dBm 하한을 -110으로** (노드 펌웨어 + 게이트웨이 펌웨어 + 브릿지 2곳).
   지금은 약한 신호를 소프트웨어가 먼저 버려서 실험 지점 4곳이 **데이터 0행**이 됩니다.
2. **채널을 payload 에 채웁니다** (`--ap-channel 6`).
   ESP-NOW 패킷에 채널 필드가 없어 백엔드 QC 경고 + 그래픽스 raw CSV 검증 실패를 냅니다.

현장 규칙: **노드는 AP 근처에서 켜고, 시간 동기가 끝난 걸 확인한 뒤 자리로 옮깁니다.**

### 정정 — `node_positions.json` 은 손댈 필요가 없습니다

Backend 의 논문·측정 경로는 **payload 좌표를 저장하지 않습니다**
(SQLite `measurement` 테이블에 좌표 열이 없음). 좌표는 Backend 에 등록한 값만 씁니다.
따라서 `node-02` 가 `(0, 0, 0)` 이어도 측정 결과에는 영향이 없습니다.
이 파일의 좌표는 실시간 경로(`ENABLE_REALTIME=true`) 전용입니다. README 에만 그렇게 적어 뒀습니다.

| # | 할 일 | 크기 |
|---|---|---|
| 1 | 펌웨어 RSSI 하한 -110 (노드·게이트웨이) | 2줄 + **재플래시 5대** |
| 2 | 브릿지 RSSI 하한 -110 (2곳) | 2줄 |
| 3 | 브릿지 `--ap-channel` 로 채널 채우기 | 옵션 1개 |
| 4 | `node_positions.json` 설명 (README) | 문서 |
| 5 | 현장 사전 점검 3종 | 현장 |

수정 후 확인:

```bash
python -m pytest test_stm32_serial_mqtt_bridge.py -q
```

> 아래 1~4번은 사본 저장소에 실제로 적용해 `pytest`(9 passed, 신규 4개 포함)로 확인한 내용이다.

---

# 상세 (에이전트용)

## 1. RSSI 유효 하한 -100 → -110 (펌웨어)

### 문제
Sionna 예측상 cal-02 -106.7, cal-03 -105.3, test-05 -101.1, test-06 -106.7 dBm.
현재 펌웨어는 -100 미만 raw 샘플을 필터에 넣지 않는다 → 필터가 비고
`RSSI_ERR_FILTER_EMPTY` 가 서고 → Backend 가 `error_flags != 0` 을 `valid=false` 로 만들어
모든 집계에서 제외한다. **"약하게 잡힘"이 아니라 "데이터 없음"이 된다.**

Backend QC 는 각 TestSegment 에 C1~C4 4대가 모두 있을 것을 요구하므로,
cal-02/cal-03 이 죽으면 **정·역방향 20개 Segment 가 전부 실패**한다.

### 수정
| 파일 | 상수 | 값 |
|---|---|---|
| `rssi_esp32_to_stm32/esp32_node/main/node_config.h` | `RSSI_VALID_MIN_DBM` | `(-110)` |
| `rssi_esp32_to_stm32/esp32_gateway/main/gateway_config.h` | `GATEWAY_RSSI_VALID_MIN_DBM` | `(-110)` |

`*_VALID_MAX_DBM (-10)` 은 그대로. 사용처는 상수만 바꾸면 따라온다
(`rssi_filter.c:12`, `gateway_rssi.c:24`).

자료형은 이미 안전하다 — `int8_t rssi_raw_dbm` 은 -110, `int16_t rssi_filtered_x10` 은 -1100 표현 가능.

### 재빌드 범위
`NODE_ID` 가 컴파일 상수(`node_config.h:6`)라 **노드 4대를 각각 따로 빌드/플래시**해야 한다
(`NODE_ID` 1~4). 게이트웨이 1대까지 총 5대. `BUILD_FLASH_COMMANDS.md` 참고.

### 검증
게이트웨이 UART 라인에 -100 보다 낮은 `rssi_filtered_x10`(예: -1053)이 실려 나오고
`error_flags` 가 0 인지 확인한다.

## 2. 브릿지 RSSI 하한

### 문제
`stm32_serial_mqtt_bridge.py` 가 범위 밖 값을 **`return None` 으로 조용히 버렸다.**
로그도 남지 않아 현장에서 "왜 데이터가 없지?" 를 진단할 수 없다.

### 수정
`normalize_reading()` 안의 하드코딩 `-100` 두 곳(개별 publish 경로 / gateway batch 경로)을
상수로 바꾸고 -110 으로 내린다.

```python
# 펌웨어와 같은 유효 범위. 범위 밖 값을 여기서 버리면 로그도 남지 않으므로
# 하한은 Backend(rssi_min)와 반드시 함께 움직여야 한다.
RSSI_MIN_DBM = -110
RSSI_MAX_DBM = -10
```

### 주의 — 네 곳이 같이 움직여야 한다
펌웨어 노드, 펌웨어 게이트웨이, 브릿지, Backend(`rssi_min`).
**하나라도 -100 이면 이 수정은 무의미하다.** Backend 쪽은 `network.md` 1번이다.

## 3. `ap_channel` 채우기

### 문제
`espnow_packet.h` 패킷 구조체에 `ap_bssid` 는 있으나 **채널 필드가 없다.**
그래서 Backend `measurement.ap_channel` 이 항상 비고 두 가지가 걸린다.

- 그래픽스 `validate-csv --kind raw` 가 `ap_channel` 을 유한한 숫자로 요구
  (`tools/rf_experiment/contracts.py:432`) → **raw CSV 전 행 검증 실패**
- Backend QC 경고: `모든 측정에 AP 채널이 비어 있습니다`
- 실험 계획서 §10-3 "채널 누락 없음" 완료 조건

### 수정 (펌웨어 대신 브릿지에서)
채널은 `ESPNOW_WIFI_CHANNEL`(=6) 로 고정이고 `#error` 가드로 AP 채널과 같음이 보장된다.
따라서 패킷 구조를 바꾸지 않고 브릿지에서 넣는다.

- `--ap-channel` 인자 추가 (기본 6, `DEFAULT_AP_CHANNEL`)
- `attach_position(reading, positions, ap_channel=None)` 에서 `positioned["ap_channel"]` 채움

Backend `parsing.py` 는 `ap_channel` / `channel` 둘 다 인식하므로 그대로 저장된다.

**현장 AP 채널이 6이 아니면 `--ap-channel` 값과 펌웨어 상수를 함께 고친다.**

### 검증 (테스트 4개를 함께 넣는다)
- -105 dBm 샘플이 살아남는가
- -120 dBm 은 여전히 버려지는가
- `ap_channel` 이 채워지는가 / 지정하지 않으면 빠지는가

## 4. `node_positions.json` — 손대지 않는다

Backend 의 측정 경로는 payload 좌표를 저장하지 않는다(위 정정 참고).
`node-02` 는 T1~T10 을 옮겨 다니는데 이 파일은 "노드 1대 = 좌표 1개" 구조이고
시작할 때 한 번만 읽으므로(재로딩 없음) 애초에 이동 좌표를 담을 수 없다.

README 에 다음을 적어 둔다.

- 이 파일 좌표는 실시간 경로 전용이다
- 현장에서 위치를 바꿨으면 **Backend 등록 좌표**를 고친다 (좌표 출처를 하나로 유지)

## 5. 현장 사전 점검 (측정 시작 전) — 남은 항목

### 5-1. 시간 동기 순서 — 가장 중요
`node_time.c` 의 `node_time_now_ms()` 는 시각이 2024-01-01 이후인지만 본다.
**한 번 맞으면 그 뒤로 다시 무효가 되지 않는다**(SNTP 재동기 실패해도 무관).
반대로 **한 번도 못 맞으면** 모든 샘플에 `RSSI_ERR_TIME_INVALID` 가 붙어 전량 무효가 된다.

노드는 AP 에 STA 로 계속 붙어 있으려 하는데(`wifi_event_handler` 무한 재접속),
-105 dBm 지점에서는 association 자체가 되지 않는다.

**규칙: 5대를 AP 근처에서 켜고 로그의 `SNTP synchronized` 를 확인한 뒤 자리로 옮긴다.**
pre-offset 측정(계획서 §6.1, 5대를 한 곳에 모음)을 AP 근처에서 하면 자연히 충족된다.
현장 배터리 교체·재부팅도 반드시 AP 근처에서 한다.

부수 효과(기록만): 깊은 그림자 지점에서는 STA 재접속 시도가 RSSI 스캔과 무선을 다투어
샘플 주기가 흔들릴 수 있다. 데이터가 죽지는 않는다.

### 5-2. AP BSSID·채널 확인
`node_config.h` / `gateway_config.h` 에 BSSID `B0:38:6C:52:BA:FE`, 채널 6 이 **하드코딩**되어 있다.

- 현장 AP 의 BSSID 가 다르면(휴대폰 핫스팟은 MAC 이 바뀔 수 있음) 전 노드가 AP 를 못 찾는다
- 채널이 6이 아니면 `#error` 가드 때문에 두 상수를 함께 고쳐 다시 빌드해야 한다
- 비밀번호는 추적되지 않는 `time_credentials.h` 에 있어야 한다(`*.example.h` 참고)

**측정 당일 아침에 BSSID·채널을 실제로 확인하고, 다르면 그 자리에서 재빌드한다.**

### 5-3. ESP-NOW 상향 링크 도달 확인
계획서 §7 은 "AP 신호가 잡히는가" 만 확인하는데, 데이터가 남으려면
**노드 → gw-01(ESP-NOW 브로드캐스트, 채널 6)** 경로도 살아야 한다.

- `gw-01` 은 C4 `(5.86, 18.56)` 에 있고 C2 `(24.02, 6.31)` 까지 코어 뒤 **약 22 m** 다.
  C2 에서 TX 까지 거리(11.8 m)보다 **더 나쁜 조건**이다.
- 예비 좌표 `(34.40, 6.60)` 은 게이트웨이에서 **약 31 m** 로 더 멀다.

**절차:** C1~C4 배치 직후 Backend `GET /nodes/status` 에서 4대가 모두 online 인지 확인한다.
C2/C3 가 AP 는 잡는데 게이트웨이로 못 보내면, **C2 를 옮기기 전에 gw-01(C4)을
넓은 복도 안쪽으로 옮기는 것**을 먼저 검토한다(C4 는 LOS 조건만 지키면 되므로 자유도가 크다).
옮기면 좌표를 그 자리에서 기록하고 Backend 등록 좌표와 `tx_rx.json` 을 함께 갱신한다.
