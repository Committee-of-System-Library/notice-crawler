import logging
import os
import time
from main import run
import traceback
from datetime import datetime
from main import run

"""
@file runner.py
@brief Notice Crawler 반복 실행을 담당하는 모듈

이 모듈은 Docker 컨테이너 환경에서 Notice Crawler를
주기적으로 실행하기 위한 엔트리포인트(Entry Point) 역할을 한다

기존 main.py는 CLI 인자를 기반으로 단일 게시판에 대해
1회성 크롤링을 수행하도록 설계되어 있다
runner.py는 해당 로직을 래핑하여 모든 게시판 유형을
일괄 실행하고, 지정된 주기마다 반복 수행한다

@details
동작 흐름:

1. 환경변수 CRAWL_INTERVAL_MINUTES 값을 읽는다
   (기본값: 5분)
2. run_all() 함수를 통해 다음 게시판을 순차적으로 크롤링한다
   - 공지사항 (-Notice)
   - 학부인재모집 (-Recruiting)
   - 취업정보 (-Employment)
3. 지정된 시간(분 단위)만큼 대기한다
4. 무한 루프를 통해 위 과정을 반복 수행한다

이 구조를 통해 컨테이너 실행만으로도
Host 환경의 별도 cron 설정 없이 자동 반복 크롤링이 가능하다

@note
- 크롤링 주기는 환경변수 CRAWL_INTERVAL_MINUTES 로 제어
- 컨테이너 실행 시 자동으로 동작하도록 Dockerfile의 CMD에 등록
- 예외 발생 시 로그를 출력하고 다음 주기에 다시 시도

@warning
CRAWL_INTERVAL_MINUTES 값이 너무 짧게 설정될 경우
대상 서버에 과도한 요청이 발생할 수 있다

@see main.py
"""
os.makedirs("logs", exist_ok=True)

general_logger = logging.getLogger("crawler")
general_logger.setLevel(logging.INFO)

error_logger = logging.getLogger("crawler.error")
error_logger.setLevel(logging.ERROR)


formatter = logging.Formatter(
    "%(asctime)s [%(levelname)s] %(message)s"
)

class InfoOnlyFilter(logging.Filter):
    def filter(self, record):
        return record.levelno in (logging.INFO, logging.ERROR)
    
# 일반 로그
general_handler = logging.FileHandler("logs/general.log")
general_handler.setLevel(logging.INFO)
general_handler.setFormatter(formatter)
general_handler.addFilter(InfoOnlyFilter())

# 에러 로그
error_handler = logging.FileHandler("logs/error.log")
error_handler.setLevel(logging.ERROR)
error_handler.setFormatter(formatter)


general_logger.handlers.clear()
error_logger.handlers.clear()

general_logger.addHandler(general_handler)
error_logger.addHandler(error_handler)

general_logger.propagate=False
error_logger.propagate=False

# 크롤링 주기
INTERVAL = int(os.getenv("CRAWL_INTERVAL_MINUTES", "5"))

def run_all():
    """모든 게시판 유형을 순차적으로 크롤링"""
    run("-Notice")
    run("-Recruiting")
    run("-Employment")
    run("-SeminarEvent")
    run("-SchoolNews")

    general_logger.info("Finish crawling cycle")


if __name__ == "__main__":
    general_logger.info(f"Runner started (interval={INTERVAL} minutes)")

    while True:
        try:
            general_logger.info("Start crawling notices")
            run_all()
            general_logger.info("Crawler tick finish")

        except Exception:
            general_logger.error("Error occurred during crawling")
            error_logger.exception("Error occurred during crawling")

        general_logger.info(f"Sleep {INTERVAL} minutes\n")
        time.sleep(INTERVAL * 60)
