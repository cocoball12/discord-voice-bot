from flask import Flask
from threading import Thread
import os
import requests
import asyncio
from datetime import datetime
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 웹 서버 (Render용) - 더 안정적으로 개선
app = Flask(__name__)

# 봇 상태 추적용 전역 변수
bot_status = {
    'last_ping': datetime.now(),
    'total_pings': 0,
    'bot_ready': False
}

@app.route('/')
def home():
    status = "🟢 온라인" if bot_status['bot_ready'] else "🟡 시작중"
    return f"""
    <h1>Discord Bot Status</h1>
    <p>상태: {status}</p>
    <p>마지막 핑: {bot_status['last_ping'].strftime('%Y-%m-%d %H:%M:%S')}</p>
    <p>총 핑 횟수: {bot_status['total_pings']}</p>
    <p>활성 채널: {len(created_channels) if 'created_channels' in globals() else 0}개</p>
    """

@app.route('/health')
def health():
    return {
        "status": "alive", 
        "timestamp": datetime.now().isoformat(),
        "bot_ready": bot_status['bot_ready'],
        "active_channels": len(created_channels) if 'created_channels' in globals() else 0
    }

@app.route('/ping')
def ping():
    bot_status['last_ping'] = datetime.now()
    bot_status['total_pings'] += 1
    return {"pong": True, "timestamp": datetime.now().isoformat()}

def run_web():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)), debug=False)

# 개선된 Keep-Alive 함수
async def keep_alive():
    """더 안정적인 keep-alive 시스템"""
    consecutive_failures = 0
    max_failures = 3
    
    while True:
        try:
            # 3분마다 ping (5분보다 짧게)
            await asyncio.sleep(180)  # 180초 = 3분
            
            # 환경변수에서 URL 가져오기
            url = os.environ.get('RENDER_EXTERNAL_URL')
            
            if url:
                # 자신의 서버에 ping
                response = requests.get(f"{url}/ping", timeout=30)
                
                if response.status_code == 200:
                    consecutive_failures = 0
                    logger.info(f"✅ Keep-alive 성공: {response.status_code} at {datetime.now()}")
                else:
                    consecutive_failures += 1
                    logger.warning(f"⚠️ Keep-alive 응답 이상: {response.status_code}")
            else:
                logger.info("🔄 RENDER_EXTERNAL_URL 미설정, 로컬 모드")
                
        except requests.exceptions.RequestException as e:
            consecutive_failures += 1
            logger.error(f"❌ Keep-alive 네트워크 오류: {e}")
            
        except Exception as e:
            consecutive_failures += 1
            logger.error(f"❌ Keep-alive 예상치 못한 오류: {e}")
        
        # 연속 실패가 많으면 더 자주 시도
        if consecutive_failures >= max_failures:
            logger.error(f"🚨 Keep-alive {consecutive_failures}회 연속 실패, 1분 후 재시도")
            await asyncio.sleep(60)  # 1분 후 재시도
        
        # 상태 업데이트
        bot_status['last_ping'] = datetime.now()

# 웹 서버를 별도 스레드에서 실행
web_thread = Thread(target=run_web, daemon=True)
web_thread.start()
logger.info("🌐 웹 서버 시작됨")

# Discord 봇 부분
import discord
from discord.ext import commands, tasks
from datetime import timedelta

# 봇 설정
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.guilds = True

bot = commands.Bot(command_prefix='!', intents=intents)

# 생성된 채널들을 추적하기 위한 딕셔너리
created_channels = {}
channel_timers = {}

