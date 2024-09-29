import discord
from discord import app_commands
from discord.ext import commands
import os
import asyncio
import yt_dlp
from dotenv import load_dotenv
import re

# Define the regex patterns for each type
playlist_pattern = r"https:\/\/www\.youtube\.com\/playlist\?list="
music_pattern = r"https:\/\/www\.youtube\.com\/watch\?v=[\w-]+$"
music_in_playlist_pattern = r"https:\/\/www\.youtube\.com\/watch\?v=[\w-]+&list="
remove_music_in_playlist_pattern = r"(https:\/\/www\.youtube\.com\/watch\?v=[\w-]+)&list=.*"

def run_bot():
    load_dotenv()
    TOKEN = os.getenv('DISCORD_TOKEN')
    intents = discord.Intents.default()
    intents.message_content = True
    client = commands.Bot(command_prefix='!', intents = intents)

    queues = {}
    now_playing = {}
    voice_clients = {}
    yt_dl_options = {
        "format": "bestaudio/best",
        "nocookies": True,
        "extractor-args": "youtube:player-client=web,default;player-skip=webpage,configs"
    }
    ytdl = yt_dlp.YoutubeDL(yt_dl_options)
    message_max_length = 1800

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

    @client.event
    async def on_command_error(ctx, error):
        """Handles errors raised during command execution."""
        if isinstance(error, commands.CommandNotFound):
            await error_fallback(ctx, error)
        else:
            # For other types of errors, you can log or handle them differently
            print(f"An error occurred: {error}")
            await error_fallback(ctx, error)

    async def error_fallback(ctx, error):
        if isinstance(error, commands.CommandNotFound):
            await ctx.send('Command not found. Use `!help` to see available commands.')
        else:
            # Extract the command from the message using regex
            match = re.match(r'!(\w+)', ctx.message.content)
            if match:
                invalid_command = match.group(1)
                await ctx.send(f'Your command `{invalid_command}` seems wrong. Try `!help {invalid_command}` to see details of this command or `!help` to see available commands.')
            else:
                await ctx.send('An error occurred. Please try again.')

    async def play_next(ctx):
        if queues[ctx.guild.id] != []:
            data = queues[ctx.guild.id].pop(0)
            await play(ctx, data[0], data[1])

    async def identify_youtube_link(url):
        if re.match(playlist_pattern, url):
            return "Playlist"
        elif re.match(music_in_playlist_pattern, url):
            return "Music inside Playlist"
        elif re.match(music_pattern, url):
            return "Music"
        else:
            return "Invalid YouTube link"
    
    async def clean_music_link(url):
        # Check if the link is "Music inside Playlist"
        if re.match(remove_music_in_playlist_pattern, url):
            # Remove the "&list=" part and anything after it
            cleaned_url = re.sub(r"&list=.*", "", url)
            return cleaned_url
        else:
            return url

    async def play(ctx, link, title):
        #check if no link was provided, if so, check if player is paused, if paused, resume, if not, check if any song is in the queue, if so, play the next song in the queue, if not, send "No song in queue"

        if not link or not title:
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
                print('!@#$!#!@#$@#$!#@$@#$!@#¨%@#!¨@$$!@#$!@#$!@!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
                queue(ctx, link)
                return

        except Exception as e:
            print(e)
    
        try:
            loop = asyncio.get_event_loop()
            #data = await loop.run_in_executor(None, lambda: ytdl.extract_info(link, download=False))

            #if not data:
            #    print('---------from link-------------')
                #data = await loop.run_in_executor(None, lambda: ytdl.extract_info(link, download=False))
           # else:
           #     print('---------from data param-------------')
            
            #print(data)
            #print('----------------------')
            
            #song_name = data.get('title')
            #song_url = data.get('url') or data.get('webpage_url')
            #cleaned_url = clean_music_link(link)

            player = discord.FFmpegOpusAudio(link, **ffmpeg_options)

            voice_clients[ctx.guild.id].play(player, after=lambda e: asyncio.run_coroutine_threadsafe(play_next(ctx), client.loop))

            now_playing[ctx.guild.id] = title

            #check if "play" was called from the queue command, if so, send "Now playing {song name}"
            #song_name = data['title']
            await ctx.send(f'Now playing `{title}`')

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
            #await ctx.send('Skipping ' + now_playing[ctx.guild.id])
            await ctx.send(f'Skipping current song')
            voice_clients[ctx.guild.id].stop()
            await play_next(ctx)
        except Exception as e:
            print(e)

    @client.command(name='show_queue', aliases=['sq'], help='Shows the current queue')
    async def show_queue(ctx, *, page = 1):
        if ctx.guild.id in queues:
            messages_paginated = {}
            messages_paginated[0] = ""
            current_loop_page = 0
            #if queues[ctx.guild.id]:
            #    queue = '\n'.join([f'{index + 1}. {song_name}' for index, (link, song_name) in enumerate(queues[ctx.#guild.id])])
            #    await ctx.send(f'Queue:\n{queue}')
            #refactor method above to add musics on a for loop, every loop checking for the message lenght, if it's bigger than message_max_length add it to next page
            for index, (link, song_name) in enumerate(queues[ctx.guild.id]):
                if len(messages_paginated[current_loop_page]) > message_max_length:
                    current_loop_page += 1
                    messages_paginated.append("")
                messages_paginated[current_loop_page] += f'{index + 1}. {song_name}\n'
            
            # text for total of queues to be put at the end of the message, like "Page 1 of 2"
            total_pages = len(messages_paginated)
            
            # should print messages_paginated[page-1], then the pagination
            if page > total_pages:
                await ctx.send(f'Invalid page number. Queue has {total_pages} pages.')
            else:
                await ctx.send(f'Queue (Page {page} of {total_pages}):\n{messages_paginated[page-1]}')
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

    async def get_song_info(query):
        """Extracts song information (name and URL) from a YouTube link or search query."""
        loop = asyncio.get_event_loop()
        
        # Attempt to extract info from the query as if it was a URL
        try:
            data = await loop.run_in_executor(None, lambda: ytdl.extract_info(query, download=False))
        except Exception as e:
            print(f"Error extracting info from URL: {e}")
            data = None
        
        # If the above fails, treat the query as a search term
        if not data:
            try:
                # Perform a YouTube search for the query
                search_data = await loop.run_in_executor(None, lambda: ytdl.extract_info(f"ytsearch:{query}", download=False))
                # Extract information from the first search result
                data = search_data['entries'][0] if search_data['entries'] else None
            except Exception as e:
                print(f"Error performing YouTube search: {e}")
                return None, None, None  # Return None if no data was found

        if not data:
            return None, None, None  # Return None if no data was found after both attempts
        
        # Check if it's a playlist
        if 'entries' in data:
            songs = [(entry.get('title'), entry.get('url') or entry.get('webpage_url')) for entry in data['entries']]
            return songs, None, True

        song_name = data.get('title')
        song_url = data.get('url') or data.get('webpage_url')

        return [(song_name, song_url)], song_name, False

    @client.command(name='play', aliases=['q', 'queue', 'p'], help='Plays or queues a song or playlist from a YouTube link or search query')
    async def queue(ctx, *, query):
        async with ctx.typing():
            # Initialize the queue for the guild if it doesn't exist
            if ctx.guild.id not in queues:
                queues[ctx.guild.id] = []

            # Get song name and URL from the query
            songs, song_name, is_playlist = await get_song_info(query)

            if not songs:
                await ctx.send("Couldn't find a song matching your query.")
                return

            # Add each song to the queue
            for song_name, song_url in songs:
                queues[ctx.guild.id].append((song_url, song_name))

            # If a playlist was queued, notify the user
            if is_playlist:
                await ctx.send(f'Added playlist with {len(songs)} songs to queue.')
            else:
                await ctx.send(f'Added `{song_name}` to queue')

            # Check if the bot is connected to a voice channel
            if ctx.guild.id in voice_clients and voice_clients[ctx.guild.id].is_connected():
                # If the bot is connected, check if it's currently playing something
                if not voice_clients[ctx.guild.id].is_playing():
                    await play_next(ctx)
            else:
                # If the bot is not connected, connect and start playing the first song
                #first_song_url, first_song_name = songs[0]
                await play_next(ctx)
                # Remove the first song from the queue as it's being played
                #queues[ctx.guild.id].pop(0)

    @client.command(name='queue_multiple', aliases=['qm'], help='Queue multiple songs from a list of youtube links, separated by commas')
    async def queue_multiple(ctx, *links):
        for link in links:
            await queue(ctx, link)
        await ctx.send(f'All {len(links)} songs added to queue')

    @client.command(name='now_playing', aliases=['np'], help='Shows the currently playing song')
    async def now_playing(ctx):
        if ctx.guild.id in now_playing:
            await ctx.send(f'Now playing `{now_playing[ctx.guild.id]}`')
        else:
            await ctx.send('No song is currently playing')
    
    #@client.command(name='play_temp', help='Plays a temporary sound and resumes the current song')
    async def play_temp(ctx, *, query):
        # Verifica se tem algo tocando atualmente
        if ctx.guild.id not in voice_clients or not voice_clients[ctx.guild.id].is_playing():
            await ctx.send('Nenhuma música está tocando atualmente.')
            return

        voice_client = voice_clients[ctx.guild.id]

        # Pega o ponto em que a música atual foi pausada
        original_timestamp = voice_client.timestamp  # Timestamp atual em milissegundos

        # Pausa a música atual
        voice_client.pause()
        await ctx.send(f'Música atual pausada em {original_timestamp // 1000} segundos.')

        # Baixa e toca o novo som temporário
        songs, temp_song_name, _ = await get_song_info(query)
        if not songs:
            await ctx.send("Não foi possível encontrar o som temporário solicitado.")
            return

        temp_song_url = songs[0][1]  # URL do som temporário
        player = discord.FFmpegOpusAudio(temp_song_url, **ffmpeg_options)
        
        # Toca o som temporário
        await ctx.send(f'Tocando som temporário: `{temp_song_name}`')
        voice_client.play(player, after=lambda e: asyncio.run_coroutine_threadsafe(resume_original_song(ctx, original_timestamp), client.loop))

    async def resume_original_song(ctx, original_timestamp):
        try:
            # Aguarda um pequeno delay para garantir que a música temporária terminou
            #await asyncio.sleep(1)

            voice_client = voice_clients[ctx.guild.id]
            # Se a música original ainda estiver pausada, retome-a
            if voice_client.is_paused():
                voice_client.resume()
                voice_client.seek(original_timestamp // 1000)  # Retorna para o ponto exato em segundos
                await ctx.send(f'Música original retomada de {original_timestamp // 1000} segundos.')
            else:
                await ctx.send('Erro ao retomar a música original.')
        except Exception as e:
            print(f"Erro ao retomar a música original: {e}")
            await ctx.send('Erro ao retomar a música original.2')

    client.run(TOKEN)

if __name__ == '__main__':
    run_bot()