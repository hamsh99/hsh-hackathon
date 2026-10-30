# 다음 세션을 위한 상태

대상: 하네스 자체 개발 저장소. 실제 해커톤 서비스가 아니다.
완료: 설치 도구, 공통 규칙, 작업 프롬프트 9개, 기록 양식 4개, 점검 도구 2개와 내부 모듈.
검증: VERIFICATION.md와 EVIDENCE.md의 최신 H-SELFTEST 참조.
브랜치: main. 현재 커밋·미커밋 상태는 재개 시 `git status --short --branch`, `git log -1 --oneline`로 확인.
검증 당시 Git 상태와 파일 지문은 실행 JSON에 별도로 남아 있다.

## 다음 행동
1. 실제 과제 폴더가 정해지면 install.py 미리보기 후 --apply 적용.
2. 기존 AGENTS·README·사용자 변경을 보존하고 START.md의 시작 프롬프트 사용.
3. 과제 요구·실행 명령·원본·실제 T-ID·제출 목록 설정.
4. 실제 플랫폼에서 지침 인식, 한 기능, 세션 재개, 최종 수동 확인을 연습.

## 실행 중 환경
- 이 작업에서 서비스 서버를 시작하지 않았다.
- MCP·패키지·전역 Codex 설정을 설치/변경하지 않았다.
- 기존 연습 서비스 폴더를 수정하지 않았다.

## 차단·미확인
- 하네스 자체 자동 검사에서 알려진 실패 없음. 구체 결과는 최신 기록으로 재확인.
- 실제 제품 UI·개발 라우트 분리·외부 AI 호출·공식 제출은 미실행.
- 별도 Codex 세션의 실제 handoff 리허설은 미실행.
- GitHub 공개 완료: hamsh99/hsh-hackathon. 파일 일치·설치 확인은 PUBLICATION.md 참조.
- 현재 실행 환경의 DNS 문제로 실제 git clone은 미확인. 사용자 환경에서 README 명령으로 확인.

사용자 결정·Codex 판단·한계는 DECISIONS.md 참조. TASK에 기능별 상태를 관리한다.

공개 참고 기록은 docs/public-evidence에 있으며 새 clone의 로컬 검증으로 취급하지 않는다.