async def delete_channel_after_delay(channel_id, delay=30):
    """지정된 시간 후 채널 삭제"""
    try:
        await asyncio.sleep(delay)
        
        if channel_id in created_channels:
            channel = created_channels[channel_id]['channel']
            
            # 채널이 여전히 비어있는지 확인
            if len(channel.members) == 0:
                await channel.delete()
                logger.info(f"⏰ 30초 타이머로 채널 삭제됨: {channel.name}")
                
                # 딕셔너리에서 제거
                if channel_id in created_channels:
                    del created_channels[channel_id]
                if channel_id in channel_timers:
                    del channel_timers[channel_id]
            else:
                # 채널에 사람이 있으면 타이머 제거
                if channel_id in channel_timers:
                    del channel_timers[channel_id]
                    
    except discord.NotFound:
        # 채널이 이미 삭제된 경우
        if channel_id in created_channels:
            del created_channels[channel_id]
        if channel_id in channel_timers:
            del channel_timers[channel_id]
    except Exception as e:
        logger.error(f"❌ 타이머 채널 삭제 오류: {e}")

class VoiceChannelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label='1인', style=discord.ButtonStyle.secondary, emoji='1️⃣', custom_id='voice_1')
    async def one_person(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.create_voice_channel(interaction, 1)
    
    @discord.ui.button(label='2인', style=discord.ButtonStyle.secondary, emoji='2️⃣', custom_id='voice_2')
    async def two_person(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.create_voice_channel(interaction, 2)
    
    @discord.ui.button(label='3인', style=discord.ButtonStyle.secondary, emoji='3️⃣', custom_id='voice_3')
    async def three_person(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.create_voice_channel(interaction, 3)
    
    @discord.ui.button(label='4인', style=discord.ButtonStyle.secondary, emoji='4️⃣', custom_id='voice_4')
    async def four_person(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.create_voice_channel(interaction, 4)
    
    @discord.ui.button(label='5인', style=discord.ButtonStyle.secondary, emoji='5️⃣', custom_id='voice_5')
    async def five_person(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.create_voice_channel(interaction, 5)
    
    async def create_voice_channel(self, interaction: discord.Interaction, limit: int):
        try:
            guild = interaction.guild
            user = interaction.user
            
            # 카테고리 찾기 (없으면 생성)
            category = discord.utils.get(guild.categories, name="🔊 임시 통화방")
            if not category:
                category = await guild.create_category("🔊 임시 통화방")
            
            # 채널 이름 생성
            base_name = f"{limit}인방"
            channel_name = base_name
            
            # 동일한 이름의 채널이 있는지 확인하고 번호 추가
            existing_names = [ch.name for ch in guild.voice_channels if ch.category == category]
            counter = 1
            
            while channel_name in existing_names:
                counter += 1
                channel_name = f"{base_name} #{counter}"
            
            # 음성 채널 생성
            voice_channel = await guild.create_voice_channel(
                name=channel_name,
                category=category,
                user_limit=limit
            )
            
            # 채널 권한 설정 (생성자에게 관리 권한)
            await voice_channel.set_permissions(user, manage_channels=True, move_members=True)
            
            # 생성된 채널 추적
            created_channels[voice_channel.id] = {
                'channel': voice_channel,
                'creator': user.id,
                'created_at': datetime.now(),
                'limit': limit,
                'has_been_used': False
            }
            
            # 사용자를 채널로 이동 (음성 채널에 있을 때만)
            if user.voice and user.voice.channel:
                try:
                    await user.move_to(voice_channel)
                    created_channels[voice_channel.id]['has_been_used'] = True
                except:
                    pass
            else:
                # 사용자가 음성 채널에 없으면 30초 타이머 시작
                task = asyncio.create_task(delete_channel_after_delay(voice_channel.id))
                channel_timers[voice_channel.id] = task
            
            embed = discord.Embed(
                title="🎉 통화방 생성 완료!",
                description=f"**{channel_name}** 이 생성되었습니다.\n"
                           f"📊 최대 인원: **{limit}명**\n"
                           f"⏰ 30초간 비어있으면 자동 삭제됩니다.\n"
                           f"🔗 채널: <#{voice_channel.id}>",
                color=0x00ff88
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            logger.info(f"✅ 채널 생성됨: {channel_name} by {user.display_name}")
            
        except Exception as e:
            error_embed = discord.Embed(
                title="❌ 채널 생성 실패",
                description=f"오류가 발생했습니다: {str(e)}\n관리자에게 문의해주세요.",
                color=0xff0000
            )
            await interaction.response.send_message(embed=error_embed, ephemeral=True)
            logger.error(f"❌ 채널 생성 오류: {e}")

@bot.event
async def on_ready():
    logger.info(f'🤖 {bot.user}가 로그인했습니다!')
    bot.add_view(VoiceChannelView())
    
    # 봇 상태 업데이트
    bot_status['bot_ready'] = True
    
    # Keep-alive 작업 시작
    asyncio.create_task(keep_alive())
    logger.info("🔄 Keep-alive 작업이 시작되었습니다.")
    
    try:
        synced = await bot.tree.sync()
        logger.info(f'⚡ {len(synced)}개의 슬래시 명령어가 동기화되었습니다.')
    except Exception as e:
        logger.error(f'❌ 명령어 동기화 실패: {e}')

@bot.event
async def on_voice_state_update(member, before, after):
    """음성 채널 상태 변경 감지"""
    
    # 사용자가 임시 통화방에 들어왔을 때
    if after.channel and after.channel.id in created_channels:
        created_channels[after.channel.id]['has_been_used'] = True
        
        # 기존 타이머가 있으면 취소
        if after.channel.id in channel_timers:
            channel_timers[after.channel.id].cancel()
            del channel_timers[after.channel.id]
            logger.info(f"⏹️ 채널 입장으로 타이머 취소됨: {after.channel.name}")
    
    # 사용자가 임시 통화방을 떠났을 때
    if before.channel and before.channel.id in created_channels:
        channel_info = created_channels[before.channel.id]
        
        # 채널이 완전히 비었는지 확인
        if len(before.channel.members) == 0:
            if channel_info['has_been_used']:
                # 사용된 적이 있는 채널은 즉시 삭제
                try:
                    await before.channel.delete()
                    
                    if before.channel.id in created_channels:
                        del created_channels[before.channel.id]
                    if before.channel.id in channel_timers:
                        channel_timers[before.channel.id].cancel()
                        del channel_timers[before.channel.id]
                    
                    logger.info(f"🗑️ 사용 후 빈 채널 즉시 삭제됨: {before.channel.name}")
                    
                except discord.NotFound:
                    if before.channel.id in created_channels:
                        del created_channels[before.channel.id]
                    if before.channel.id in channel_timers:
                        del channel_timers[before.channel.id]
                except Exception as e:
                    logger.error(f"❌ 채널 삭제 오류: {e}")
            else:
                # 사용된 적이 없는 채널은 30초 타이머 시작
                if before.channel.id not in channel_timers:
                    task = asyncio.create_task(delete_channel_after_delay(before.channel.id))
                    channel_timers[before.channel.id] = task
                    logger.info(f"⏰ 30초 타이머 시작됨: {before.channel.name}")

# 슬래시 명령어들
@bot.tree.command(name="패널", description="통화방 생성 패널을 현재 채널에 전송합니다. (관리자 전용)")
async def send_panel(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        embed = discord.Embed(
            title="❌ 권한 없음",
            description="이 명령어는 관리자만 사용할 수 있습니다.",
            color=0xff0000
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    embed = discord.Embed(
        title="🎙️ 통화방 생성",
        description="**아래 버튼을 클릭하여 통화방을 생성하세요!**\n\n"
                   "🔹 **1~5인** 인원제한 통화방\n"
                   "🔹 **30초간** 비어있으면 자동 삭제\n"
                   "🔹 **무제한** 통화방 생성 가능\n\n"
                   "⚡ 버튼을 클릭하면 즉시 통화방이 생성됩니다!",
        color=0x5865f2
    )
    embed.set_footer(text="🎯 원하는 인원수 버튼을 클릭하세요!")
    
    view = VoiceChannelView()
    await interaction.response.send_message(embed=embed, view=view)

@bot.tree.command(name="채널목록", description="현재 생성된 임시 통화방 목록을 확인합니다.")
async def channel_list(interaction: discord.Interaction):
    if not created_channels:
        embed = discord.Embed(
            title="📋 채널 목록",
            description="현재 생성된 임시 통화방이 없습니다.",
            color=0x888888
        )
    else:
        embed = discord.Embed(
            title="📋 현재 임시 통화방 목록",
            color=0x00ff99
        )
        
        for channel_id, info in created_channels.items():
            try:
                channel = info['channel']
                creator = bot.get_user(info['creator'])
                created_time = info['created_at'].strftime("%H:%M:%S")
                member_count = len(channel.members)
                
                # 타이머 상태 확인
                timer_status = "⏰ 타이머 작동중" if channel_id in channel_timers else "✅ 활성"
                
                embed.add_field(
                    name=f"🔊 {channel.name}",
                    value=f"생성자: {creator.display_name if creator else '알 수 없음'}\n"
                          f"현재: {member_count}/{info['limit']}명\n"
                          f"생성: {created_time}\n"
                          f"상태: {timer_status}",
                    inline=True
                )
            except:
                continue
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="내채널삭제", description="내가 만든 통화방을 삭제합니다.")
async def delete_my_channel(interaction: discord.Interaction):
    user_channels = [
        info for info in created_channels.values() 
        if info['creator'] == interaction.user.id
    ]
    
    if not user_channels:
        embed = discord.Embed(
            title="❌ 삭제할 채널 없음",
            description="삭제할 수 있는 통화방이 없습니다.",
            color=0xff6b6b
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    try:
        deleted_count = 0
        for channel_info in user_channels:
            try:
                channel = channel_info['channel']
                await channel.delete()
                
                if channel.id in created_channels:
                    del created_channels[channel.id]
                if channel.id in channel_timers:
                    channel_timers[channel.id].cancel()
                    del channel_timers[channel.id]
                deleted_count += 1
            except:
                continue
        
        embed = discord.Embed(
            title="✅ 채널 삭제 완료",
            description=f"{deleted_count}개의 통화방이 삭제되었습니다.",
            color=0x51cf66
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
    except Exception as e:
        embed = discord.Embed(
            title="❌ 삭제 실패",
            description=f"통화방 삭제 중 오류가 발생했습니다.",
            color=0xff0000
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="상태", description="봇 상태를 확인합니다.")
async def bot_status_cmd(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🤖 봇 상태",
        description=f"봇이 정상적으로 작동 중입니다!\n"
                   f"현재 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                   f"활성 채널: {len(created_channels)}개\n"
                   f"마지막 핑: {bot_status['last_ping'].strftime('%H:%M:%S')}\n"
                   f"총 핑 횟수: {bot_status['total_pings']}회",
        color=0x00ff99
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.command(name="패널")
async def send_panel_text(ctx):
    if not ctx.author.guild_permissions.administrator:
        await ctx.send("❌ 관리자만 사용할 수 있는 명령어입니다.", delete_after=5)
        return
    
    embed = discord.Embed(
        title="🎙️ 통화방 생성",
        description="**아래 버튼을 클릭하여 통화방을 생성하세요!**\n\n"
                   "🔹 **1~5인** 인원제한 통화방\n"
                   "🔹 **30초간** 비어있으면 자동 삭제\n"
                   "🔹 **무제한** 통화방 생성 가능\n\n"
                   "⚡ 버튼을 클릭하면 즉시 통화방이 생성됩니다!",
        color=0x5865f2
    )
    embed.set_footer(text="🎯 원하는 인원수 버튼을 클릭하세요!")
    
    view = VoiceChannelView()
    await ctx.send(embed=embed, view=view)
    
    try:
        await ctx.message.delete()
    except:
        pass

# 봇 실행
if __name__ == "__main__":
    TOKEN = os.getenv('DISCORD_BOT_TOKEN')
    
    if not TOKEN:
        logger.error("❌ DISCORD_BOT_TOKEN 환경변수가 설정되지 않았습니다!")
        logger.error("호스팅 서비스에서 환경변수를 설정해주세요.")
    else:
        logger.info("🚀 봇을 시작합니다...")
        try:
            bot.run(TOKEN, log_handler=None)  # 로깅 중복 방지
        except Exception as e:
            logger.error(f"❌ 봇 실행 오류: {e}")
