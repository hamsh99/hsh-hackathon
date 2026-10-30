# 시작: 실제 과제 폴더에서

하네스는 서비스 구현이 아니라 작업 규칙·양식·검증 보조 도구다.
Python 3.10 이상만 필요하며 외부 패키지·MCP·개인 API 키를 요구하지 않는다.
실전에서 Python이 없으면 자동 설치하지 말고 문서를 직접 읽는 방식으로 운영한다.

## 1. 현재 상태 확인
`python3 tools/doctor.py`

ENVIRONMENT_ONLY는 환경 확인일 뿐 제품 통과가 아니다. Git 저장소가 없으면
기준점이 없다고 기록한다. 이미 스테이징된 사용자 변경은 그대로 보존한다.
설치 시 AGENTS.md를 보존했다면 harness/AGENTS.suggested.md와 비교해 필요한 규칙을 합친다.
파일이 있는 것과 Codex가 자동 인식한 것을 구분한다.

## 2. Codex에 붙여 넣기
```text
현재 과제 README·공식 안내와 기존 AGENTS.md를 먼저 읽어줘.
harness/START.md와 OPERATIONS.md의 '01 새 문제'를 적용해줘.
지금은 요구사항과 첫 기능 계획을 세우고 실행 환경을 확인하는 단계야.
기존 파일과 사용자 변경을 보존하고, 읽은 범위와 가정을 밝혀줘.
시작·마감: [시간대 포함 입력].
```

## 3. 실제 검사 설정
TASK의 계약을 먼저 정하고 CONFIG_GUIDE.md에 따라 harness/checks.json을 채운다.
기본값은 checks=[]이므로 `status`는 NOT_CONFIGURED, `release`는 NOT_READY가 정상이다.
예제 설정을 과제의 실제 검사인 것처럼 복사하지 않는다.

원본이 있으면 originals.mode=tracked, paths에 실제 경로를 지정한 뒤:
`python3 tools/check.py originals init`
원본이 없으면 mode=none, reason에 확인한 이유를 적는다. 시작 코드는 Git 기준점으로 보존한다.

## 4. 기능 단위 운영
```text
python3 tools/check.py run T-001
python3 tools/check.py status
```
T-001은 실제로 등록한 검사 ID다. 명령 반환 0만 보지 말고 category·status·counts를 확인한다.
코드 변경 후 TASK의 상태는 status 결과를 바탕으로 Codex가 갱신한다.

사람 확인은 `run M-UI`로 대기 기록을 만든 뒤, 사용자가 실제로 확인한 경우에만:
```text
python3 tools/check.py confirm <RUN-ID> --result pass --observer 사용자 --observation "실제로 본 조작과 결과"
```
<RUN-ID>는 실제 대기 실행 ID로 바꾼다. 위 문장 자체를 관찰 결과로 쓰지 않는다.
대기 이후 코드가 바뀌면 STALE이다. 새 run으로 재확인한다.

## 5. 종료·제출
`python3 tools/check.py release`

이 명령은 로컬 설정 기준으로 검토한다. 제출·push·배포를 실행하지 않는다.
공식 제출 규칙과 플랫폼의 실제 수집 범위를 별도로 확인하고, 최종 체크리스트를 사람이 검토한다.
제출 성공 여부는 플랫폼에서 확인한다.

## 시간 제안
0~15분 초기 확인, 15~40분 첫 실제 흐름, 40~115분 필수 기능,
115~135분 필수 누락 해결, 135~160분 최종 검사, 160~180분 제출·여유.
한 기능 15~25분, 약 10분 막히거나 같은 접근 두 번 실패하면 원인을 재분류한다.
선택 기능부터 줄이고 공식 필수 요구를 몰래 제외하지 않는다.

## 용어
- 계약: 어떤 입력에 어떤 결과와 오류를 내야 하는지 정한 약속.
- 해시·지문: 파일 내용이 바뀌었는지 비교하는 식별값.
- 통합 검사: 여러 부분이 연결되어 실제 흐름이 되는지 확인.
- handoff: 다른 세션이 이어갈 현재 상태와 다음 행동의 요약.
- 리팩토링: 동작을 유지하면서 내부 구조를 개선하는 작업.
