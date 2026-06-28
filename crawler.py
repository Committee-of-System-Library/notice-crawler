import logging
import requests
from bs4 import BeautifulSoup
import re
import unicodedata

from notice import *

logger = logging.getLogger("crawler")

URLs = {
        '공지사항': 'https://cse.knu.ac.kr/bbs/board.php?bo_table=sub5_1&page=',
        '학부인재모집': 'https://cse.knu.ac.kr/bbs/board.php?bo_table=sub5_3_a&page=',
        '취업정보': 'https://cse.knu.ac.kr/bbs/board.php?bo_table=sub5_3_b&page=',
        '세미나/행사':'https://cse.knu.ac.kr/bbs/board.php?bo_table=sub5_4&page=', # 추가
        '학부소식' : 'https://cse.knu.ac.kr/bbs/board.php?bo_table=sub5_2_a&page=',
    }

CATEGORY_ALIAS = {
    '전체' : 'ALL',
    '일반공지' : 'NORMAL',
    '학사' : 'STUDENT',
    '장학' : 'SCHOLARSHIP',
    '심컴' : 'SIM_COM',
    '글솝' : 'GL_SOP',
    '인컴' : 'IN_COM', #변경
    '대학원' : 'GRADUATE_SCHOOL',
    '대학원 계약학과' : 'GRADUATE_CONTRACT',

    # 추가
    'ICT융합[학부]' : 'ICT',
    '학부인재모집': 'RECRUITING',
    '세미나/행사': 'SEMINAR_EVENT',
    '취업정보': 'EMPLOYMENT_INFO',
    '플솝[구.심컴]': 'PL_SOP',
    '첨컴': 'CHEOM_COM',

    # 학부소식
    '학부소식': 'SCHOOL_NEWS',
}

MAX_COUNT_OF_NOTICE_PER_PAGE = 0

