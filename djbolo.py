import discord
from discord import app_commands
from discord.ext import commands
import os
import asyncio
import yt_dlp
from dotenv import load_dotenv

def run_bot():
    load_dotenv()
    TOKEN = os.getenv('DISCORD_TOKEN')
    intents = discord.Intents.default()
    intents.message_content = True
    client = commands.Bot(command_prefix='!', intents = intents)

    queues = {}
    voice_clients = {}
    yt_dl_options = {"format": "bestaudio/best"}
    ytdl = yt_dlp.YoutubeDL(yt_dl_options)

    ffmpeg_options = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn -filter:a "volume=0.5"'}
    
    @client.event
    async def on_ready():
        print(f'{client.user} is now jamming!')

        try:
            synced = await client.tree.sync()
            print(f"Synced {len(synced)} commands")
        except Exception as e:
            print(f"Failed to sync commands: {e}")

        #await debug_start_bot()

    
############## DEBUG START ################

    async def debug_start_bot():
        guild_id = 1247528929397313609
        user_id = 247261012296728587
        voice_channel_id = 1247528930030780571
        text_channel_id = 1274479349403353170  # ID of the text channel where you want to send messages

        # Fetch the guild and the user
        guild = client.get_guild(guild_id)
        user = await client.fetch_user(user_id)

        if guild and user:  # Ensure both the guild and user exist
            # Get the specific voice channel in the guild
            voice_channel = guild.get_channel(voice_channel_id)
            
            if voice_channel and isinstance(voice_channel, discord.VoiceChannel):  # Ensure the voice channel exists
                try:
                    # Connect to the voice channel
                    voice_client = await voice_channel.connect()
                    voice_clients[guild.id] = voice_client  # Save the voice client

                    # Get the specific text channel to send messages
                    text_channel = guild.get_channel(text_channel_id)
                    
                    if text_channel and isinstance(text_channel, discord.TextChannel):  # Ensure the text channel exists
                        # Simulate context for the user
                        ctx = await client.get_context(await text_channel.send('Bot is starting, auto-queuing default songs...'))
                        ctx.author = user  # Set the context author to the specified user
                        
                        # List of song links to auto-queue
                        songs = [
                            "https://www.youtube.com/watch?v=HNBCVM4KbUM",
                            "https://www.youtube.com/watch?v=pAGrykAxkB4",
                            "https://www.youtube.com/watch?v=I_2D8Eo15wE",
                            "https://www.youtube.com/watch?v=mWGNEHGhkn4",
                            "https://www.youtube.com/watch?v=CiJeSSzu9Bo",
                            "https://www.youtube.com/watch?v=qFfnlYbFEiE",
                            #"https://www.youtube.com/watch?v=WcqK9Ls7Eos",
                            #"https://www.youtube.com/watch?v=CHekNnySAfM",
                            
                            # "https://www.youtube.com/watch?v=o1tj2zJ2Wvg",
                            # "https://www.youtube.com/watch?v=pAgnJDJN4VA",
                            # "https://www.youtube.com/watch?v=HQmmM_qwG4k",
                            # "https://www.youtube.com/watch?v=1QP-SIW6iKY",
                            # "https://www.youtube.com/watch?v=Rp6-wG5LLqE",
                            # "https://www.youtube.com/watch?v=hTWKbfoikeg",
                            # "https://www.youtube.com/watch?v=bKttENbsoyk",
                            # "https://www.youtube.com/watch?v=arpZ3fCwDEw",
                            # "https://www.youtube.com/watch?v=L397TWLwrUU"
                        ]

                        # Queue each song in the list
                        for song in songs:
                            await queue(ctx, song)
                        await ctx.send('Auto-queue complete!')

                    else:
                        print("Text channel not found or not a text channel.")

                except Exception as e:
                    print(f"Failed to connect to the voice channel: {e}")
            else:
                print("Voice channel not found or not a voice channel.")

