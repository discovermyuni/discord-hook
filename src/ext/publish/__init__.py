from .extension import Publish


async def setup(bot):
    await bot.add_cog(Publish(bot))
