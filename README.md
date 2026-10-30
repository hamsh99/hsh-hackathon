# 3시간 Codex 개발 하네스 v1.0.0

작은 기능을 실제 서비스에 연결하며 구현·검증·설명하기 위한 재사용 묶음입니다.
특정 서비스나 웹 프레임워크를 포함하지 않습니다. 이 폴더의 테스트는 하네스 자체 검사입니다.

**Python 3.10 이상, 추가 패키지 없음, MCP 불필요.** 실제 실행 검증 환경은 docs/VERIFICATION.md에 기록합니다.
공식 시험 규정은 포함하지 않습니다. 과제의 공식 지시·제출 형식·허용 환경을 우선합니다.

## GitHub에서 과제 폴더로 불러오기

일반 터미널에서 실제 과제 폴더로 이동한 뒤 아래 명령을 실행합니다.
MCP나 GitHub 로그인은 공개 저장소를 내려받는 데 필요하지 않습니다.

```bash
git clone https://github.com/hamsh99/hsh-hackathon.git work/sk-hackathon-harness
python3 work/sk-hackathon-harness/install.py .
python3 work/sk-hackathon-harness/install.py . --apply
```

끝의 `.`은 현재 과제 폴더입니다. clone한 하네스 폴더로 이동하지 않습니다.
같은 이름의 폴더가 이미 있으면 삭제하지 말고 기존 다운로드인지 확인합니다.
첫 install 명령은 미리보기, 두 번째는 적용입니다. 기존 규칙·문서는 보존합니다.
적용 후 Codex에 `harness/START.md를 읽고 기존 규칙과 공식 과제 안내를 확인해줘`라고 요청합니다.
자동 지침 인식 여부는 별도로 확인합니다.

## ZIP 또는 로컬 폴더에서 적용할 때

아래 경로는 실제 하네스와 과제 폴더로 바꿉니다. 과제 폴더가 이미 있어야 합니다.

```bash
python3 "/하네스경로/sk-hackathon-harness/install.py" "/과제폴더"
python3 "/하네스경로/sk-hackathon-harness/install.py" "/과제폴더" --apply
```

첫 명령은 변경 예정 목록만, 두 번째는 실제 적용입니다. 결과가 CONFLICT이면 아무 파일도 쓰지 않습니다.
이미 있는 문서·규칙·설정은 보존하고, 다른 도구 파일은 덮어쓰지 않습니다.
Git 초기화·커밋·push·전역 설정 변경·패키지 설치는 수행하지 않습니다.
기존 AGENTS.md가 있으면 `harness/AGENTS.suggested.md`에 제안 규칙을 두므로 직접 비교해 합칩니다.
기존 `.gitignore`는 수정하지 않습니다. `harness/gitignore.suggested`를 검토해 필요한 항목만 반영합니다.

과제 폴더로 이동한 뒤:
```bash
python3 tools/doctor.py
python3 tools/check.py status
```
초기 상태의 NOT_CONFIGURED는 오류가 아니라 **아직 제품 검사 설정을 안 했다는 뜻**입니다.
`harness/START.md`의 프롬프트를 Codex에 전달하세요. 자동 지침 인식은 따로 확인합니다.
Python이 없는 환경에서는 새 도구 설치를 이어가기보다 문서와 기존 검사 명령을 직접 사용합니다.

## 실제 작업의 짧은 순서
1. 공식 안내와 실행 환경을 읽고 TASK에 R-ID·F-ID·성공 조건 작성.
2. 다음 기능만 상세 계약 작성. 실제 검사·원본 분류·제출 목록을 checks.json에 설정.
3. 기능을 실제 진입점에 연결한 뒤 `python3 tools/check.py run T-001` 실행.
4. 사람이 봐야 하면 수동 run을 만들고 실제 확인 후 confirm.
5. `python3 tools/check.py status`를 확인하여 TASK·STATE 갱신.
6. 의미 있는 검증 후 변경 내용을 검토하고 필요 시 커밋. 기존 스테이징은 보존.
7. 마지막에 `python3 tools/check.py release`와 사람 체크리스트 수행.