class Crawler:
    """
    경북대학교 컴퓨터학부 공지사항을 크롤링하는 클래스

    기능:
        - 공지 목록 페이지 요청 및 HTML 파싱
        - 개별 공지의 제목, 링크, 내용, 작성 시간 추출
        - Notice 객체 생성
        - 수집한 공지를 Backend(SpringBoot) API로 전송
    
    -Python 기반 크롤러, Discord Backend(Java Spring) 서버에 데이터를 전달하는 역할
    """
    def __get_max_count_of_notice_per_page(self, type: str):
        # 페이지 하나에 최대 몇 개의 공지사항이 들어있는지 확인하기
        # 모든 페이지의 최대 공지 수는 동일하고, 1번 페이지에 가장 많은 공지가 존재하므로, 1번 페이지만 확인합니다.
        # 페이지 구조 변경에 대응하며, MAX_COUNT_OF_NOTICE_PER_PAGE 전역변수를 조작합니다.
        # 
        # Parameter)
        #   type: 가져와야 할 공지사항 종류 (공지사항 / 학부인재모집 / 취업정보)
        #
        # Result)
        #   None
        global MAX_COUNT_OF_NOTICE_PER_PAGE
        response = requests.get(URLs[type] + str(1))
        soup = BeautifulSoup(response.text, 'html.parser').select_one('tbody')
        if (self.__isEmpty(soup) == 1):
            MAX_COUNT_OF_NOTICE_PER_PAGE = 0
        else:
            MAX_COUNT_OF_NOTICE_PER_PAGE = len(soup.find_all('tr'))
        
    def __get_raw_page_of_notice(self, type:str, pageNum: int) -> BeautifulSoup:
        #
        # 공지사항 페이지에서 Raw data 가져오기 
        # 하나의 페이지에 대한 Raw data 가져옵니다.
        #
        # Parameter)
        #   type: 가져와야 할 공지사항 종류 (공지사항 / 학부인재모집 / 취업정보)
        #   pageNum: 가져올 공지사항의 Page Number
        #   
        # Return) 가져온 공지사항 html code (Type: BeautifulSoup)
        #
        response = requests.get(URLs[type] + str(pageNum))
        soup = BeautifulSoup(response.text, 'html.parser')
        return soup
        
    def __isEmpty(self, rawData: str) -> int:
        #
        # 가져온 Page의 공지 글 존재 여부 반환
        #
        # Parameter) 
        #   rawData: 공지 글의 존재 여부를 판단할 페이지 (Raw Data)
        #
        # Return: 공지 없으면 1 / 공지 존재하면 0 (Type: INT)
        #
        if (rawData.find(class_='empty_table') != None):
            return len(rawData.find(class_='empty_table'))
        else:
            return 0
        
    def __get_content_and_created_time_of_notice(self, url: str) -> str:
        #
        # 파라미터로 받은 공지글 내용과 작성 시간 가져오기
        #
        # Parameter)
        #   url: 가져올 공지사항의 URL
        #
        # Return) 공지사항의 내용 (Content; Type: STR) 및 작성 시간 (Created_time; Type: STR)
        #
        # Notice) 공지사항 페이지에 표시된 시간은 적절한 형태로 수정됩니다. (YY-DD-MM HH:MM -> YYYY-DD-MM HH:MM:00)
        #
        response = requests.get(url, verify=True)
        soup = BeautifulSoup(response.text, 'html.parser')
        content = soup.select_one('#bo_v_con').get_text(strip=True).replace('\xa0', '')

        raw_date = soup.select_one('.if_date').text.replace('작성일 ', '').strip()

        if re.match(r'^\d{2}-\d{2}-\d{2} \d{2}:\d{2}$', raw_date):
            created_time = '20' + soup.select_one('.if_date').text.replace('작성일 ', '') + ':00'
        else:
            created_time = raw_date + ':00'
        return content, created_time
        
    
    def __parse_notice_of_each_page(self, type:str, pageNum: int, noticeCnt: int, noticeList: list) -> int:
        #
        # 가져온 Raw Data 파싱 -> 각 공지별 정보 추출하여 리스트에 저장
        # 하나의 페이지에 있는 공지를 파싱합니다.
        #
        # Parameter) 
        #   type: 가져와야 할 공지사항 종류 (공지사항 / 학부인재모집 / 취업정보)
        #   pageNum: 가져올 공지사항의 Page Number 
        #   noticeCnt: 한 페이지에서 가져올 공지사항의 수 -> 본 함수의 반환값에 따라 caller 함수에서 noticeCnt 값을 업데이트합니다.
        #               (크롤링한 공지 개수만큼 noticeCnt 값을 감소시킴; caller 함수는 callee 함수 (= This function) 를 반복 호출합니다.)
        #   noticeList: DB로 전송될 공지사항 객체 목록
        #               (공지사항 파싱 후, 객체를 append 합니다.)
        #
        # Return) 파싱한 공지사항 수 / -1: 공지사항 없음 (Empty Page) (Type: INT)
        #
        rawData = self.__get_raw_page_of_notice(type=type, pageNum=pageNum).select_one('tbody')
        
        if (self.__isEmpty(rawData=rawData) == 1):
            return -1
        
        rawData = rawData.find_all('tr')
        noticeCnt = MAX_COUNT_OF_NOTICE_PER_PAGE if (MAX_COUNT_OF_NOTICE_PER_PAGE < noticeCnt) else noticeCnt # 가져와야 할 공지가 페이지당 최대 공지 수보다 큰 경우
        noticeCnt = len(rawData) if (len(rawData) < noticeCnt) else noticeCnt # 가져와야 할 공지 수 > 페이지에 기록된 공지 수 (페이지에 공지가 가져와야 할 개수보다 부족)

        # 게시판별 고정 bo_table 매핑
        # 일부 게시판에서 href에 잘못된 bo_table이 포함되는 경우가 있어
        # 현재 크롤링 중인 게시판(type)을 기준으로 URL을 재생성한다.
        bo_table_map = {
                '공지사항': 'sub5_1',
                '학부인재모집': 'sub5_3_a',
                '취업정보': 'sub5_3_b',
                '세미나/행사': 'sub5_4',
                '학부소식': 'sub5_2_a',
            }
        
        for i in range(noticeCnt): # 공지사항 정보를 추출합니다.
            noticeInfo = rawData[i].find('td', class_='td_subject') 
            
            title = noticeInfo.find('div', class_='bo_tit').get_text(strip=True) # 공지 제목 추출 및 양 끝 whiteSpace 제거
            href = noticeInfo.find('div', class_='bo_tit').find('a')['href']

            match = re.search(r"wr_id=(\d+)", href)
            if not match:
                continue

            # 게시판(type)에 맞는 bo_table로 URL 재생성
            # 제목-URL mismatch 방지
            num = match.group(1)
            link = f"https://cse.knu.ac.kr/bbs/board.php?bo_table={bo_table_map[type]}&wr_id={num}"
            if (type == '공지사항'):
                cate_text = noticeInfo.find('a', class_='bo_cate_link').get_text(strip=True)

                category = CATEGORY_ALIAS.get(cate_text)# 각 공지에 지정되어 있는 카테고리 추출
                
                
                if category is None:
                    logger.warning(f"Unknown category detected: {cate_text}")
                    category="NORMAL"

            else:
                category = CATEGORY_ALIAS[type] #수정
            content, created_time = self.__get_content_and_created_time_of_notice(link) # 각 공지의 내용(Content) 및 작성 시간 (Created Time) 추출
            
            noticeObj = Notice(num=num, title=title, link=link, category=category, content=content, created_at=created_time) # 공지 객체 생성
            noticeList.append(noticeObj) #리스트에 공지 객체 추가
        
        return i + 1 # 크롤링한 공지 수 (생성된 공지 객체 수) 반환 (Type: INT)
    
    def get_all_notice(self, type: str, noticeCnt: int) -> list[Notice]:
        #
        # 공지사항을 noticeCnt 만큼 가져오는 함수
        # __parse_notice_of_each_page() 함수는 각 페이지에 있는 모든 공지를 가져옵니다. (MAX = 15)
        # __parse_notice_of_each_page() 함수를 반복 호출하여, noticeCnt 만큼 공지를 가져오면 됩니다.
        #
        # Parameter)
        #   type: 가져와야 할 공지사항 종류 (공지사항 / 학부인재모집 / 취업정보) 
        #   noticeCnt: 가져와야 할 공지사항의 수
        #
        # Return)
        #   DB로 전송될 공지사항 객체 목록 (Type: LIST[Notice])
        #
        # Notice) __parse_notice_of_each_page() 함수에 의해 공지사항 목록이 만들어집니다.
        #

        logger.info(f"Start crawling {type}")

        if type == "학부소식":
            noticeList = self.__parse_school_news(noticeCnt)
            logger.info(f"Finish crawling {type} - collected {len(noticeList)} notices")
            return noticeList

        noticeList = list()
        pageNum = 1
        self.__get_max_count_of_notice_per_page(type=type) # 페이지당 최대 공지 수 업데이트
        
        while (noticeCnt): # 가져와야 할 공지사항이 남은 경우
            crawledCnt = self.__parse_notice_of_each_page(type=type, pageNum=pageNum, noticeCnt=noticeCnt, noticeList=noticeList) # 공지 가져오기 & 가져온 공지 수 반환
            
            if (crawledCnt == -1): # 페이지에 공지가 없는 경우 -> 가져올 수 있는 모든 공지를 가져온 상황
                break
            
            noticeCnt -= crawledCnt # 가져와야 할 공자사항 수에서 가져온 공지사항 수를 빼기
            pageNum += 1 # 페이지 갱신
            
        logger.info(f"Finish crawling {type} - collected {len(noticeList)} notices")
        return noticeList
    
    def send_notice_to_api(self, BE_url: str, noticeList: list[Notice]) -> int:
        #
        # 가져온 공지사항을 Discord BackEnd 서버로 전송
        #
        # Parameter)
        #   BE_url: Discord BackEnd 서버 URL (SpringBoot)
        #   noticeList: 수집한 공지사항 목록
        #
        # Return) Discord BackEnd로부터 수신한 Status Code (Type: INT)
        #
        try:
            response = requests.post(
                BE_url, 
                json={'data': [notice.__dict__ for notice in noticeList]}, 
                headers={'Content-Type': 'application/json'}
                )
            
            if response.status_code == 200:
                logger.info(f"Send success - status={response.status_code}")
            else:
                logger.error(f"Send failed - status={response.status_code}, body={response.text}")

            return response
        except Exception:
            logger.error("Error while sending notice API")
            logger.exception("Error while sending notice to API")
            raise


    def __parse_school_news(self, noticeCnt: int) -> list[Notice]:
        """
        학부소식 게시판 전용 파싱 함수
        카드형 레이아웃(div#prs > ul > li) 게시글 목록을 수집
        """
        noticeList = []
        pageNum = 1

        while len(noticeList) < noticeCnt:
            response = requests.get(URLs["학부소식"] + str(pageNum))
            soup = BeautifulSoup(response.text, "html.parser")

            items = soup.select("div#prs > ul > li")
            if not items:
                logger.warning(f"No school news items found on page {pageNum}")
                break

            page_added = 0

            for item in items:
                a_tag = item.select_one("a[href*='wr_id=']")
                title_tag = item.select_one("h4")

                if not a_tag or not title_tag:
                    continue

                href = a_tag.get("href")
                title = title_tag.get_text(" ", strip=True)

                if not href or not title:
                    continue

                # 링크 정규화
                if href.startswith("http"):
                    link = href
                elif href.startswith("/"):
                    link = "https://cse.knu.ac.kr" + href
                else:
                    link = "https://cse.knu.ac.kr/bbs/" + href.lstrip("./")

                # wr_id 추출
                match = re.search(r"wr_id=(\d+)", link)
                if not match:
                    continue

                num = match.group(1)

                # 중복 방지
                if any(notice.link == link for notice in noticeList):
                    continue

                try:
                    content, created_time = self.__get_content_and_created_time_of_notice(link)
                except Exception:
                    logger.error(f"Failed to fetch school news detail: {link}")
                    logger.exception(f"Failed to fetch school news detail: {link}")
                    continue

                noticeObj = Notice(
                    num=num,
                    title=title,
                    link=link,
                    category="SCHOOL_NEWS",
                    content=content,
                    created_at=created_time
                )
                noticeList.append(noticeObj)
                page_added += 1

                if len(noticeList) >= noticeCnt:
                    break

            if page_added == 0:
                logger.warning(f"No new school news collected on page {pageNum}")
                break

            pageNum += 1

        return noticeList