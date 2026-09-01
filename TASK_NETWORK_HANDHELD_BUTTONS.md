# 작업 지시서 — 핸드헬드 버튼 2개를 Graphics로 중계 (네트워크/백엔드)

이 파일 하나로 작업할 수 있게 필요한 정보를 전부 담았다. 막히는 부분이 있으면
`RFVisualizer-Docs/INTERFACE.md` §11(Handheld Control Interface)을 확인한다.

## 목표

RFHC Packet의 `flags` bit1·bit2(버튼 상태)를 그대로 읽어서 `/handheld/control`
WebSocket의 `handheld_state` 메시지에 실어 Graphics로 넘긴다. **새로 판단하거나,
중복 제거하거나, 응답을 기다리는 로직이 필요 없다** — `orientation_valid`를 지금
그대로 통과시키는 것과 완전히 같은 패턴이다.

## 배경

기획이 바뀌어 "방향 Recenter 버튼", "Position Update 버튼"은 폐기했다. 대신:

1. **텔레포트 버튼** — PC Viewer에서 "누르고 조준, 떼면 이동"하는 기능. 판단·동작은
   전부 Graphics(SIBR Viewer)가 한다.
2. **Height-cycle 버튼** — 누를 때마다 Graphics가 Heatmap 표시 높이를 프리셋 순서로
   한 칸씩 바꾼다.

Backend는 이제 두 버튼에 대해 **아무것도 계산하지 않는다.** RFHC에서 읽은 bit를 그대로
전달만 하면 끝이다. 예전 두 버튼(Position Update/Recenter)이 Backend에 요구했던
"anchor 재계산", "PositionProvider 조회", "accepted/rejected 응답" 같은 로직은 새
버튼에는 해당 사항이 없다.

## 확정된 Wire 규격 (RFHC v1, `INTERFACE.md` §11.3·§11.6 반영 완료)

### 수신 쪽 (RFHC Parser, 이미 구현된 것 — bit 의미만 바뀜)

RFHC Packet 구조·CRC 계산은 그대로다. `flags` bit1·bit2의 **의미만** 바뀐다.

| Bit | 이름 | 값 |
|---:|---|---|
| 0 | `ORIENTATION_VALID` | 기존 그대로 |
| **1** | **`TELEPORT_BUTTON_HELD`** | **텔레포트 버튼의 그 순간 물리 상태(레벨)** |
| **2** | **`HEIGHT_CYCLE_BUTTON_HELD`** | **Height-cycle 버튼의 그 순간 물리 상태(레벨)** |
| 3 | `TIME_SYNCED` | 기존 그대로 |

`event_seq` 필드(offset 20)는 2026-08-28부터 미사용이다 — Embedded가 `0`을 보낸다.
Parser가 이 필드를 특별 취급하고 있었다면(예: 기존 버튼 dedup 키로 사용) 그 부분만
제거하면 된다. Parsing 자체(byte offset, CRC 검증)는 바뀌지 않는다.

### 송신 쪽 (`handheld_state` WebSocket 메시지 — 필드 교체)

```
기존: "recenter_event": boolean, "position_update_event": boolean
신규: "teleport_button_held": boolean, "height_cycle_button_held": boolean
```

`orientation_valid`와 정확히 같은 방식으로 채운다 — RFHC bit1·bit2를 그대로 읽어
그 순간 값을 넣기만 한다. Frame마다 매번 보낸다(값이 안 바뀌어도 계속 보낸다).
`event_seq` 필드도 이 메시지에서 제거한다(더 이상 의미 없음).

### 완전히 없어지는 것

- `position_update` WebSocket 메시지 타입 — 더는 아무도 트리거하지 않는다. 전송
  로직을 삭제한다.
- `(device_id, session_id, event_seq, flag)` 기반 Recenter/Position Event 중복 제거
  로직 — 새 두 버튼에는 dedup이 필요 없으므로 삭제한다.
- 버튼 3-packet 반복 관련 처리가 Backend에 있었다면 그것도 삭제한다.

### 그대로 남기는 것 (지우지 않는다)

- `PositionProvider` / `ConfiguredPositionProvider` 클래스와 REST Endpoint
  (`GET /handheld/positions`, `POST /handheld/position/active`, `GET /handheld/status`).
  버튼과의 연결만 끊길 뿐, 코드 자체는 다른 용도(수동 테스트, 향후 실제 위치 추정
  연동)로 계속 쓸 수 있으므로 삭제하지 않는다. `INTERFACE.md` §10에 이미 이렇게
  정리해 뒀다.
- `session_id`, `sample_seq` 기반 Session/Sample 중복 제거·재부팅 판정 로직 — 이건
  버튼과 무관하게 계속 필요하다.
- `orientation_valid`/`stale` 처리 로직.

## 작업 목록

1. RFHC Parser에서 `flags` bit1·bit2를 읽는 부분의 이름/주석을
   `REQUEST_POSITION_UPDATE`/`RECENTER_ORIENTATION`에서 `TELEPORT_BUTTON_HELD`/
   `HEIGHT_CYCLE_BUTTON_HELD`로 바꾼다. Byte 파싱 로직 자체는 안 바뀐다.
2. `event_seq` 기반 dedup·3-packet 반복 처리 로직을 삭제한다(§ "완전히 없어지는 것").
3. `handheld_state` 송신 payload에서 `recenter_event`/`position_update_event`를
   `teleport_button_held`/`height_cycle_button_held`로 교체한다.
4. `position_update` WebSocket 메시지 송신 코드를 삭제한다.
5. `PositionProvider`/REST Endpoint는 그대로 둔다(§ "그대로 남기는 것") — 삭제하지
   않는다.

## 완료 기준

- 기존 RFHC Parser Host Test(공유 CRC Test Vector 포함)가 구조체·CRC 부분은 그대로
  통과한다.
- bit1·bit2를 각각 세팅한 Packet을 넣었을 때 `handheld_state`에 올바른
  `teleport_button_held`/`height_cycle_button_held` 값이 나오는지 확인하는 Test를
  추가한다(기존 Recenter/Position Event 관련 Test는 이 Test로 교체·삭제).
- Handheld 관련 기존 통합 테스트가 새 필드명으로 통과한다.
- 완료 후 `network/NETWORK.md` §13(Handheld Control)을 "구현·실물 검증 완료"로
  갱신한다. 이 문서(`RFVisualizer-Docs`)는 네트워크 파트가 직접 고치거나, 고친
  내용을 알려주면 그래픽스 파트가 반영한다.

## 참고

- `RFVisualizer-Docs/INTERFACE.md` §10(PositionEstimate), §11(Handheld Control
  Interface) — 이 규격의 원본이자 최종 기준.
- `RFVisualizer-Docs/network/NETWORK.md` §13 — 이 파트의 현재 구현 상태 전체.
