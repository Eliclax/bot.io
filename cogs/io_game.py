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
		if 1+1==2:
			cursor.execute("DROP TABLE IF EXISTS status")
			cursor.execute("DROP TABLE IF EXISTS solved")
			cursor.execute("DROP TABLE IF EXISTS queue")
			cursor.execute("DROP TABLE IF EXISTS mark")
		cursor.execute("""CREATE TABLE IF NOT EXISTS status
						  (userid str, round str, inputs str, outputs str,
						   guesses str, delta_score int, message str,
						   statusKEY INTEGER PRIMARY KEY AUTOINCREMENT, verdict_to str)""")
		cursor.execute("""CREATE TABLE IF NOT EXISTS solved
						  (userid str, round str,
						  solvedKEY INTEGER PRIMARY KEY AUTOINCREMENT, status_key int)""")
		cursor.execute("""CREATE TABLE IF NOT EXISTS queue
						  (m_c_id str, msg_id str, author_id str,
						   channel_id str, ans str, round str,
						   queueKEY INTEGER PRIMARY KEY AUTOINCREMENT, status_key int)""")
		cursor.execute("""CREATE TABLE IF NOT EXISTS mark
						  (userid str, msg_id str, status_key int, verdict str,
						  markKEY INTEGER PRIMARY KEY AUTOINCREMENT)""")
		cursor.close()
		self.bot.database.commit()

	def log_status(self, userid, round, inputs, outputs, guesses, delta_score, message, verdict_to):
		cursor = self.bot.database.cursor()
		cursor.execute("""INSERT into status (userid, round, inputs, outputs, guesses, delta_score, message, verdict_to)
			VALUES ($1, $2, $3, $4, $5, $6, $7, $8);""", (userid, round, repr(inputs),
			repr(outputs), repr(guesses), delta_score, message, verdict_to))

	def get_status(self, userid, round):
		cursor = self.bot.database.cursor()
		cursor.execute("""SELECT * FROM status WHERE userid=$1 AND round=$2;""",
			(userid, round))
		rtn = [
			(eval(i[2]), eval(i[3]), eval(i[4]), i[5], i[6], i[7], i[8])
			for i in cursor.fetchall()
		]
		cursor.close()
		return rtn

	'''def get_status_full(self, userid, round):
		cursor = self.bot.database.cursor()
		rtn = cursor.execute("""SELECT * FROM status WHERE userid=$1 AND round=$2;""",(userid, round)).fetchall()
		cursor.close()
		return rtn'''

	def get_status_from_key(self, key):
		cursor = self.bot.database.cursor()
		rtn = cursor.execute("""SELECT * FROM status WHERE statusKEY=$1;""", (key,)).fetchone()
		cursor.close()
		return rtn

	def update_delta_score(self, key, score):
		cursor = self.bot.database.cursor()
		rtn = cursor.execute("""UPDATE status SET delta_score=$1 WHERE statusKEY=$2;""", (score, key)).fetchone()
		cursor.close()
		return rtn

	def log_mark(self, userid, msg_id, status_key, verdict=''):
		cursor = self.bot.database.cursor()
		cursor.execute("""INSERT INTO mark (userid, msg_id, status_key, verdict)
			VALUES ($1, $2, $3, $4);""", userid, msg_id, status)
		cursor.close()
		self.bot.database.commit()

	def find_verdict_to(self, submission_key):
		cursor = self.bot.database.cursor()
		rtn = cursor.execute("""SELECT COUNT(verdict_to) FROM status WHERE verdict_to=$1;""", (submission_key,)).fetchone()
		return rtn
		cursor.close()

	def record_solved(self, userid, round, status_key):
		cursor = self.bot.database.cursor()
		cursor.execute("""INSERT into solved (userid, round, status_key) VALUES
			($1, $2, $3);""", (userid, round, status_key))
		cursor.close()
		self.bot.database.commit()

	'''def get_solved(self, round):
		cursor = self.bot.database.cursor()
		cursor.execute("""SELECT userid FROM status WHERE round=$1;""", (round,))
		rtn = list(set(int(i[0]) for i in cursor.fetchall()))
		cursor.close()
		return rtnhello'''

	def is_solved(self, userid, round):
		cursor = self.bot.database.cursor()
		rtn = cursor.execute("""SELECT COUNT(*) FROM solved WHERE userid=$1 AND round=$2;""", (userid, round)).fetchone()[0]
		cursor.close()
		return rtn

	def get_solved(self, userid, round):
		cursor = self.bot.database.cursor()
		rtn = cursor.execute("""SELECT status_key FROM solved WHERE userid=$1 AND round=$2;""", (userid, round)).fetchone()[0]
		cursor.close()
		return rtn

	def sub_queue_push(self, ctx, answer, msg, round, status_key):
		cursor = self.bot.database.cursor()
		cursor.execute("""INSERT into queue (m_c_id, msg_id, author_id, channel_id, ans, round, status_key) VALUES
			($1, $2, $3, $4, $5, $6, $7);""", (msg.channel.id, msg.id, ctx.author.id, ctx.channel.id, answer, round, status_key))
		cursor.close()
		self.bot.database.commit()

	def get_queue_from_key(self, key):
		cursor = self.bot.database.cursor()
		cursor.execute("""SELECT * FROM queue WHERE status_key=$1;""", (key,))
		rtn = cursor.fetchone()
		cursor.close()
		return rtn

	def check_sub_queue(self, mid):
		cursor = self.bot.database.cursor()
		cursor.execute("""SELECT * FROM queue WHERE msg_id=$1;""", (mid,))
		rtn = cursor.fetchone()
		cursor.close()
		return rtn

	def rows_in_status(self):
		cursor = self.bot.database.cursor()
		return cursor.execute("""SELECT COUNT(*) FROM status;""").fetchone()[0]
		cursor.close()






	# MISC
	def times(self, number):
		if number == 1:
			return 'once'
		elif number == 2:
			return 'twice'
		else:
			msg = str(number[0])+' times'
			return msg

	def get_score(self, userid, round_name, status=None):
		check = self.is_solved(userid, round_name)
		self.bot.logger.info(check)
		if check != 0:
			key_of_solve = self.get_solved(userid, round_name) + 1  # Primary key is 1-indexed, not 0-indexed wew
			self.bot.logger.info(key_of_solve)
			if status is None:
				status = self.get_status(userid, round_name)
			score = 0
			for i in status:
				self.bot.logger.info(str(i)+'|'+str(i[5]))
				if i[3] == -2 or i[5] >= key_of_solve:
					break
				elif i[3] > -2:
					score += i[3]
			return score

		if status is None:
			status = self.get_status(userid, round_name)
		score = 0
		for i in status:
				if i[3] == -2:
					break
				if i[3] > -2:
					score += i[3]
		return score

	'''def ordinal(self, number):
		if number == 1:
			return 'first'
		elif number == 2:
			return 'second'
		elif number == 3:
			return 'third'
		else:
			return str(number[0])+'th'''





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

		status = self.get_status(ctx.author.id, round)
		score = self.get_score(ctx.author.id, round, status)
		max_key = self.rows_in_status()  # We would need to minus 1 but logging occurs ~10 lines later

		n = len([i for i in status if not i[4]])

		logmsg = f'{max_key} | {ctx.message.id} | {ctx.author.id} as {ctx.author.name}'
		logmsg += f' | [{n}]: {round}{params} = {out} | +{delta_score} => {score}'
		logmsg += '' if guess is None else f' | guess = {guess}'

		self.bot.logger.info(logmsg)

		self.log_status(ctx.author.id, round, params, out, guess, delta_score, '', -1)
		
		await ctx.send(self.format_prompt(query, op, n-1))

	@commands.command(aliases=['s'])
	async def submit(self, ctx, round_name: str, *, answer):
		"""Submit an answer for a given round.
		You will be notified by the bot when a host has checked your answer."""
		if ctx.guild is not None:
			await ctx.message.delete()
			return await ctx.send('This command only works in DMs. Try DMing me that again.')

		if round_name not in rounds:
			return await ctx.send(self.format_prompt(round_name, 'Unknown round name'))

		if self.is_solved(ctx.author.id, round_name) != 0:
			return await ctx.send('You\'ve already solved this problem.')
			#return self.stats_on_solve(ctx.author.id, round_name)

		doc = rounds[round_name].__doc__
		ans = first(doc.split('\n'), lambda x: x.strip().startswith('Solution:'), 'Solution: No clue')
		ans = ans.strip().split('Solution:', 1)[1].strip()

		chan = self.bot.get_channel(self.SUBMISSION_CHANNEL)
		status = self.get_status(ctx.author.id, round_name)
		score = self.get_score(ctx.author.id, round_name, status)
		max_key = self.rows_in_status()  # We would need to minus 1 but logging occurs ~10 lines later

		logmsg = f'{max_key} | {ctx.message.id} | {ctx.author.id} as {ctx.author.name}'
		logmsg += f' | {round_name} is {answer} | +1 => {score}'

		self.bot.logger.info(logmsg)

		q = await chan.send(f'**{max_key}** | {ctx.author.mention} submitted: **{answer}**\nCorrect solution: **{ans}**')
		self.sub_queue_push(ctx, answer, q, round_name, max_key)
		#await q.add_reaction('✅')
		#await q.add_reaction('❌')

		self.log_status(ctx.author.id, round_name, None, None, None, 1, f'Submitted {answer}', -1)
		await ctx.send('Answer recorded. Please wait for a host to review it.')

	@commands.command(aliases=['m'])
	@is_developer()
	async def mark(self, ctx, submission_key, verdict: str):
		"""Mark a submission"""

		precheck = self.find_verdict_to(submission_key)

		if precheck[0] != 0:
			return await ctx.send(f'Already marked {self.times(precheck)}. Use `overwrite_mark` to edit verdict.')

		verdicts = ['correct', 'incorrect', 'obfuscated']
		if verdict not in verdicts:
			return await ctx.send('Invalid verdict.')

		check = self.get_queue_from_key(submission_key)

		msg = await self.bot.get_channel(int(check[0])).get_message(int(check[1]))
		chan = self.bot.get_channel(int(check[3]))

		if verdict == 'correct':
			self.record_solved(check[2], check[5], check[7])
			#self.update_delta_score(submission_key+1, 0)   # Primary key is 1-indexed
			await chan.send(f'''Your submission of **{check[4]}** is correct!
			Final score: **{self.get_score(check[2], check[5])}**.''')
			score = -1
		elif verdict == 'incorrect':
			await chan.send(f'Your submission of **{check[4]}** is incorrect.')
			score = 0
		else:
			await chan.send(f'Your submission of **{check[4]}** is obfuscated, you troll! XD')
			score = 0


		key = self.rows_in_status() # We would need to minus 1 but logging occurs next line.
		self.log_status(check[2], check[5], None, None, None, score, f'Submission {check[4]} {verdict}.', submission_key)
		await msg.edit(content=f'~~' + msg.content + f'~~\n**{key} | Marked as {verdict}.**')

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

	'''@commands.command()
	@is_developer()
	async def who_solved(self, ctx, round_name: str):
		solved = self.get_solved(round_name)
		msg = '**Users who have solved round:**'
		if not solved:
			msg += '\nNone yet!'
		else:
			for i in solved:
				msg += f'\n<@{i}>'
		await ctx.send(msg)'''

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
					self.record_solved(check[2], check[5], check[7])
				mark = 'correct'
				await chan.send(f'Your submission of {check[4]} was correct. '\
					f'Your score was **{self.get_score(check[2], check[5])}**.')
				score = -1
			else:
				mark = 'incorrect'
				await chan.send(f'Your submission of {check[4]} was incorrect.')
				score = 0

			self.log_status(check[2], check[5], None, None, None, score, f'Answer {check[4]} {mark}.', check[7])
			await msg.edit(content=f'**Marked as {mark}.**\n~~' + msg.content + '~~')


def setup(bot):
	bot.add_cog(IO_Game(bot))
