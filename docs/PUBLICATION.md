# 공개 배포와 설치 확인

- 대상 계정·저장소 이름: hamsh99/hsh-hackathon.
- 검토한 소스 기준: 1873df42ab8f77a2fb73228eb48dcbb7a433d76c.
- 원래 개발 저장소의 Git 이력은 공개본으로 복사하지 않았다. 공개본은 별도 첫 커밋에서 시작한다.
- 실제 도구·테스트·설치 코드는 원본과 동일하다. README의 clone 안내와 공개 기록 관리 문서만 조정했다.
- 개발 시점 최신 실행의 root/cwd/command에서 로컬 절대경로를 치환했다. 원본 JSON SHA-256은 공개 복사본에 기록했다.
- 새 실행은 artifacts에 저장하고 Git에서 제외한다. 공유할 근거는 필요한 내용을 검토한 뒤 공개 복사본으로 만든다.
- 비밀키·로그인 설정은 포함하지 않는다. 테스트에 있는 secret/PRIVATE KEY 문자열은 차단 검사 코드이며 실제 비밀값이 아니다.
- GitHub 공개 여부와 clone 성공 여부는 별도로 확인한다.

## 실제 공개·설치 확인

- 확인 시각: 2026-10-30T16:55:59Z (UTC).
- 저장소: https://github.com/hamsh99/hsh-hackathon (public).
- 업로드 커밋: `000f46e77da2bfab12465af8d720307f30acf93d`.
- GitHub API로 원격 34개 파일의 Git blob 해시가 공개본과 모두 일치함을 확인했다.
- 사용자가 만든 최초 README 커밋을 부모로 유지했다. 기존 원격 이력을 덮어쓰지 않았다.
- 아래 설치 확인은 원격과 일치하는 공개본을 임시 과제 폴더의 `work/sk-hackathon-harness`에 놓고 수행했다. 실제 clone으로 받은 사본에서 실행한 것은 아니다.

작업 위치는 임시 과제 폴더이며, Python 3.14.3/macOS에서 실행했다.

| 실제 명령 | 종료 코드 | 관찰 결과 |
|---|---:|---|
| `python3 work/sk-hackathon-harness/install.py .` | 0 | PREVIEW, 파일 변경 없음 |
| `python3 work/sk-hackathon-harness/install.py . --apply` | 0 | APPLIED |
| `python3 tools/doctor.py` | 0 | ENVIRONMENT_ONLY |
| `python3 tools/check.py status` | 2 | NOT_CONFIGURED: 실제 과제 검사를 아직 설정하지 않음 |
| `python3 tools/check.py release` | 2 | NOT_READY: 실제 제출 준비 완료로 표시하지 않음 |
| 동일한 install 명령에 `--apply`로 재적용 | 0 | 기존 파일의 SHA-256 모두 유지 |

별도 `git clone https://github.com/hamsh99/hsh-hackathon.git hsh-hackathon` 시도는 종료 코드 128, `Could not resolve host: github.com`으로 차단되었다. 실행 환경의 DNS 문제로 다운로드 경로는 검증하지 못했으며 사용자 실전 환경에서 다시 확인해야 한다. 공개 API 접근 성공을 clone 성공으로 취급하지 않는다.

이 확인은 배포 파일 일치와 설치 동작에 한정된다. 실제 과제 기능·화면·AI 연동·제출의 통과 증거가 아니다.
