# 작업 지시서 — 핸드헬드 버튼 2개를 RFHC로 송신 (임베디드)

이 파일 하나로 작업할 수 있게 필요한 정보를 전부 담았다. 막히는 부분이 있으면
`RFVisualizer-Docs/INTERFACE.md` §11(Handheld Control Interface)을 확인한다.

## 목표

물리 버튼 2개의 눌림 상태를, 기존에 이미 50 Hz로 나가고 있는 IMU Quaternion RFHC
Packet에 실어 Backend(UDP `9200`)로 보낸다. 새 Task·새 연결·새 Packet 종류를 만들지
않는다 — 기존 Packet의 `flags` 필드 2비트만 채운다.

## 배경

기획이 바뀌어 "방향 Recenter 버튼", "Position Update 버튼"은 폐기했다. 대신:

1. **텔레포트 버튼** — PC Viewer에서 "누르고 조준, 떼면 이동"하는 기능(SIBR Viewer 쪽은
   이미 구현돼 있고 그래픽스 파트가 별도로 연결 중이다).
2. **Height-cycle 버튼** — 누를 때마다 PC Viewer의 Heatmap 표시 높이가 프리셋 순서로
   한 칸씩 바뀐다.

두 기능 다 판단과 동작은 전부 PC(SIBR Viewer)가 한다. **Embedded가 할 일은 버튼의 현재
눌림 상태를 정직하게 실어 보내는 것뿐이다.** 위치를 계산하거나, 이벤트를 몇 번 반복해서
보내거나, 서버 응답을 기다리는 로직이 전혀 필요 없다 — 이 점이 예전 두 버튼 기획과
가장 다른 부분이다.

## 확정된 Wire 규격 (RFHC v1, `INTERFACE.md` §11.2·§11.3 반영 완료)

Packet은 52 byte 고정, 이미 구현된 그대로다. **바꾸는 건 `flags` 필드 2개 bit뿐이다.**

| Offset | 크기 | 필드 | 이번 작업에서 바뀌는 점 |
|---:|---:|---|---|
| 0 | 4 | `magic` | 그대로 (`0x52464843`) |
| 4 | 1 | `version` | 그대로 (`1`) |
| 5 | 1 | `flags` | **bit1·bit2 의미가 바뀜 — 아래 표** |
| 6 | 2 | `packet_length` | 그대로 (`52`) |
| 8 | 4 | `device_id` | 그대로 |
| 12 | 4 | `session_id` | 그대로 |
| 16 | 4 | `sample_seq` | 그대로 |
| 20 | 4 | `event_seq` | **더 이상 안 씀 — `0` 고정으로 보낸다** |
| 24 | 8 | `timestamp_ms` | 그대로 |
| 32~44 | 16 | quaternion x/y/z/w | 그대로, 이미 구현·검증됨 |
| 48 | 4 | `crc32` | 계산 방식 그대로 (CRC-32/ISO-HDLC, offset 0~47) |

`flags` bit 정의:

| Bit | 이름 | 값 |
|---:|---|---|
| 0 | `ORIENTATION_VALID` | 기존 그대로 |
| **1** | **`TELEPORT_BUTTON_HELD`** | **텔레포트 버튼을 지금 물리적으로 누르고 있으면 1, 아니면 0** |
| **2** | **`HEIGHT_CYCLE_BUTTON_HELD`** | **Height-cycle 버튼을 지금 물리적으로 누르고 있으면 1, 아니면 0** |
| 3 | `TIME_SYNCED` | 기존 그대로 |
| 4~7 | Reserved | 그대로 항상 `0` |

**핵심: bit1·bit2는 "이벤트"가 아니라 "그 순간의 물리 상태"다.** 예전처럼 버튼 하나
누를 때마다 Packet 3개에 반복해서 보내거나 `event_seq`를 관리할 필요가 **없다.** 매
50 Hz Packet마다 그 순간 debounce된 버튼 상태를 그대로 1비트씩 채워 보내면 끝이다.
Packet이 중간에 하나 유실돼도 다음 Packet에서 상태가 이어지므로 신뢰성 문제가 없다.

## 작업 목록

1. **버튼 GPIO 2개 배선·읽기.** 보드에 남는 GPIO 아무거나 사용, 극성(active-low/high)은
   회로에 맞춰 정한다. 어떤 핀·극성을 썼는지 `EMBEDDED.md`(§3 설정값 근처 또는 §11
   하드웨어 계획)에 표로 남긴다.
2. **Debounce.** 20~30 ms 정도의 표준 소프트웨어 debounce면 충분하다(정밀 값이 중요한
   기능이 아니다). 이미 쓰는 debounce 유틸이 있으면 그걸 재사용한다.
3. **RFHC Serializer 연결.** RFHC v1 Serializer는 이미 Component로 존재하지만
   `app_main`의 실제 UDP 송신 Task에서 아직 호출되지 않는다(`EMBEDDED.md` 기준). 기존
   IMU Quaternion 송신 Task(`handheld_jpeg_stream`)에 얹어서, 매 Packet 조립 시 위 두
   GPIO의 현재 debounce된 상태를 `flags` bit1·bit2에 채우고 `event_seq=0`으로 보낸다.
   새 Task는 만들지 않는다.
4. **버튼 2개의 물리 배치.** 텔레포트는 "누르고 있다가 떼는" 제스처라 조준 중 다른 손
   동작(특히 방향 조작)과 안 겹치는 위치가 좋다. 배치 이유를 문서에 한 줄 남긴다.

## 하지 않아도 되는 것 (예전 기획에서 남은 것 — 이번엔 필요 없음)

- 버튼 Event 3-packet 반복 로직
- `event_seq` 증가/관리
- Backend 응답을 기다리는 로직 (Position Update가 하던 accepted/rejected 확인 같은 것)
- 부팅 시 로컬 LCD Wireframe의 자세 Recenter — 이건 이번 변경과 **무관한 별개 기능**이라
  건드리지 않는다(RFHC 네트워크 bit와 무관한, 핸드헬드 자체 로컬 동작).

## 완료 기준

- 기존 RFHC Serializer Host Test(공유 CRC Test Vector 포함)가 그대로 통과한다 — bit1·bit2
  의미만 바뀌었지 구조체 레이아웃과 CRC 계산은 그대로이므로 기존 Test Vector가 깨지면 안 된다.
- 두 버튼을 각각 눌렀을 때 UDP로 나가는 Packet의 `flags` bit1·bit2가 물리 상태와 정확히
  일치하는지 로그나 간단한 Host Test로 확인한다(새 Test 하나 추가 권장 — Serializer에
  버튼 상태 두 개를 넣었을 때 나오는 byte가 기대한 flags 값과 일치하는지만 보면 된다).
- 완료 후 `EMBEDDED.md` §2.2(버튼 목록), §10(검증 상태), §12(버튼 절), §13(다음 작업)의
  해당 항목을 "구현·실물 검증 완료"로 갱신한다. 이 문서(`RFVisualizer-Docs`)는 임베디드
  파트가 직접 고치거나, 고친 내용을 알려주면 그래픽스 파트가 반영한다.

## 참고

- `RFVisualizer-Docs/INTERFACE.md` §11 — 이 규격의 원본이자 최종 기준.
- `RFVisualizer-Docs/embedded/EMBEDDED.md` — 이 파트의 현재 구현 상태 전체.
