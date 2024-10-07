#!/usr/bin/env python3
#
# Copyright (c) 2024-present toru173 and contributors
#
# Redistribution and use in source and binary forms, with or without 
# modification, are permitted (subject to the limitations in the disclaimer 
# below) provided that the following conditions are met:
#
# * Redistributions of source code must retain the above copyright notice, 
#   this list of conditions and the following disclaimer.
# * Redistributions in binary form must reproduce the above copyright notice, 
#   this list of conditions and the following disclaimer in the documentation 
#   and/or other materials provided with the distribution.
# * Neither the name of the copyright holder nor the names of the contributors
#   may be used to endorse or promote products derived from this software
#   without specific prior written permission.
#
# NO EXPRESS OR IMPLIED LICENSES TO ANY PARTY'S PATENT RIGHTS ARE GRANTED BY 
# THIS LICENSE. THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND 
# CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT 
# NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A 
# PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER 
# OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, 
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, 
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; 
# OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, 
# WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR 
# OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF 
# ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from __future__ import annotations
import os
import re

import discord
from nomi import Session, Nomi

def trim_string(input_string: str, max_length: int = 600) -> str:
    did_trim = False
    if len(input_string) <= max_length:
        return did_trim, input_string

    did_trim = True
    trimmed_string = input_string[:max_length]
    last_space = trimmed_string.rfind(' ')

    if last_space != -1:
        trimmed_string = trimmed_string[:last_space]

    return did_trim, trimmed_string

class NomiClient(discord.Client):

    _message_prefix = "*You receive a message from {author} on Discord* "
    _message_suffix = "... (the message is longer, but was cut off)"

    # =========================================================================
    # =============================== IMPORTANT ===============================
    # =========================================================================
    # === Change the number below to '400' if you are a user on a free tier ===
    # =========================================================================
    _max_message_length = 600
    _max_message_length = _max_message_length - len(_message_suffix)

    def __init__(self, *args, **kwargs) -> None:
        if nomi in kwargs and type(nomi) is not Nomi:
            raise TypeError(f"Expected nomi to be a Nomi, got a {type(nomi)}")
        
        self._nomi = nomi
        super().__init__(*args, **kwargs)     

    async def on_message(self, discord_message):
        # we do not want the Nomi to reply to themselves
        if discord_message.author.id == self.user.id:
            return

        # Check if the Nomi is mentioned in the message
        if self.user in discord_message.mentions:

            for user in discord_message.mentions:
                # Get the nickname if available, otherwise use the username
                try:
                    name = user.nick if user.nick else user.name
                except AttributeError:
                    name = user.name
                mention_text = f"<@{user.id}>"

                # Replace the mention with the nickname
                discord_message_content = discord_message.content.replace(mention_text, name)

            # Build the message to send to the Nomi
            nomi_message = self._message_prefix.format(author = discord_message.author,
                                                       channel = discord_message.channel,
                                                       guild = discord_message.guild)
            
            nomi_message = nomi_message + discord_message_content

            did_trim, nomi_message = trim_string(nomi_message, max_length = self._max_message_length)

            if did_trim:
                nomi_message = nomi_message + self._message_suffix

            try:
                # Attempt to send message
                _, reply = self._nomi.send_message(nomi_message)
                nomi_reply = reply.text
            except RuntimeError as e:
                # If there's an error, use that as the reply
                nomi_reply = f"❌ ERROR ❌\n{str(e)}"

            # Attempt to substitute user ID in any mentions
            # Example: Replace plain-text @username with the proper mention
            #          format: <@userid>
            # Use a regular expression to find words that start with @
            pattern = r"@(\w+)"
            matches = re.findall(pattern, nomi_reply)

            if matches:
                # Determine if the message is in a DM or a guild
                if discord_message.guild:
                    # If it's a guild, use the guild's member list
                    member_search = lambda name: discord.utils.find(
                        lambda m: m.name.lower() == name.lower() or (m.nick and m.nick.lower() == name.lower()),
                        discord_message.guild.members
                    )
                else:
                    # If it's a DM, use the Nomi's user cache
                    member_search = lambda name: discord.utils.find(
                        lambda u: u.name.lower() == name.lower(),
                        self.users
                    )

                for username in matches:
                    user = member_search(username)
                    if user:
                        mention = f"<@{user.id}>"
                        # Replace @username with the proper mention
                        nomi_reply = nomi_reply.replace(f"@{username}", mention)

            await discord_message.channel.send(nomi_reply)  

if __name__ == "__main__":
    # Read environment variables
    nomi_api_key = os.environ.get('NOMI_API_KEY')
    nomi_id = os.environ.get('NOMI_ID')
    discord_bot_token = os.environ.get('DISCORD_BOT_TOKEN')

    if nomi_api_key is None:
        print("NOMI_API_KEY not found in the .env file")
        exit(1)

    if nomi_id is None:
        print("NOMI_ID not found in the .env file")
        exit(1)

    if discord_bot_token is None:
        print("DISCORD_BOT_TOKEN not found in the .env file")
        exit(1)

    nomi_session = Session(api_key = nomi_api_key)
    nomi = Nomi.from_uuid(session = nomi_session, uuid = nomi_id)        

    intents = discord.Intents.default()
    intents.messages = True
    intents.members = True

    client = NomiClient(nomi = nomi, intents = intents)
    client.run(discord_bot_token)