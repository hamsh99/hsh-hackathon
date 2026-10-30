# 검사 설정: 실제 과제에 맞춰 채우기

`harness/checks.json`은 실행할 검사 목록이다. TASK의 성공 조건을 바탕으로 작성한다.
지원: Python unittest, 조건을 명시한 일반 명령, 사람 확인. pytest/Jest 결과 자동 판독은 미지원이다.
Python 외 제품도 일반 명령·사람 확인으로 사용할 수 있으나 테스트 개수를 검증했다고 표현하지 않는다.

## 전체 예시 — 실제로 존재하는 파일로 바꿀 것
```json
{
  "version": 1,
  "checks": [
    {
      "id": "T-001", "feature_ids": ["F-001"], "category": "task",
      "kind": "unittest", "start_dir": "tests", "pattern": "test_input.py",
      "cwd": ".", "scope": ["src", "tests", "requirements.txt"],
      "timeout_seconds": 60,
      "expected": "대표 7행 파싱과 빈 입력·잘못된 열·중복 ID 검사"
    },
    {
      "id": "M-RELEASE", "feature_ids": ["F-001"], "category": "task", "kind": "manual",
      "scope": ["src", "tests", "requirements.txt", "README.md"],
      "expected": "공식 필수 요구·실제 진입점·현재 서버·개발 도구 제외·제출 목록 확인"
    }
  ],
  "originals": {"mode": "tracked", "paths": ["data/original"], "reason": "과제 제공 원본"},
  "submission": {
    "include": ["src", "tests", "requirements.txt", "README.md", "docs"],
    "exclude": [], "required_files": ["README.md", "requirements.txt"]
  },
  "release": {"required_checks": ["T-001", "M-RELEASE"], "manual_review_check": "M-RELEASE"}
}
```
예시의 requirements.txt 등이 없으면 삭제하거나 실제 의존성 파일로 바꾼다. 없는 파일은 차단한다.
프로젝트의 실제 진입점(app.py 등)이 있다면 검사 scope·제출 include·required_files에 포함한다.
각 필수 요구사항을 어떤 검사로 확인하는지는 TASK에서 연결한다. 프로그램이 업무 누락을 자동 이해하지 않는다.

## 필드와 규칙
- category: task(실제 과제), harness(하네스), example(예제), environment(환경).
- release는 task 범주의 필수 검사만 인정한다. 예제나 자체 검사를 제품 통과로 쓰지 않는다.
- scope: 현재 검사에 영향을 주는 파일·폴더의 상대 경로 배열. 실제 제품 진입점·호출부·테스트·입력·설정·lock 파일까지 포함한다.
- scope에 `.`이나 glob, 외부 경로, 링크는 사용하지 않는다. 디렉토리에는 새로 추가된 파일도 감지한다.
- .git·캐시·가상환경·node_modules는 해시에서 제외한다. 의존성 변경은 lock 파일과 필요한 버전 정보를 기준으로 관리한다.
- docs의 기록 4개와 work/artifacts는 제품 지문에서 제외한다. 기록을 추가했다고 모든 검사를 다시 돌리지 않는다.
- 이 제외 폴더에서 제품 코드를 실행하지 않는다. 앱이 문서나 결과 파일을 입력으로 사용하면 별도의 제품 입력 경로로 두고 scope에 지정한다.
- 설정 전체를 무조건 해시하지 않고 해당 검사 정의·원본 정책·실행 도구·Python 정보를 포함한다. 수동 확인은 제출 정책도 포함한다.
- timeout_seconds 기본 60, 최대 600초. 시간 초과는 통과가 아니다. POSIX에서는 해당 실행 프로세스 그룹을 종료한다.
- unittest는 이번 실행 ID가 있는 JSON으로 개수를 확인한다. 0개=UNVERIFIED, 건너뜀·예상 실패가 하나라도 있으면 INCOMPLETE.
- expected는 독립 기대값의 요약이다. 이 문자열만으로 정답을 검사하지 않는다. 실제 테스트 assertion이 규칙을 확인해야 한다.
- 원본 기준 파일은 한 번 생성하고 덮어쓰지 않는다. 변경 원인을 조사하기 전에 다시 기준을 만들지 않는다.

## 일반 명령
```json
{
  "id": "C-BUILD", "feature_ids": ["F-001"], "category": "task", "kind": "command",
  "purpose": "build", "command": ["npm", "run", "build"], "cwd": ".",
  "scope": ["src", "package.json", "package-lock.json"],
  "fresh_files": ["dist/index.html"], "timeout_seconds": 120,
  "expected": "빌드 성공과 이번 실행에서 갱신된 진입 파일"
}
```
purpose는 build/lint/integration/environment 중 하나다. 테스트 runner 자동 판독의 대용이 아니다.
stdout_contains(기대 문자열 배열) 또는 fresh_files(생성·갱신될 파일 배열)를 최소 하나 지정한다.
종료 코드 0만으로 통과시키지 않는다. fresh_files가 이전 파일 그대로면 INCONCLUSIVE이다.
command는 문자열 배열로 지정하며 shell=True를 사용하지 않는다. `{python}`은 현재 Python으로 치환된다.
조건은 의도한 기능을 실제로 확인해야 한다. 단순 echo나 오래된 로그 읽기를 제품 검사로 등록하지 않는다.
비밀키를 인수·예상 문자열·로그에 넣지 않는다. 명령은 기록되며 로그 자동 비밀정보 제거는 제공하지 않는다.

## 사람 확인과 서버
run으로 확인할 코드 상태를 먼저 고정하고 실제 확인 후 confirm한다.
observer와 observation은 사용자/검토자의 보고이며 도구가 화면을 보았다는 뜻이 아니다.
프로젝트 경로·실행 명령·포트·확인 시각을 STATE에 기록하고, 다른 서버가 아닌지 확인한다.
제품 화면에 빌드 식별자를 억지로 노출할 필요는 없다. 서버 재시작·실행 경로 등으로 대조한다.

## 제출
include의 파일을 실제 해시 목록으로 만들고 exclude의 정확한 경로·하위 경로만 제외한다(glob 없음).
required_files는 제외 후에도 있어야 한다. 비밀 파일명·개인키 헤더는 일부 탐지하지만 완전한 비밀 탐지가 아니다.
최종 수동 검토의 scope는 제출 파일을 포함해야 한다. 기록 4개와 artifacts/evidence는 자동 생성 근거라 별도로 목록만 확인한다.
Git ignore와 제출 제외는 별개다. 이 목록은 플랫폼 수집 자체를 바꾸지 않는다.
최종 검사 후 소스가 바뀌면 status/release가 STALE을 표시한다. 과거 결과 JSON은 수정하지 않는다.

## 임시 데이터
`python3 tools/check.py sandbox new`로 생성한 TMP-ID 폴더만 clean할 수 있다.
`python3 tools/check.py sandbox clean <실제 TMP-ID>`는 해당 실행 폴더만 삭제한다.
빈 경로·상위 폴더·외부 링크·다른 프로젝트 마커를 거부한다. 실제 사용자 데이터는 work/runs에 두지 않는다.
동시 악의적 경로 변경까지 방어하는 보안 도구는 아니다. 한 세션의 신뢰 가능한 로컬 작업용이다.
