import discord
from discord import app_commands
from discord.ext import commands

from configurable_cog import ConfigurableCog
from database import get_async_session

from .data import clear_source_key
from .data import delete_guild_publishing_channel
from .data import get_all_source_keys
from .data import get_guild_publishing_channel
from .data import get_source_key
from .data import set_guild_publishing_channel
from .data import set_source_key

default_settings = {"publish_url": "https://example.com/publish"}


async def _publish(self, url: str, content: str, source_key: str | None = None):
    print("Publishing content to URL:", url)
    print("Content:", content)
    print("source_key:", source_key)


class Publish(ConfigurableCog):
    def __init__(self, bot, **kwargs):
        super().__init__(bot, "publish", default_settings, **kwargs)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not message.guild:
            return

        print(f"Received message in guild {message.guild.id} from {message.author.name}: {message.content}")

        async with get_async_session() as session:
            channel_id = await get_guild_publishing_channel(session, message.guild.id)
            print(f"Publishing channel ID for guild {message.guild.id}: {channel_id}")
            if channel_id and message.channel.id == channel_id:
                print(f"Publishing message in channel {message.channel.id}")
                source_key = await get_source_key(session, guild_id=message.guild.id, user_id=message.author.id)
                await _publish(self, self.settings.publish_url, message.content, source_key)

    @app_commands.command()
    @app_commands.default_permissions(administrator=True)
    async def publish(self, interaction: discord.Interaction, message_id: str):
        """Manually publish a message using its link."""
        message = await interaction.channel.fetch_message(message_id)

        async with get_async_session() as session:
            content = message.content
            source_key = await get_source_key(session, guild_id=interaction.guild_id)
            await _publish(self, self.settings.publish_url, content, source_key)

    @app_commands.command(name="manage-auto-publishing")
    @app_commands.default_permissions(administrator=True)
    @app_commands.choices(
        choices=[
            app_commands.Choice(name="Set Channel", value="set"),
            app_commands.Choice(name="Reset Channel", value="reset"),
        ],
    )
    async def manage_auto_publishing(
        self,
        interaction: discord.Interaction,
        choices: app_commands.Choice[str],
        channel: discord.TextChannel | None,
    ):
        """Configure your server's auto-publishing (if enabled by root)."""
        async with get_async_session() as session:
            if choices.value == "set":
                if not channel:
                    await interaction.response.send_message(
                        "Please specify a channel to set for auto-publishing.",
                        ephemeral=True,
                    )
                    return
                await set_guild_publishing_channel(session, interaction.guild_id, channel.id)
                await interaction.response.send_message(
                    f"Auto-publishing channel set to {channel.mention}.",
                    ephemeral=True,
                )

            elif choices.value == "reset":
                await delete_guild_publishing_channel(session, interaction.guild_id)
                await interaction.response.send_message(
                    "Auto-publishing channel reset.",
                    ephemeral=True,
                )

            else:
                await interaction.response.send_message("Invalid choice.", ephemeral=True)

    @commands.command(name="manage-guilds")
    @commands.is_owner()
    async def manage_guilds(
        self,
        ctx: commands.Context,
        action: str,
        guild_id: str,
        source_key: str | None = None,
        user_id: str | None = None,
    ):
        """Manage root source keys."""
        action_list = ["list", "set", "user", "clear"]
        try:
            guild_id = int(guild_id)
            user_id = int(user_id) if user_id else None
        except ValueError:
            await ctx.send("Invalid guild or user ID. Please provide valid integers.")
            return

        async with get_async_session() as session:
            if action == "list":
                if guild_id == -1:  # -1 is a special case for listing all source keys
                    source_keys = await get_all_source_keys(session)
                else:
                    source_keys = await get_all_source_keys(session, guild_id)
                await ctx.send(f"Source keys: {', '.join(map(str, source_keys))}")

            elif action == "set":
                if not source_key:
                    await ctx.send("Please provide a source key to set.")
                    return
                await set_source_key(session, guild_id, source_key)
                await ctx.send(f"Added source key {source_key} for guild {guild_id}.")

            elif action == "clear":
                await clear_source_key(session, guild_id, user_id)
                if user_id:
                    await ctx.send(f"Cleared source key for user {user_id} in guild {guild_id}.")
                else:
                    await ctx.send(f"Cleared source key for guild {guild_id}.")

            elif action == "user":
                if not source_key or not user_id:
                    await ctx.send("Please provide a source key and user ID to set.")
                    return
                await set_source_key(session, guild_id, source_key, user_id)
                await ctx.send(f"Added source key {source_key} for guild {guild_id} and user {user_id}.")

            else:
                await ctx.send(f"Invalid action. Use {', '.join(action_list[:-1])} or {action_list[-1]}.")
