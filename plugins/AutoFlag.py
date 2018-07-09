import asyncio
import logging
import re

import discord
from discord.ext import commands

from WolfBot import WolfChecks
from WolfBot import WolfConfig
from WolfBot import WolfUtils
from WolfBot.WolfStatics import *

LOG = logging.getLogger("DakotaBot.Plugin." + __name__)


# noinspection PyMethodMayBeStatic
class AutoFlag:
    """
    The Auto Flag plugin allows staff members to be alerted on the use of certain key phrases.

    This command may be considered with the /autoflag command, where flags can be added and removed.
    """

    def __init__(self, bot: discord.ext.commands.Bot):
        self.bot = bot

        self._config = WolfConfig.get_config()

        self._delete_time = 30 * 60  # 30 minutes (30 x 60 seconds)
        LOG.info("Loaded plugin!")

    async def regex_message_filter(self, message: discord.Message, context: str = "new_message"):
        flag_regexes = self._config.get("flaggedRegexes", [])

        alert_channel = self._config.get('specialChannels', {}).get(ChannelKeys.STAFF_ALERTS.value, None)
        if alert_channel is not None:
            alert_channel = self.bot.get_channel(alert_channel)  # type: discord.TextChannel

        log_channel = self._config.get('specialChannels', {}).get(ChannelKeys.STAFF_LOG.value, None)
        if log_channel is not None:
            log_channel = self.bot.get_channel(alert_channel)  # type: discord.TextChannel

        if not isinstance(message.channel, discord.TextChannel):
            return

        if not WolfUtils.should_process_message(message):
            return

        if message.author.permissions_in(message.channel).manage_messages:
            return

        for flag_term in flag_regexes:
            if re.search(flag_term, message.content, re.IGNORECASE) is not None:
                embed = discord.Embed(
                    title=Emojis.RED_FLAG + " Message autoflag raised!",
                    description="A message matching term `{}` was detected and has been raised to staff. "
                                "Please investigate.".format(flag_term),
                    color=Colors.WARNING
                )

                embed.add_field(name="Message Content", value=WolfUtils.trim_string(message.content, 1000),
                                inline=False)
                embed.add_field(name="Message ID", value=message.id, inline=True)
                embed.add_field(name="Channel", value=message.channel.mention, inline=True)
                embed.add_field(name="User", value=message.author.mention, inline=True)
                embed.add_field(name="Message Timestamp", value=message.created_at.strftime(DATETIME_FORMAT),
                                inline=True)

                if alert_channel is not None:
                    await alert_channel.send(embed=embed, delete_after=self._delete_time)

                if log_channel is not None:
                    await log_channel.send(embed=embed)

                LOG.info("Got flagged message (context %s, key %s, from %s in %s): %s", context,
                         message.author, flag_term, message.channel, message.content)

    async def user_filter(self, message: discord.Message):
        flag_users = self._config.get("flaggedUsers", [])

        alert_channel = self._config.get('specialChannels', {}).get(ChannelKeys.STAFF_ALERTS.value, None)
        if alert_channel is not None:
            alert_channel = self.bot.get_channel(alert_channel)  # type: discord.TextChannel

        if not WolfUtils.should_process_message(message):
            return

        if message.author.id in flag_users:
            embed = discord.Embed(
                title=Emojis.RED_FLAG + " Message autoflag raised!",
                description="A message from flagged user {} was detected and has been raised to staff. "
                            "Please investigate.".format(message.author.mention),
                color=Colors.WARNING
            )

            embed.add_field(name="Message Content", value=WolfUtils.trim_string(message.content, 1000), inline=False)
            embed.add_field(name="Message ID", value=message.id, inline=True)
            embed.add_field(name="Channel", value=message.channel.mention, inline=True)
            embed.add_field(name="User ID", value=message.author.id, inline=True)
            embed.add_field(name="Message Timestamp", value=message.created_at.strftime(DATETIME_FORMAT),
                            inline=True)

            if alert_channel is not None:
                await alert_channel.send(embed=embed, delete_after=self._delete_time)

            LOG.info("Got user flagged message (from %s in %s): %s", message.author, message.channel, message.content)

    async def on_message(self, message):
        asyncio.ensure_future(self.regex_message_filter(message))
        asyncio.ensure_future(self.user_filter(message))

    # noinspection PyUnusedLocal
    async def on_message_edit(self, before, after):
        await self.regex_message_filter(after, "edit")

    @commands.group(name="autoflag", brief="Manage the autoflag plugin")
    @WolfChecks.has_guild_permissions(manage_messages=True)
    async def autoflag(self, ctx: commands.Context):
        """
        Parent command for the AutoFlag plugin.

        This command inherently does nothing, and only exists to support the child commands, listed below.
        """
        pass

    @autoflag.command(name="add", brief="Add a new regex to the autoflag config")
    async def add(self, ctx: commands.Context, *, regex: str):
        """
        Add a regex to the autoflag list.

        This command takes a single argument - a regular expression. It will attempt to add the specified regular
        expression to the autoflag list. Note that this command will not take action against the message, but inform
        a staff member only.

        If the regex already exists in the autoflag list, it will be ignored.
        """

        flag_regexes = self._config.get("flaggedRegexes", [])  # type: list

        if regex in flag_regexes:
            await ctx.send(embed=discord.Embed(
                title="Autoflag Plugin",
                description="The regex `" + regex + "` is already autoflagged.",
                color=Colors.WARNING
            ))
            return

        flag_regexes.append(regex)

        self._config.set('flaggedRegexes', flag_regexes)

        await ctx.send(embed=discord.Embed(
            title="Autoflag Plugin",
            description="The regex `" + regex + "` has been added to the autoflag list.",
            color=Colors.SUCCESS
        ))

    @autoflag.command(name="remove", brief="Remove a regex from the autoflag config")
    async def remove(self, ctx: commands.Context, *, regex: str):
        """
        Remove a regex from the autoflag list.

        This command takes a single argument - a regular expression. It will attempt to remove the specified regex from
        the autoflag list. If it doesn't exist, this command will raise an exception.
        """

        flag_regexes = self._config.get("flaggedRegexes", [])  # type: list

        if regex not in flag_regexes:
            await ctx.send(embed=discord.Embed(
                title="Autoflag Plugin",
                description="The regex `" + regex + "` is already not autoflagged.",
                color=Colors.WARNING
            ))
            return

        flag_regexes.remove(regex)

        self._config.set('flaggedRegexes', flag_regexes)

        await ctx.send(embed=discord.Embed(
            title="Autoflag Plugin",
            description="The regex `" + regex + "` has been removed from the autoflag list.",
            color=Colors.SUCCESS
        ))

    @autoflag.command(name="list", brief="List all regexes in the autoflag config")
    async def list(self, ctx: commands.Context):
        """
        List all defined autoflags registered with the bot.

        This command will attempt to return a separated list of all known regexes that the bot has registered in the
        autoflag database. All regexes in this list will generate a staff alert.
        """

        flag_regexes = self._config.get("flaggedRegexes", [])

        sep = '`\n- `'

        fr = sep.join(flag_regexes)

        await ctx.send(embed=discord.Embed(
            title="Autoflag Plugin",
            description="The following regexes are autoflagged:\n- `{}`".format(fr),
            color=Colors.INFO
        ))

    @autoflag.command(name="useradd", brief="Add a flag for any message from a user", aliases=["uadd"])
    async def useradd(self, ctx: commands.Context, user: discord.Member):
        flag_users = self._config.get("flaggedUsers", [])

        if user.id in flag_users:
            await ctx.send(embed=discord.Embed(
                title="Autoflag Plugin",
                description="The user {} is already autoflagged.".format(user),
                color=Colors.WARNING
            ))
            return

        flag_users.append(user.id)

        self._config.set('flaggedUsers', flag_users)

        await ctx.send(embed=discord.Embed(
            title="Autoflag Plugin",
            description="The user `{}` has been added to the autoflag list.".format(user),
            color=Colors.SUCCESS
        ))

    @autoflag.command(name="userremove", brief="Add a flag for any message from a user", aliases=["uremove"])
    async def userremove(self, ctx: commands.Context, user: discord.Member):
        flag_users = self._config.get("flaggedUsers", [])

        if user.id not in flag_users:
            await ctx.send(embed=discord.Embed(
                title="Autoflag Plugin",
                description="The user {} is not autoflagged.".format(user),
                color=Colors.WARNING
            ))
            return

        flag_users.remove(user.id)

        self._config.set('flaggedUsers', flag_users)

        await ctx.send(embed=discord.Embed(
            title="Autoflag Plugin",
            description="The user `{}` has been removed from the autoflag list.".format(user),
            color=Colors.SUCCESS
        ))

    @autoflag.command(name="userlist", brief="List all regexes in the autoflag config", aliases=["ulist"])
    async def userlist(self, ctx: commands.Context):
        """
        List all defined autoflags registered with the bot.

        This command will attempt to return a separated list of all known regexes that the bot has registered in the
        autoflag database. All regexes in this list will generate a staff alert.
        """

        flag_users = self._config.get("flaggedUsers", [])

        sep = '`\n- `'

        fr = sep.join(map(str, flag_users))

        await ctx.send(embed=discord.Embed(
            title="Autoflag Plugin",
            description="The following user IDs are autoflagged:\n- `{}`".format(fr),
            color=Colors.INFO
        ))


def setup(bot: discord.ext.commands.Bot):
    bot.add_cog(AutoFlag(bot))