################# END OF DEBUG START ####################

    async def play_next(ctx):
        if queues[ctx.guild.id] != []:
            link = queues[ctx.guild.id].pop(0)[0]
            await play(ctx, link)

    async def play(ctx, link):
        #check if no link was provided, if so, check if player is paused, if paused, resume, if not, check if any song is in the queue, if so, play the next song in the queue, if not, send "No song in queue"

        if not link:
            if ctx.guild.id in voice_clients:
                if voice_clients[ctx.guild.id].is_paused():
                    voice_clients[ctx.guild.id].resume()
                    await ctx.send('Resumed')
                elif ctx.guild.id in queues and queues[ctx.guild.id]:
                    await play_next(ctx)
                else:
                    await ctx.send('No song in queue')

        try:
            voice_client = await ctx.author.voice.channel.connect()
            
            #voice_clients[voice_client.guild.id] = voice_client
            #instead of just adding voice client to voice_clients, firstcheck if voice_client.guild.id is in voice_clients, if so, just add the song to the queue
            
            if voice_client.guild.id not in voice_clients:
                voice_clients[voice_client.guild.id] = voice_client
            else:
                queue(ctx, link)
                return

        except Exception as e:
            print(e)
    
        try:
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(None, lambda: ytdl.extract_info(link, download=False))

            song = data['url']
            player = discord.FFmpegOpusAudio(song, **ffmpeg_options)

            voice_clients[ctx.guild.id].play(player, after=lambda e: asyncio.run_coroutine_threadsafe(play_next(ctx), client.loop))

            #check if "play" was called from the queue command, if so, send "Now playing {song name}"
            song_name = data['title']
            await ctx.send(f'Now playing `{song_name}`')

        except Exception as e:
            print(e)

    @client.tree.command(name = "hi")
    async def hi(interaction: discord.Integration):
        await interaction.response.send_message(f"Hi {interaction.guild.id}!", ephemeral=True)

    @client.command(name='clear_queue', aliases=['cq', 'clear'], help='Clears the queue')
    async def clear_queue(ctx):
        if ctx.guild.id in queues:
            queues[ctx.guild.id] = []
            await ctx.send('Queue cleared')
        else:
            await ctx.send('Queue is already empty')

    @client.command(name='skip', aliases=['s'], help='Skips the current song')
    async def skip(ctx):
        try:
            voice_clients[ctx.guild.id].stop()
            await play_next(ctx)
        except Exception as e:
            print(e)

    @client.command(name='show_queue', aliases=['sq'], help='Shows the current queue')
    async def show_queue(ctx):
        if ctx.guild.id in queues:
            if queues[ctx.guild.id]:
                queue = '\n'.join([f'{index + 1}. {song_name}' for index, (link, song_name) in enumerate(queues[ctx.guild.id])])
                await ctx.send(f'Queue:\n{queue}')
            else:
                await ctx.send('Queue is empty')
        else:
            await ctx.send('Queue is empty')

    async def jump(ctx, song_number):
        try:
            song_number = int(song_number)
            if song_number < 1:
                await ctx.send('Invalid song number')
                return
        except ValueError:
            await ctx.send('Invalid song number')
            return

        if ctx.guild.id in queues:
            if 1 <= song_number <= len(queues[ctx.guild.id]):
                for _ in range(song_number-1):
                    queues[ctx.guild.id].pop(0) #refactor this later, it's not efficient to pop(0) multiple times
                voice_clients[ctx.guild.id].stop()
                await play_next(ctx)
                await ctx.send(f'Jumped to song number {song_number}')
            else:
                await ctx.send('Invalid song number')
        else:
            await ctx.send('Queue is empty')

    @client.command(name='debug', help='Debugging command')
    async def debug(ctx):
        print("--------------------")
        print(f'queues: {queues}')
        print(f'voice_clients: {voice_clients}')
    
        if ctx.guild.id in queues:
            print(f'queues[ctx.guild.id]: {queues[ctx.guild.id]}')
        else:
            print(f'queues[ctx.guild.id]: None (no queue for this guild)')
        print("--------------------")

    @client.command(name='pause', help='Pauses the current song')
    async def pause(ctx):
        try:
            voice_clients[ctx.guild.id].pause()
        except Exception as e:
            print(e)

    @client.command(name='resume', aliases=['r'], help='Resumes the current song')
    async def resume(ctx):
        try:
            voice_clients[ctx.guild.id].resume()
        except Exception as e:
            print(e)

    @client.command(name='stop', aliases=['exit', 'leave'], help='Stops the current song')
    async def stop(ctx):
        try:
            voice_clients[ctx.guild.id].stop()
            await voice_clients[ctx.guild.id].disconnect()
            del voice_clients[ctx.guild.id]
        except Exception as e:
            print(e)

    async def get_song_name(link):
        song_name = ytdl.extract_info(link, download=False)['title']
        return song_name

    @client.command(name='play', aliases=['q', 'queue', 'p'], help='Plays or queue a song from a youtube link')
    async def queue(ctx, link):
        async with ctx.typing():
            # Initialize the queue for the guild if it doesn't exist
            if ctx.guild.id not in queues:
                queues[ctx.guild.id] = []

            #queues[ctx.guild.id].append(link)
            song_name = await get_song_name(link)
            queues[ctx.guild.id].append((link, song_name))

            # Check if the bot is connected to a voice channel
            if ctx.guild.id in voice_clients and voice_clients[ctx.guild.id].is_connected():
                # If the bot is connected, check if it's currently playing something
                if not voice_clients[ctx.guild.id].is_playing():
                    await play_next(ctx)
                else:
                    await ctx.send(f'Added `{song_name}` to queue')
            else:
                # If the bot is not connected, connect and start playing the song
                await play(ctx, link)
                # After playing, remove the song from the queue to avoid duplication
                queues[ctx.guild.id].pop()

    @client.command(name='queue_multiple', aliases=['qm'], help='Queue multiple songs from a list of youtube links, separated by commas')
    async def queue_multiple(ctx, *links):
        for link in links:
            await queue(ctx, link)
            # all {number} songs added to queue
        await ctx.send(f'All {len(links)} songs added to queue')

    client.run(TOKEN)