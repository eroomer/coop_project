# 1) 베이스 이미지: 파이썬 3.10이 설치된 가벼운 리눅스
FROM python:3.10-slim

# 2) 파이썬 관련 기본 환경 변수(권장)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# 3) 컨테이너 내부 작업 폴더
WORKDIR /app

# 4) (필요할 수 있는) OS 패키지 설치
#    opencv/이미지 처리에서 자주 필요한 런타임 라이브러리
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
  && rm -rf /var/lib/apt/lists/*

# 5) 파이썬 의존성 설치 (캐시 효율 위해 requirements 먼저 복사)
COPY requirements.docker.txt /app/requirements.docker.txt
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r /app/requirements.docker.txt

# 6) 프로젝트 소스 복사
COPY . /app

# 7) 스크립트 실행권한 부여 (윈도우/깃 환경에서 권한이 날아갈 수 있어서 안전장치)
RUN chmod +x /app/scripts/run_api.sh /app/scripts/run_worker.sh

# 8) 외부에 열 포트(문서용. 실제 노출은 docker run -p에서 결정)
EXPOSE 8000

# 9) 컨테이너 시작 시 실행할 기본 명령
CMD ["/app/scripts/run_api.sh"]
