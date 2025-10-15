# (중략... 위에 import os가 있어야 합니다.)

# 봇 실행 명령어 변경 (맨 아래):
# client.run('인터넷에 포스팅되었던 무효화된 토큰')  <-- 이 부분을 삭제해야 합니다!

# 대신 이전에 안내해 드린 환경 변수 코드를 사용합니다.
try:
    # BOT_TOKEN 환경 변수에서 토큰을 가져와 실행합니다.
    client.run(os.environ.get("BOT_TOKEN")) 
except Exception as e:
    print(f"🚨 봇 실행 중 오류 발생: {e}")
    print("환경 변수 BOT_TOKEN이 설정되었는지 확인해 주세요.")


