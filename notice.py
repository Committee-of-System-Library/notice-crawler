import json

# num : 공지글 번호(링크에서의 wr_id 파라미터)
# link : 공지의 링크
# title : 공지글 제목, 가끔 수정될 때 있음 → 업데이트할 때마다 확인 필요
# category : 공지글 카테고리 (전체, 일반공지, 학사, 장학, 심컴, 글솝, 대학원, 대학원 계약학과)
# content : 공지글 내용, 필요성은 아직 없으나 미리 보기 등의 추가 기능에 대비해서 미리 넣어둠
# created_at : 공지글 게시 날짜 및 시간 (YYYY-MM-DD hh:mm:00) (sec는 0초로 고정)
# saved_at : 공지글 크롤링 시간 (YYYY-MM-DD hh:mm:00) (sec는 0초로 고정)
# updated_at : 공지글 업데이트 시간 (YYYY-MM-DD hh:mm:00) (sec는 0초로 고정)
# status : (NEW, OLD, UPDATE), 공지 알림 전송 여부를 체크하기 위한 필드

class Notice:
    def __init__(self, num, link, title, category, content, created_at):
        self.num = num
        self.link = link
        self.title = title
        self.category = category
        self.content = content
        self.created_at = created_at
