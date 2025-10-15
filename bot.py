import discord
from discord.ext import commands, tasks
import requests 
from bs4 import BeautifulSoup
import os # <-- os 모듈 추가: 환경 변수를 읽기 위해 필요

# --- [1. 설정 변수] ---
# Koyeb 환경 변수에서 ID를 가져옵니다. (환경 변수 이름: CHANNEL_ID)
try:
    # 환경 변수에서 가져온 문자열을 정수로 변환합니다.
    NOTIFICATION_CHANNEL_ID = int(os.environ.get("CHANNEL_ID")) 
except (TypeError, ValueError):
    print("경고: 환경 변수 CHANNEL_ID가 설정되지 않았거나 올바르지 않은 값입니다. 기본값으로 설정합니다.")
    # 환경 변수가 없을 경우 임시로 기본값을 사용합니다. (배포 시에는 반드시 설정해야 함)
    NOTIFICATION_CHANNEL_ID = 123456789012345678 # 임시 채널 ID

# 크롤링할 네이버 카페 게시판 URL (PC 주소 사용)
CAFE_URL = "https://cafe.naver.com/ArticleList.naver?search.clubid=27131930&search.menuid=1"

# LAST_POST_URL은 봇이 처음 시작할 때 초기화됩니다.
LAST_POST_URL = "" 
# ---------------------

# 봇 설정
intents = discord.Intents.default()
intents.message_content = True
client = commands.Bot(command_prefix='!', intents=intents)

# --- [2. 크롤링 함수 (생략...)] ---
def get_latest_naver_post_bs4(cafe_url):
    # (이 부분은 이전 코드와 동일합니다. 그대로 유지합니다.)
    # requests와 BeautifulSoup을 사용하여 네이버 PC 페이지의 정적 HTML을 분석하는 함수
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(cafe_url, headers=headers, timeout=10)
        response.raise_for_status() 
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        iframe = soup.find('iframe', {'id': 'cafe_main'})
        
        if not iframe:
            latest_article_link = soup.select_one('.board-list .inner_list a.article')
            if latest_article_link:
                 link_path = latest_article_link.get('href')
                 link = f"https://cafe.naver.com{link_path}" if link_path.startswith('/ArticleRead.naver') else link_path
                 print("게시글 찾기 성공! (BeautifulSoup 사용 - iframe 우회)")
                 return {"title": latest_article_link.text.strip(), "link": link}
            
            print("🚨 PC 페이지에서 'cafe_main' iframe 및 게시글을 찾을 수 없습니다.")
            return None

        iframe_src = iframe.get('src')
        iframe_url = f"https://cafe.naver.com{iframe_src}" if not iframe_src.startswith('http') else iframe_src

        iframe_response = requests.get(iframe_url, headers=headers, timeout=10)
        iframe_response.raise_for_status()
        
        iframe_soup = BeautifulSoup(iframe_response.text, 'html.parser')
        
        latest_article_link = iframe_soup.select_one('.article') 
        
        if latest_article_link:
            title = latest_article_link.text.strip()
            link_path = latest_article_link.get('href')
            link = f"https://cafe.naver.com{link_path}" if link_path.startswith('/ArticleRead.naver') else link_path
            
            print(f"게시글 찾기 성공! (BeautifulSoup 사용 - PC iframe 분석)") 
            return {"title": title, "link": link}
        
        else:
            print("🚨 게시글 목록을 찾을 수 없습니다. (iframe 내부 HTML에 게시글 정보가 없습니다.)")
            return None
            
    except Exception as e:
        print(f"🚨 크롤링 중 오류 발생: {e}")
        return None

# --- [3. 봇 루프 및 이벤트 (생략...)] ---
@tasks.loop(seconds=60)
async def check_naver_cafe():
    global LAST_POST_URL
    
    channel = client.get_channel(NOTIFICATION_CHANNEL_ID)
    if not channel:
        print(f"경고: 채널 ID({NOTIFICATION_CHANNEL_ID})를 찾을 수 없습니다.")
        return

    latest_post = get_latest_naver_post_bs4(CAFE_URL)
    
    if latest_post:
        current_url = latest_post['link']
        
        if LAST_POST_URL == "":
            print(f"초기 글 저장 완료: {current_url}")
            LAST_POST_URL = current_url
            
        elif current_url != LAST_POST_URL:
            # 새 글 발견!
            print(f"새 글 발견 및 알림 전송: {latest_post['title']}")
            
            embed = discord.Embed(
                title=f"🔔 [NEW] 새로운 공지입니다!",
                description=f"**[{latest_post['title']}]**",
                color=discord.Color.from_rgb(255, 69, 0)
            )
            embed.add_field(name="바로가기", value=f"[게시글 링크]({latest_post['link']})", inline=False)
            embed.set_footer(text="자동 알림 봇 | 1분마다 확인 (BeautifulSoup PC)")
            
            await channel.send(f"새로운 공지가 올라왔어요! <#{NOTIFICATION_CHANNEL_ID}>", embed=embed)
            
            LAST_POST_URL = current_url


@client.event
async def on_ready():
    print(f'로그인 성공! 봇 이름: {client.user}')
    if not check_naver_cafe.is_running():
        check_naver_cafe.start()
        print("네이버 카페 확인 태스크가 시작되었습니다. (60초 간격 - BeautifulSoup PC)")


@client.command(name="확인", help="현재 크롤링 설정 및 마지막 확인 글을 보여줍니다.")
async def check_status_command(ctx):
    global LAST_POST_URL
    
    status_embed = discord.Embed(
        title="🔍 네이버 카페 크롤러 상태 (BeautifulSoup PC)",
        description="봇이 주기적으로 확인하고 있는 **크롤링 설정 정보**입니다.",
        color=discord.Color.blue()
    )
    
    status_embed.add_field(
        name="크롤링 대상 URL",
        value=f"```\n{CAFE_URL}\n```",
        inline=False
    )
    
    status_embed.add_field(
        name="마지막 확인된 글",
        value=f"[바로가기]({LAST_POST_URL})" if LAST_POST_URL else "아직 확인된 글이 없습니다.",
        inline=False
    )
    
    status_embed.add_field(
        name="알림 채널",
        value=f"<#{NOTIFICATION_CHANNEL_ID}>",
        inline=True
    )
    status_embed.add_field(
        name="확인 주기",
        value="60초",
        inline=True
    )
    
    status_embed.set_footer(text=f"상태 확인 시간: {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M:%S')} (UTC)")
    
    await ctx.send(embed=status_embed)

# 봇 실행 명령어: 환경 변수에서 토큰을 가져와 실행합니다.
# 주의: os.environ.get("BOT_TOKEN")은 Koyeb의 환경 변수 이름과 정확히 일치해야 합니다.
try:
    client.run(os.environ.get("BOT_TOKEN")) 
except Exception as e:
    print(f"🚨 봇 실행 중 오류 발생: {e}")
    print("MTQyNjE5NjA3OTQyNjQwODQ4OQ.Gwnc-j.Nc_JVvEyzKbEsJcb51FBaIn1SltTvlbfrHEbRE")

