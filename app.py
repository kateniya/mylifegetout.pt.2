import copy
import html
import io
import json
import time
from datetime import datetime
from urllib.parse import urlparse

import qrcode
import streamlit as st
from core import KST, STAGES, make_code, metrics, new_record, now, validate_record
from storage import Store

st.set_page_config(page_title='숨 · 나의 금연 동행', page_icon='🌿', layout='centered')
st.markdown('''<style>
#MainMenu,footer {visibility:hidden}
.block-container {max-width:820px;padding-top:2rem;padding-bottom:8rem}
.hero {background:linear-gradient(135deg,#0a5c53,#087f73);color:white;padding:30px 26px;border-radius:24px;margin:12px 0 22px}
.hero h1 {color:white;font-size:2.3rem;margin:8px 0}
.hero p {color:#d5eee8;line-height:1.8}
.eyebrow {font-size:12px;letter-spacing:2px;font-weight:700}
.card {background:white;border:1px solid #dce9e4;border-radius:18px;padding:20px;margin:10px 0;color:#183b35}
.subtle {color:#526f68;font-size:14px}
div[data-testid="stMetric"] {background:white;border:1px solid #dce9e4;border-radius:16px;padding:16px}
div.st-key-bottom_nav {position:fixed;bottom:0;left:50%;transform:translateX(-50%);width:min(100%,820px);z-index:999;background:#f5f8f7;padding:12px 12px 20px;border-top:1px solid #ccdfd6;box-shadow:0 -6px 25px #183b3510}
div.st-key-bottom_nav [data-testid="stSegmentedControl"] {width:100%}
div.st-key-bottom_nav [data-testid="stSegmentedControl"] button {flex:1;min-height:46px;font-size:13px}
@media(max-width:500px){.block-container{padding-left:14px;padding-right:14px}.hero h1{font-size:1.9rem}div.st-key-bottom_nav{padding:8px 4px 18px}div.st-key-bottom_nav button{padding:5px!important;font-size:12px!important}}
</style>''', unsafe_allow_html=True)

def secret_value(key, default=''):
    try:
        return st.secrets.get(key, default)
    except Exception:
        return default

@st.cache_resource
def get_store():
    return Store(secret_value('SUPABASE_URL'), secret_value('SUPABASE_SERVICE_ROLE_KEY'))

try:
    store = get_store()
except Exception:
    st.error('저장소 설정에 문제가 있습니다. Secrets의 URL·키와 DB 테이블을 확인해 주세요.')
    st.stop()

for k, v in {'record': new_record(), 'user': None, 'nav': '홈', 'saved_code': None,
             'failed': 0, 'lock_until': 0, 'breath_until': 0}.items():
    if k not in st.session_state:
        st.session_state[k] = v
S = st.session_state

def save(record):
    try:
        if S.user:
            store.save(S.user['id'], record)
        S.record = record
        return True
    except Exception:
        st.error('저장하지 못했습니다. 입력은 아직 반영되지 않았습니다. 잠시 후 다시 시도하세요.')
        return False

def card(title, text):
    st.markdown(f'<div class="card"><b>{html.escape(title)}</b><p>{html.escape(text)}</p></div>', unsafe_allow_html=True)

def goto(page):
    S.nav = page

st.markdown('**🌿 숨**　 ·　나의 금연 동행')
if not store.cloud:
    st.caption('로컬 체험 저장소 · 공개 배포 전 Supabase 연결 필수 (재배포 시 로컬 기록이 사라질 수 있습니다).')

page = S.nav or '홈'
if page == '홈':
    st.markdown('<div class="hero"><div class="eyebrow">BREATHE BETTER, DAY BY DAY</div><h1>오늘의 한 번이,<br>내일의 숨을 바꿔요.</h1><p>완벽하지 않아도 괜찮아요.<br>지금 이 순간부터, 나의 속도로 금연을 시작해요.</p></div>', unsafe_allow_html=True)
    st.button('나의 금연 기록 보기 →', type='primary', use_container_width=True, on_click=goto, args=('기록',))
    c1,c2 = st.columns(2)
    with c1:
        card('⏱ 한눈에 보는 변화', '금연 시간, 피우지 않은 담배, 절약한 금액을 기록해요.')
    with c2:
        card('🌱 함께 만드는 습관', '흡연 욕구가 생길 때 작은 행동부터 실천해요.')
    st.info('가입은 선택이에요. 손님은 바로 사용하고, 회원은 로그인 코드로 다른 기기에서도 기록을 불러와요.')
    st.button('지금 흡연 욕구가 생겼어요', use_container_width=True, on_click=goto, args=('실천',))
    card('오늘의 한 문장', '한 번의 실수로 모든 노력이 사라지지 않아요. 다시 시작할 수 있어요.')