## 구성
| 위치 | 역할 |
|---|---|
| AGENTS.md | 짧은 공통 규칙 |
| harness/OPERATIONS.md | 복사해 사용할 9개 작업 프롬프트 |
| harness/START.md | 과제 폴더에 적용한 뒤 시작 방법 |
| harness/CONFIG_GUIDE.md | 실제 검사·원본·제출 범위 설정 |
| harness/RELEASE_CHECKLIST.md | 최종 사람 확인 |
| harness/EXAMPLE.md | 가상 CSV 서비스의 기능 계획 예제(서비스 구현 없음) |
| templates/docs/ | 요구사항·상태·결정·증거 양식 4개 |
| tools/doctor.py | 읽기 중심 환경 확인 |
| tools/check.py | 검사·현재 상태·원본·안전한 임시 정리·제출 점검 |
| tools/_core.py, _unittest_runner.py | 위 명령의 내부 공통 코드와 실제 unittest 실행기 |
| tests/ | 임시 프로젝트에서 하네스 동작을 검증하는 회귀 검사 |
| docs/VERIFICATION.md | 실제 자체 검사 결과와 미확인 범위 |
| docs/ACCEPTANCE.md | 계획의 H-01~H-18과 검증 방법·한계 |

## 실제 실행 근거
검사마다 `artifacts/evidence/RUN-.../result.json`과 로그를 남깁니다.
기본 출력은 지문과 요약이며, 전체 정보는 저장된 JSON 또는 `--verbose`로 확인합니다.
원본 기록은 덮어쓰지 않고 현재 코드와 비교해 STALE(재검증 필요)을 표시합니다.
검사 범위 밖 파일은 자동 추적하지 않으므로 실제 진입점·호출부·데이터·설정·의존성을 scope에 넣습니다.
unittest의 실제 테스트 디렉토리는 scope에서 빠져도 자동으로 포함합니다.

## 종료 코드와 의미
- 0: 해당 작업의 성공. doctor는 환경 확인, status는 등록된 범위 상태 확인일 뿐 제품 전체 완료가 아닙니다.
- 1: 실제 검사 실패.
- 2: 설정 필요·차단·미검증·건너뜀·대기·오래된 결과·시간 초과·판정 불가·제출 미준비.
- release의 READY_FOR_SUBMISSION: 등록된 실제 과제 검사·사람 보고·원본·제출 목록을 충족. 실제 제출은 별도입니다.

## 자체 검사
이 **하네스 원본 폴더**에서 실행합니다. 과제 폴더에는 자체 테스트를 설치하지 않습니다.
```bash
python3 tools/check.py run H-SELFTEST
```
임시 프로젝트에서 실패 조건을 만들며, 기존 연습 서비스·사용자 데이터는 사용하지 않습니다.
테스트 성공을 실제 해커톤 기능의 성공으로 기록하지 않습니다.

## 한계
- UI를 자동으로 열거나 관찰하지 않습니다. 사람 확인은 입력한 보고이며 도구가 진실성을 보장하지 않습니다.
- pytest/Jest 등 외부 테스트 runner의 구조화된 결과 판독은 아직 없습니다. 임의 출력의 'PASS'를 테스트 통과로 파싱하지 않습니다.
- 일반 명령은 지정한 문자열·새 산출물 조건만 검사합니다. 업무 정답을 자동으로 이해하지 않습니다.
- scope 누락, 누락된 요구사항, 잘못된 테스트 기대값은 사람이 검토해야 합니다.
- 저장소 격리는 파일 경로·마커 검사 수준입니다. 신뢰할 수 없는 코드나 동시 경로 공격용 보안 샌드박스가 아닙니다.
- 기본 출력에는 비밀값을 넣지 말아야 하며 로그 자동 비밀정보 제거는 없습니다. 제출 검사도 일부 파일·개인키 표식만 탐지합니다.
- 플랫폼에서의 Codex 자동 지침 인식, 실제 AI 호출, 실제 서비스 화면, 공식 제출 절차는 아직 별도 확인 대상입니다.

공개 GitHub 자료는 설계 참고만 했고 해당 코드·스킬 파일을 복사하지 않았습니다. 출처와 판단은 SOURCES.md에 있습니다.
공개용 기록에서는 개인 로컬 경로를 치환했습니다. 원본 실행 기록은 비공개 개발본에 보존했습니다. 자세한 범위는 docs/PUBLICATION.md를 참조하세요.
