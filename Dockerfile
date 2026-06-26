##
# @file Dockerfile
# @brief Notice Crawler 컨테이너 이미지 빌드 정의 파일
#
# 본 Dockerfile은 Notice Crawler를 Docker 환경에서
# 독립적으로 실행하기 위한 이미지를 생성
#
# 주요 기능:
# - Python 3.11 기반 경량 이미지 사용
# - requirements.txt를 통해 의존성 설치
# - runner.py를 실행 엔트리포인트로 설정
#
# 동작 방식:
# 컨테이너 실행 시 runner.py가 실행되며
# CRAWL_INTERVAL_MINUTES 환경변수에 따라
# 일정 주기로 크롤링을 반복 수행
#
# 환경변수:
# - CRAWL_INTERVAL_MINUTES (default: 5)
#
# @note
# Host 환경의 cron 설정 없이 컨테이너 단독 실행만으로
# 자동 반복 크롤링이 가능하도록 설계함
##

FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV CRAWL_INTERVAL_MINUTES=5
ENV PYTHONUNBUFFERED=1

CMD ["python","-u", "runner.py"]