elif page == '기록':
    st.title('나의 금연 기록')
    st.caption('금연 시작 시각 기준 · 한국 표준시(KST)')
    @st.fragment(run_every='1s')
    def live_metrics():
        m = metrics(S.record)
        st.markdown(f'<div class="hero"><div class="eyebrow">SMOKE-FREE TIME</div><h1>{m["days"]}일 {m["hours"]:02d}:{m["minutes"]:02d}:{m["seconds_part"]:02d}</h1><p>지금도 쌓이고 있는 나의 노력</p></div>', unsafe_allow_html=True)
        a,b = st.columns(2)
        a.metric('피우지 않은 담배 · 추정', f'{m["count"]:,.1f}개비')
        b.metric('절약한 금액 · 추정', f'₩{m["money"]:,.0f}')
        target = (m['days']//7+1)*7
        st.progress(min(1., m['seconds']/(target*86400)), text=f'다음 목표 {target}일 · {max(0,target-m["days"])}일 남았어요')
        st.caption('입력한 하루 흡연량과 갑당 가격을 기준으로 시간에 비례해 계산합니다. 실제 절약액과 다를 수 있습니다.')
    live_metrics()
    st.write('**나의 금연 이유**')
    st.write(S.record['goal'])
    with st.expander('금연 시작일·시간 및 흡연 정보 수정', expanded=False):
        start = datetime.fromisoformat(S.record['start']).astimezone(KST)
        with st.form('settings'):
            date = st.date_input('금연 시작 날짜', value=start.date(), max_value=now().date())
            clock = st.time_input('금연 시작 시각 (시:분)', value=start.time().replace(tzinfo=None, second=0, microsecond=0), step=60)
            seconds_input = st.number_input('금연 시작 초', 0, 59, start.second)
            daily = st.number_input('금연 전 하루 흡연량 (개비)', 0, 200, int(S.record['daily']))
            price = st.number_input('담배 한 갑 가격 (원)', 0, 100000, int(S.record['pack_price']), step=100)
            count = st.number_input('한 갑의 개비 수', 1, 100, int(S.record['pack_count']))
            goal = st.text_input('금연 이유', value=S.record['goal'], max_chars=200)
            if st.form_submit_button('변경 내용 저장', type='primary'):
                r = copy.deepcopy(S.record)
                r.update(start=datetime.combine(date,clock.replace(second=int(seconds_input)),tzinfo=KST).isoformat(), daily=daily, pack_price=price, pack_count=count, goal=goal)
                try:
                    r = validate_record(r)
                    if save(r): st.rerun()
                except ValueError as e: st.error(str(e))
    st.caption('초기 시작 시각은 앱을 처음 연 시간입니다. 실제 금연 시작 시각으로 수정해 주세요.')
    st.subheader('오늘의 마음 기록')
    with st.form('diary', clear_on_submit=True):
        mood = st.selectbox('지금 기분은 어떤가요?', ['😊 편안해요','💪 할 수 있어요','😣 참기 어려워요','🌱 다시 시작해요'])
        note = st.text_area('어떤 상황이었나요?', max_chars=500, placeholder='예: 점심 뒤 담배 대신 산책을 했어요.')
        if st.form_submit_button('마음 기록 저장'):
            r = copy.deepcopy(S.record)
            r['logs'].append({'at':now().isoformat(), 'mood':mood, 'note':note})
            r['logs'] = r['logs'][-2000:]
            if save(r): st.success('오늘의 노력을 기록했어요.')
    for log in reversed(S.record['logs'][-20:]):
        card(f'{datetime.fromisoformat(log["at"]).astimezone(KST):%m.%d %H:%M} · {log["mood"]}', log['note'])

elif page == '실천':
    st.title('욕구는 지나가고, 나는 남아요')
    st.write('한 가지씩, 지금 할 수 있는 행동을 골라 보세요.')
    @st.fragment(run_every='1s')
    def breathe():
        if st.button('🌬 60초 호흡 시작 / 다시 시작', use_container_width=True):
            S.breath_until = time.time()+60
        remaining = max(0, int(S.breath_until-time.time()))
        if remaining:
            phase = (60-remaining)%10
            st.info(f'{remaining}초 남음 · '+('편안하게 들이마셔요 (4초)' if phase<4 else '천천히 내쉬어요 (6초)'))
            st.progress((60-remaining)/60)
        elif S.breath_until:
            st.success('잘했어요. 물 한 잔을 마시며 마음을 확인해 보세요.')
        st.caption('어지럽거나 불편하면 멈추고 평소대로 호흡하세요.')
    breathe()
    st.subheader('나를 돕는 작은 행동들')
    st.caption('아래 카드 영역 안에서 위아래로 스크롤해 보세요.')
    tips = [('01 · 잠깐 미루기','지금 당장 피우는 대신 5분만 기다려 보세요. 짧은 시간을 버티는 데 집중해요.'),
            ('02 · 물 천천히 마시기','물 한 잔을 천천히 마시며 담배 생각에서 잠시 벗어나 보세요.'),
            ('03 · 자리 바꾸기','흡연하던 장소를 벗어나 가볍게 걷거나 스트레칭을 해 보세요.'),
            ('04 · 손과 입에 다른 일 주기','무설탕 껌이나 작은 공, 펜으로 손과 입의 습관을 바꿔 보세요.'),
            ('05 · 나의 유발 상황 찾기','식후, 스트레스, 친구의 권유 등 담배 생각이 나는 상황을 일지에 적어 보세요.'),
            ('06 · 주변에 도움 요청하기','믿을 수 있는 친구·가족·보건교사에게 금연 중이라고 알려 주세요.'),
            ('07 · 흡연 도구 정리하기','담배와 라이터, 재떨이 등 눈에 띄는 흡연 단서를 치워 보세요.'),
            ('08 · 다시 시작하기','한 번 피웠어도 포기하지 마세요. 어떤 상황이었는지 살피고 시작 시각을 다시 정할 수 있어요.'),
            ('09 · 전문가와 상의하기','금단 증상이 힘들다면 보건소나 의료진에게 도움을 요청하세요. 청소년의 니코틴 대체제·약물 사용은 전문가와 상담하세요.')]
    with st.container(height=410, border=True):
        for title, text in tips:
            card(title,text)
    st.button('마음 일지 쓰러 가기 →', use_container_width=True, on_click=goto, args=('기록',))

elif page == '건강':
    st.title('내 몸의 회복 여정')
    st.warning('아래 내용은 일반적인 건강 정보입니다. 실제 몸 상태를 측정하거나 회복 완료를 판정하지 않습니다. 개인차가 있으며, 금연 후에도 검진과 진료는 필요합니다.')
    sec = metrics(S.record)['seconds']
    for threshold, label, detail in STAGES:
        reached = sec >= threshold
        card(('🌿 참고 기간 도달 · ' if reached else '○ 앞으로의 변화 · ')+label, detail)
    st.caption('1개월=30일, 1년=365일로 단순 환산합니다. 범위의 시작 시점 도달 여부만 표시하며 건강 회복률(%)은 표시하지 않습니다.')
    st.link_button('건강 정보 출처 · 미국 CDC', 'https://www.cdc.gov/tobacco/about/benefits-of-quitting.html', use_container_width=True)
    st.info('가슴 통증이나 심한 호흡곤란 등 급성 증상이 있다면 앱을 보며 기다리지 말고 즉시 응급 도움을 받으세요.')

elif page == '내정보':
    st.title('나의 공간')
    if S.user:
        st.success(f'{S.user["name"]}님, 오늘도 함께해요.')
        st.caption(f'{S.user["school"]} · {S.user["student_no"]}')
        st.caption('브라우저를 닫으면 자동 로그인은 유지되지 않습니다. 재접속 시 로그인 코드를 입력하세요.')
        if st.button('로그아웃', use_container_width=True):
            S.user=None; S.record=new_record(); S.saved_code=None
            st.rerun()
        with st.expander('회원 탈퇴 · 저장 기록 삭제'):
            confirm=st.checkbox('계정과 저장된 기록을 영구 삭제합니다.')
            if st.button('계정 영구 삭제', disabled=not confirm):
                try:
                    store.delete(S.user['id'])
                    S.user=None; S.record=new_record(); S.saved_code=None
                    st.rerun()
                except Exception: st.error('삭제하지 못했습니다. 연결 상태를 확인해 주세요.')
    else:
        st.info('현재 손님으로 이용 중이에요. 가입하지 않아도 모든 금연 기능을 사용할 수 있어요.')
        st.caption('손님 기록은 현재 접속 세션에만 남습니다. 나가기 전에 아래에서 백업하거나 가입해 주세요.')
        tab1,tab2=st.tabs(['다시 로그인','선택 회원가입'])
        with tab1:
            with st.form('login'):
                code=st.text_input('가입 시 받은 로그인 코드',type='password',max_chars=80)
                submitted=st.form_submit_button('로그인',type='primary')
            if submitted:
                if time.time()<S.lock_until:
                    st.error('반복 시도가 감지되었습니다. 1분 후 다시 시도해 주세요.')
                else:
                    try:
                        user=store.login(code)
                        if user:
                            record=validate_record(user['record'])
                            S.user=user; S.record=record; S.failed=0; S.saved_code=None
                            st.rerun()
                        else:
                            S.failed+=1
                            if S.failed>=5: S.lock_until=time.time()+60; S.failed=0
                            st.error('로그인 코드를 다시 확인해 주세요.')
                    except Exception: st.error('로그인하지 못했습니다. 저장소 설정과 연결을 확인해 주세요.')
            st.caption('이름·학번만으로는 다른 사람이 로그인할 수 있어 무작위 비밀 코드를 사용합니다. 코드를 잃어버리면 이 앱에서는 계정 복구가 불가능합니다.')
        with tab2:
            st.caption('학교·학번·이름만 입력합니다. 비밀번호 입력 대신 비밀 로그인 코드를 자동 발급합니다. 현재 손님 기록도 함께 저장됩니다.')
            with st.form('signup'):
                school=st.text_input('학교',max_chars=80)
                student=st.text_input('학번',max_chars=30)
                name=st.text_input('이름',max_chars=40)
                consent=st.checkbox('학교·학번·이름과 금연 기록을 계정 유지 및 기록 저장 목적으로 저장하는 데 동의합니다. 탈퇴 시 삭제됩니다.')
                register=st.form_submit_button('선택 회원가입',type='primary')
            if register:
                if not all(x.strip() for x in [school,student,name]):
                    st.error('학교·학번·이름을 모두 입력해 주세요.')
                elif not consent: st.error('저장 동의가 필요합니다. 동의하지 않으면 손님으로 이용해 주세요.')
                else:
                    try:
                        secret=make_code()
                        S.user=store.create(school.strip(),student.strip(),name.strip(),secret,S.record)
                        S.saved_code=secret
                        st.rerun()
                    except Exception: st.error('가입 정보를 저장하지 못했습니다. DB 설정·연결을 확인해 주세요.')
    if S.saved_code:
        st.warning('로그인 코드는 이번 가입 세션에서만 표시합니다. 반드시 별도로 보관하고 다른 사람에게 공유하지 마세요.')
        st.code(S.saved_code,language=None)
        st.download_button('로그인 코드 보관 파일 다운로드', '숨 로그인 코드: '+S.saved_code+'\n다른 사람에게 공유하지 마세요. 분실 시 복구할 수 없습니다.',file_name='soom-login-code.txt')
    st.divider()
    st.subheader('내 기록 백업 / 복원')
    st.download_button('금연 기록 JSON 내려받기', json.dumps(S.record,ensure_ascii=False,indent=2), 'soom-record.json','application/json',use_container_width=True)
    st.caption('백업에는 금연 시각·흡연 정보·일지가 포함됩니다. 학교·학번·이름과 로그인 코드는 포함하지 않습니다.')
    uploaded=st.file_uploader('이전에 저장한 기록 불러오기',type=['json'])
    replace=st.checkbox('불러온 기록으로 현재 기록을 교체하는 데 동의합니다.')
    if st.button('백업 복원',disabled=not(uploaded and replace)):
        try:
            if uploaded.size>2_000_000: raise ValueError('2MB 이하 파일만 가능합니다.')
            record=validate_record(json.loads(uploaded.getvalue()))
            if save(record): st.success('기록을 복원했어요.')
        except (ValueError,KeyError,TypeError,OverflowError): st.error('유효한 숨 기록 파일이 아닙니다. 내용과 날짜를 확인해 주세요.')
    st.divider()
    st.subheader('QR로 앱 열기')
    st.caption('공개 배포된 HTTPS 주소를 입력하세요. QR에는 앱 주소만 담고 로그인 정보는 담지 않습니다.')
    app_url=st.text_input('배포된 앱 URL', value=secret_value('APP_URL'), placeholder='https://나의앱.streamlit.app')
    parsed=urlparse(app_url.strip())
    if app_url and parsed.scheme=='https' and parsed.hostname and not parsed.username and not parsed.password and not parsed.query and not parsed.fragment:
        buf=io.BytesIO(); qrcode.make(app_url.strip()).save(buf,format='PNG')
        st.image(buf.getvalue(),width=220)
        st.download_button('접속 QR 이미지 다운로드',buf.getvalue(),'soom-qr.png','image/png')
        st.link_button('앱 주소 열기',app_url.strip())
    elif app_url: st.warning('로그인 정보·쿼리·앵커가 없는 올바른 HTTPS 앱 주소를 입력하세요.')
    st.caption('독립 설치형 앱이 아닌 모바일 웹앱입니다. 휴대폰 브라우저의 홈 화면 추가 기능으로 빠르게 접근할 수 있습니다.')

with st.container(key='bottom_nav'):
    st.segmented_control('화면 이동', ['홈','기록','실천','건강','내정보'],key='nav', selection_mode='single',label_visibility='collapsed',width='stretch')
