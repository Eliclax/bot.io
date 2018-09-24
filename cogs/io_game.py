import importlib
import inspect
import io
import re

import discord

from discord.ext import commands

from config.io_game import rounds
from .util.checks import is_developer
from .util.parser import parse

firstOrDefault = lambda self, x=None: self[0] if self else x
first = lambda self, func, default=None: firstOrDefault((*filter(func, self),), default)


class IO_Game:
    SUBMISSION_CHANNEL = 471641874025676801

    def __init__(self, bot):
        self.bot = bot

        """
        STATUS:
        string userid | string round | string inputs | string outputs | string guesses | int delta_score | string message

        SOLVED:
        string userid | string round

        QUEUE:
        string m_c_id | string msg_id | string author_id | string channel_id | string ans | string round
        """

        self.setup_db()

    # DATABASE
    def setup_db(self):
        cursor = self.bot.database.cursor()
        if 1+1==1:
            cursor.execute("DROP TABLE IF EXISTS status")
            cursor.execute("DROP TABLE IF EXISTS solved")
            cursor.execute("DROP TABLE IF EXISTS queue")
            cursor.execute("DROP TABLE IF EXISTS mark")
        cursor.execute("""CREATE TABLE IF NOT EXISTS status
                          (userid str, round str, inputs str, outputs str,
                           guesses str, delta_score int, message str,
                           statusKEY INTEGER PRIMARY KEY AUTOINCREMENT)""")
        cursor.execute("""CREATE TABLE IF NOT EXISTS solved
                          (userid str, round str,
                          solvedKEY INTEGER PRIMARY KEY AUTOINCREMENT)""")
        cursor.execute("""CREATE TABLE IF NOT EXISTS queue
                          (m_c_id str, msg_id str, author_id str,
                           channel_id str, ans str, round str,
                           queueKEY INTEGER PRIMARY KEY AUTOINCREMENT)""")
        cursor.execute("""CREATE TABLE IF NOT EXISTS mark
                          (userid str, msg_id str, statuskey str, verdict str,
                          markKEY INTEGER PRIMARY KEY AUTOINCREMENT)""")
        cursor.close()
        self.bot.database.commit()

    def log_status(self, userid, round, inputs, outputs, guesses, delta_score, message=''):
        cursor = self.bot.database.cursor()
        cursor.execute("""INSERT into status (userid, round, inputs, outputs, guesses, delta_score, message)
        	VALUES ($1, $2, $3, $4, $5, $6, $7);""", (userid, round, repr(inputs),
            repr(outputs), repr(guesses), delta_score, message))
        cursor.close()
        self.bot.database.commit()

    def get_status(self, userid, round):
        cursor = self.bot.database.cursor()
        cursor.execute("""SELECT * FROM status WHERE userid=$1 AND round=$2""",
            (userid, round))
        rtn = [
            (eval(i[2]), eval(i[3]), eval(i[4]), i[5], i[6], i[7])
            for i in cursor.fetchall()
        ]
        cursor.close()

        return rtn

    def get_status_from_key(self, key):
        cursor = self.bot.database.cursor()
        rtn = cursor.execute("""SELECT * FROM status WHERE statusKEY=$1""", (key)).fetchone()
        return rtn
        cursor.close()

    def log_mark(self, userid, msg_id, statuskey, verdict=''):
    	cursor = self.bot.database.cursor()
    	cursor.execute("""INSERT INTO mark (userid, msg_id, statuskey, verdict)
    		VALUES ($1, $2, $3, $4);""", userid, msg_id, status)
    	cursor.close()
    	self.bot.database.commit()

    #def log_verdict(self, key, message=''):
    #    cursor = self.bot.database.cursor()
    #    cursor.execute("""UPDATE status SET message=$1 WHERE statusKEY=$2""", (message, key))
    #    cursor.close()

    def record_solved(self, userid, round):
        cursor = self.bot.database.cursor()
        cursor.execute("""INSERT into solved (userid, round) VALUES
            ($1, $2);""", (userid, round))
        cursor.close()
        self.bot.database.commit()

    def get_solved(self, round):
        cursor = self.bot.database.cursor()
        cursor.execute("""SELECT userid FROM status WHERE round=$1""", (round,))
        rtn = list(set(int(i[0]) for i in cursor.fetchall()))
        cursor.close()
        return rtn

    def sub_queue_push(self, ctx, answer, msg, round):
        cursor = self.bot.database.cursor()
        cursor.execute("""INSERT into queue (m_c_id, msg_id, author_id, channel_id, ans, round) VALUES
            ($1, $2, $3, $4, $5, $6);""", (msg.channel.id, msg.id, ctx.author.id, ctx.channel.id, answer, round))
        cursor.close()
        self.bot.database.commit()

    def check_sub_queue(self, mid):
        cursor = self.bot.database.cursor()
        cursor.execute("""SELECT * FROM queue WHERE msg_id=$1""", (mid,))
        rtn = cursor.fetchone()
        cursor.close()
        return rtn

    def get_score(self, userid, round_name, status=None):
        if status is None:
            status = self.get_status(userid, round_name)
        score = 0
        for i in status:
            if i[3] == -2:
                break
            if i[3] > 0:
                score += i[3]
        return score

    # DISCORD
    def format_prompt(self, query, response, n='-'):
        return f'```py\n IN[{n}]: {query}\nOUT[{n}]: {response}```'

    @commands.command()
    async def history(self, ctx, round_name: str, range1: int, range2: int):
        """View your history for a given round between two given query numbers."""
        if ctx.guild is not None:
            await ctx.message.delete()
            return await ctx.send('This command only works in DMs. Try DMing me that again.')

        if round_name not in rounds:
            return await ctx.send('Unknown round name')

        status = self.get_status(ctx.author.id, round_name)
        score = self.get_score(ctx.author.id, round_name, status)

        doc = rounds[round_name].__doc__.strip()
        func = rounds[round_name].__name__
        name = doc.split('\n')[0].strip()

        sig = doc.split('Sig:', 1)[1].split('\n')[0].strip()

        sig = f'{sig} | {score}'

        msg = f'{name}\n'
        msg += '-' * max(len(name), len(sig))
        msg += f'\n{sig}\n'
        msg += '=' * max(len(name), len(sig))
        msg += '\n\n'

        low = min(range1, range2)
        high = max(range1, range2)

        low = 0 if low < 0 else low
        high = len(status) if high+1 > len(status) else high+1 

        n = len([i for i in range(0, low) if not status[i][4]])
        excess = len([i for i in range(low, high) if status[i][4]])
        _high = len(status) if high+excess+1 > len(status) else high+excess+1

        for i in range(low, _high):
            if status[i][4]:
                msg += f':: {status[i][4]}\n'
            else:
                msg += f' IN[{n}]: {func}({", ".join(map(str, status[i][0]))})'
                if status[i][2] is not None:
                    msg += f' = ({", ".join(map(str, status[i][2]))})'
                msg += '\n'
                msg += f'OUT[{n}]: {", ".join(map(str, status[i][1]))}\n'
                n += 1

        await ctx.send(f'```py\n{msg}```')

    @commands.command(aliases=['q'])
    async def query(self, ctx, *, query: str):
        """Test a query. View full help for details.

        For a basic query, use `round(arguments, arguments)`.
        To take a guess, use `round(arguments, arguments) = output, output`.
        A successful guess doesn't count to your score, but an incorrect guess counts double.
        """
        if ctx.guild is not None:
            await ctx.message.delete()
            return await ctx.send('This command only works in DMs. Try DMing me that again.')

        success, response = parse(query)

        if not success:
            return await ctx.send(self.format_prompt(query, response))

        round, params, guess = response

        if round not in rounds:
            return await ctx.send(self.format_prompt(query, 'Unknown round name'))

        sig = inspect.signature(rounds[round])
        if len(sig.parameters) != len(params):
            return await ctx.send(self.format_prompt(query, 'Unexpected number of arguments to function'))

        try:
            out = rounds[round](*params)
        except Exception as e:
            return await ctx.send(self.format_prompt(query, f'Exception in function: {e}'))

        if not isinstance(out, (tuple, list)):
            out = (out,)

        if guess is not None:
            if len(guess) != len(out):
                return await ctx.send(self.format_prompt(query, 'Unexpected number of return values from function'))

            if tuple(guess) == tuple(out):
                op = 'Correct'
                delta_score = 0
            else:
                op = 'Incorrect'
                delta_score = 2
        else:
            op = out[0] if len(out) == 1 and isinstance(out, tuple) else out
            delta_score = 1

        self.log_status(ctx.author.id, round, params, out, guess, delta_score)

        status = self.get_status(ctx.author.id, round)
        score = self.get_score(ctx.author.id, round, status)

        n = len([i for i in status if not i[4]])

        logmsg = f'{status[-1][5]} | {ctx.message.id} | {ctx.author.id} as {ctx.author.name}'
        logmsg += f' | [{n}]: {round}{params} = {out} | +{delta_score} => {score}'
        logmsg += '' if guess is None else f' | guess = {guess}'

        self.bot.logger.info(logmsg)
        
        await ctx.send(self.format_prompt(query, op, n-1))

    @commands.command()
    async def submit(self, ctx, round_name: str, *, answer):
        """Submit an answer for a given round.
        You will be notified by the bot when a host has checked your answer."""
        if ctx.guild is not None:
            await ctx.message.delete()
            return await ctx.send('This command only works in DMs. Try DMing me that again.')

        if round_name not in rounds:
            return await ctx.send(self.format_prompt(query, 'Unknown round name'))

        doc = rounds[round_name].__doc__
        ans = first(doc.split('\n'), lambda x: x.strip().startswith('Solution:'), 'Solution: No clue')
        ans = ans.strip().split('Solution:', 1)[1].strip()

        chan = self.bot.get_channel(self.SUBMISSION_CHANNEL)

        q = await chan.send(f'Sumbmissions from {ctx.author.mention}: **{answer}**\nCorrect solution: **{ans}**')
        self.sub_queue_push(ctx, answer, q, round_name)
        await q.add_reaction('✅')
        await q.add_reaction('❌')

        self.log_status(ctx.author.id, round_name, None, None, None, 1, f'Submitted {answer}')
        await ctx.send('Answer recorded. Please wait for a host to review it.')

    #@commands.command(aliases=['m'])
    #@is_developer()
    #async def mark(self, ctx, submission_key, verdict: str):
    #    x = 2

    @commands.command()
    async def rounds(self, ctx):
        """List all currently active rounds."""
        rounds_str = ''
        for i in rounds:
            rounds_str += f'\n - `{i}`'
        return await ctx.send(f'**Currently active rounds:**' + rounds_str)

    @commands.command(aliases=['show', 'details'])
    async def info(self, ctx, round_name: str):
        """Get details for a given round."""
        if round_name not in rounds:
            return await ctx.send('Unknown round name')

        doc = rounds[round_name].__doc__.strip()
        title = doc.split('\n')[0]
        details = '\n'.join(map(str.strip, doc.split('\n\n')[0].split('\n')[1:]))

        sig = first(doc.split('\n'), lambda x: x.strip().startswith('Sig:'))
        sig = sig.strip() if sig is not None else sig

        diff = first(doc.split('\n'), lambda x: x.strip().startswith('Difficulty:'))
        diff = diff.strip() if diff is not None else diff

        details = f'_{details}_\n' if details else ''
        return await ctx.send(f'**{title}**\n{details}\n{sig}\n{diff}')

    @commands.command(aliases=['log'])
    @is_developer()
    async def proxy(self, ctx, userid: int, *, command: str):
        """Run a command as a specified user."""
        if ctx.guild is not None:
            ctx.message.author = ctx.guild.get_memeber(userid)
        else:
            ctx.message.author = self.bot.get_user(userid)

        if ctx.message.author is None:
            return await ctx.send('Unable to locate user')

        if command.startswith(ctx.prefix):
            ctx.message.content = command
        else:
            ctx.message.content = ctx.prefix + command

        await ctx.bot.process_commands(ctx.message)

    @commands.command()
    @is_developer()
    async def who_solved(self, ctx, round_name: str):
        solved = self.get_solved(round_name)
        msg = '**Users who have solved round:**'
        if not solved:
            msg += '\nNone yet!'
        else:
            for i in solved:
                msg += f'\n<@{i}>'
        await ctx.send(msg)

    @commands.command()
    @is_developer()
    async def reload_rounds(self, ctx):
        """Reload the rounds config files."""
        global rounds
        import config.io_game
        importlib.reload(config.io_game)
        rounds = config.io_game.rounds
        await ctx.send(f'Reloaded {len(rounds)} rounds.')

    async def on_reaction_add(self, reaction, user):
        if user.bot:
            return

        check = self.check_sub_queue(reaction.message.id)

        if check is not None:
            msg = await self.bot.get_channel(int(check[0])).get_message(int(check[1]))
            chan = self.bot.get_channel(int(check[3]))

            if reaction.emoji == '✅':
                if check[2] not in self.get_solved(check[5]):
                    self.record_solved(check[2], check[5])
                mark = 'correct'
                await chan.send(f'Your submission of {check[4]} was correct. '\
                    f'Your score was **{self.get_score(check[2], check[5])}**.')
                score = -1
            else:
                mark = 'incorrect'
                await chan.send(f'Your submission of {check[4]} was incorrect.')
                score = 0

            self.log_status(check[2], check[5], None, None, None, score, f'Answer {check[4]} {mark}.')
            await msg.edit(content=f'**Marked as {mark}.**\n~~' + msg.content + '~~')


def setup(bot):
    bot.add_cog(IO_Game(bot))
