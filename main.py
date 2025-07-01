import discord
from discord.ext import commands, tasks
import asyncio
from datetime import datetime, timedelta
import os

# 봇 설정
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.guilds = True

bot = commands.Bot(command_prefix='!', intents=intents)

# 생성된 채널들을 추적하기 위한 딕셔너리
created_channels = {}
channel_timers = {}

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
            
            # 채널 이름 생성 (생성자 이름 없이)
            channel_name = f"{limit}인방"
            
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
            
            embed = discord.Embed(
                title="🎉 통화방 생성 완료!",
                description=f"**{channel_name}** 이 생성되었습니다.\n"
                           f"📊 최대 인원: **{limit}명**\n"
                           f"⏰ 사용 후 비어있으면 자동 삭제됩니다.",
                color=0x00ff88
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            error_embed = discord.Embed(
                title="❌ 채널 생성 실패",
                description=f"오류가 발생했습니다: {str(e)}\n관리자에게 문의해주세요.",
                color=0xff0000
            )
            await interaction.response.send_message(embed=error_embed, ephemeral=True)
            print(f"채널 생성 오류: {e}")

@bot.event
async def on_ready():
    print(f'{bot.user}가 로그인했습니다!')
    bot.add_view(VoiceChannelView())
    
    try:
        synced = await bot.tree.sync()
        print(f'{len(synced)}개의 슬래시 명령어가 동기화되었습니다.')
    except Exception as e:
        print(f'명령어 동기화 실패: {e}')

@bot.event
async def on_voice_state_update(member, before, after):
    """음성 채널 상태 변경 감지"""
    
    # 사용자가 임시 통화방에 들어왔을 때
    if after.channel and after.channel.id in created_channels:
        created_channels[after.channel.id]['has_been_used'] = True
        if after.channel.id in channel_timers:
            channel_timers[after.channel.id].cancel()
            del channel_timers[after.channel.id]
    
    # 사용자가 임시 통화방을 떠났을 때
    if before.channel and before.channel.id in created_channels:
        if len(before.channel.members) == 0 and created_channels[before.channel.id]['has_been_used']:
            try:
                await before.channel.delete()
                
                if before.channel.id in created_channels:
                    del created_channels[before.channel.id]
                if before.channel.id in channel_timers:
                    channel_timers[before.channel.id].cancel()
                    del channel_timers[before.channel.id]
                
                print(f"사용 후 빈 채널 삭제됨: {before.channel.name}")
                
            except discord.NotFound:
                if before.channel.id in created_channels:
                    del created_channels[before.channel.id]
                if before.channel.id in channel_timers:
                    del channel_timers[before.channel.id]
            except Exception as e:
                print(f"채널 삭제 오류: {e}")

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
                   "🔹 **사용 후 비어있으면** 자동 삭제\n"
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
                
                embed.add_field(
                    name=f"🔊 {channel.name}",
                    value=f"생성자: {creator.display_name if creator else '알 수 없음'}\n"
                          f"현재: {member_count}/{info['limit']}명\n"
                          f"생성: {created_time}",
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

@bot.command(name="패널")
async def send_panel_text(ctx):
    if not ctx.author.guild_permissions.administrator:
        await ctx.send("❌ 관리자만 사용할 수 있는 명령어입니다.", delete_after=5)
        return
    
    embed = discord.Embed(
        title="🎙️ 통화방 생성",
        description="**아래 버튼을 클릭하여 통화방을 생성하세요!**\n\n"
                   "🔹 **1~5인** 인원제한 통화방\n"
                   "🔹 **사용 후 비어있으면** 자동 삭제\n"
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

# 봇 실행 - 환경변수에서 토큰 가져오기
if __name__ == "__main__":
    TOKEN = os.getenv('DISCORD_BOT_TOKEN')
    
    if not TOKEN:
        print("❌ DISCORD_BOT_TOKEN 환경변수가 설정되지 않았습니다!")
        print("호스팅 서비스에서 환경변수를 설정해주세요.")
    else:
        print("🚀 봇을 시작합니다...")
        bot.run(TOKEN)
