import discord
import regex
import sqlite3

conn = sqlite3.connect('records.db')

loggingchannel = 471641874025676801

tony = 138589210604077056
milo = 186553034439000064
staffrole = 471641277365092353
staff = {tony}
iofns = {}

with conn:
	cur = conn.cursor()
	if 1+1 == 1:
		cur.execute("DROP TABLE querydata")
		cur.execute("DROP TABLE querymsgdata")
		cur.execute("DROP TABLE userproblemdata")
		cur.execute("DROP TABLE markingdata")
		cur.execute("DROP TABLE markingmsgdata")
		cur.execute("DROP TABLE problemdata")
		cur.execute("DROP TABLE setdata")
		cur.execute("DROP TABLE problemsetdata")
		cur.execute("DROP TABLE userdata")
		cur.execute("DROP TABLE solutiondata")
	cur.execute("""CREATE TABLE IF NOT EXISTS querydata 		(QueryDataID INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT, QuerierID int, LoggerID int,
																IO varchar(31), Type varchar(31), IsCorrect varchar(31), Query int, Score int, 
																Msg varchar(255), Reply varchar(511))""")
	cur.execute("""CREATE TABLE IF NOT EXISTS querymsgdata 		(QueryMsgDataID INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT, QueryDataID int, MsgID int)""")
	cur.execute("""CREATE TABLE IF NOT EXISTS userproblemdata 	(UserProblemDataID INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT, UserID int,
																IO varchar(31), Score int, Query int, ScoreAtSolve int, QueryAtSolve int, CorrectSub varchar(255))""")
	cur.execute("""CREATE TABLE IF NOT EXISTS markingdata 		(MarkingDataID INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT, MarkerID int,
																QueryDataID int, VerdictMsg varchar(255))""")
	cur.execute("""CREATE TABLE IF NOT EXISTS markingmsgdata 	(MarkingMsgDataID INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT, MarkingDataID int, MsgID int)""")
	cur.execute("""CREATE TABLE IF NOT EXISTS problemdata 		(ProblemDataID INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT, IO varchar(31), 
																Description varchar(255), Difficulty real, Rating real, Raters int, Attempts int, Solves int)""")
	cur.execute("""CREATE TABLE IF NOT EXISTS setdata 			(SetDataID INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT, SetName varchar(31), Description varchar(255)""")
	cur.execute("""CREATE TABLE IF NOT EXISTS problemsetdata 	(ProblemSetDataID INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT, SetName varchar(31), IO varchar(31))""")
	cur.execute("""CREATE TABLE IF NOT EXISTS userdata 			(UserDataID INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT, UserID int, MsgID int, PrevIO varchar(31))""")
	cur.execute("""CREATE TABLE IF NOT EXISTS solutiondata 		(SolutionDataID INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT, IO varchar(31), Solution varchar(255),
																IsOriginal boolean)""")


async def process(msg, client):

	regexDone = False; outputguessed = False; logged = False; matchname = ''; submitting = False; go = True
	msgcontent = msg.content; msgauthorid = msg.author.id; matches = regex.match(r"((.*?)\s*\(\s*(.*?)\s*\)\s*)", 'io1(2,3)')

	#requesting problem info
	if regex.match(r"^\s*(.*?)\s+probleminfo\s*$", msgcontent):
		matches = regex.match(r"^\s*(.*?)\s+probleminfo\s*$", msgcontent)
		matchname = matches.group(1)
		problemdata = cur.execute("SELECT ProblemDataID,Difficulty,Description,Rating,Raters,Attempts,Solves FROM problemdata WHERE IO='"+matchname+"'").fetchone()
		thisPDID = problemdata[0]; pddifficulty = problemdata[1]; pddescription = problemdata[2] pdrating = problemdata[3]; pdraters = problemdata[4];
		pdattempts = problemdata[5]; pdsolves = problemdata[6]
		await client.get_channel(loggingchannel).send('```'+matchname+' | '+pddescription+' | '+pddifficulty+' '+pdrating+'('+pdraters+')'+' | '+pdattempts+' '+pdsolves+'```')

	#revealing role ids
	if regex.match(r"reveal.*?", msgcontent):
		await msg.channel.send('```'+msgcontent+'```')
	#logging
	if regex.match(r"^log\s*<@([0-9]{18})>\s*(.*?)$", msgcontent) and regexDone == False and msg.author.id in staff:
		matches = regex.match(r"^log\s*<@([0-9]{18})>\s*(.*?)$", msgcontent)
		logged = True
		msgcontent = matches.group(2); msgauthorid = matches.group(1)
	#submitting
	if regex.match(r"^submit\s*(([a-zA-Z0-9]*).*?)$", msgcontent) and regexDone == False:
		submitting = True; regexDone = True
		matches = regex.match(r"^submit\s*(([a-zA-Z0-9]*).*?)$", msgcontent)
		matchname = matches.group(2); matchsubmission = matches.group(1)
	#guessing
	if regex.match(r"^((.*?)\s*\(\s*(.*?)\s*\).*?\=\s*(.*?)\s*)$", msgcontent) and regexDone == False:
		matches = regex.match(r"^((.*?)\s*\(\s*(.*?)\s*\).*?\=\s*(.*?)\s*)$", msgcontent)
		regexDone = True; outputguessed = True
		matchall = matches.group(1); matchname = matches.group(2); matchinput = matches.group(3); matchguess = matches.group(4)
		if str(matchguess) == '':
			regexDone == False
			msg.channel.send('You have typed an equals sign `=` but have not made a guess.')
	#querying
	if regex.match(r"^((.*?)\s*\(\s*(.*?)\s*\)\s*)$", msgcontent) and regexDone == False: # and isinstance(msg.channel, discord.abc.PrivateChannel):
		matches = regex.match(r"^((.*?)\s*\(\s*(.*?)\s*\)\s*)$", msgcontent)
		matchall = matches.group(1); matchname = matches.group(2); matchinput = matches.group(3)
		regexDone = True

	#standard query process
	if matchname in iofns and regexDone == True and go == True:
		try:
			if submitting == False: value = iofns[matchname]["f"](*regex.split(r" *, *", matchinput))
			if cur.execute("SELECT COUNT(UserProblemDataID) FROM userproblemdata WHERE UserID="+str(msgauthorid)+" AND IO='"+matchname+"'").fetchone()[0] == 0:
				cur.execute("INSERT INTO userproblemdata (UserID,IO,Score,Query,ScoreAtSolve,QueryAtSolve,CorrectSub) VALUES (?,?,?,?,?,?,?)", (msgauthorid,matchname,0,0,0,0,''))
			befscore = cur.execute("SELECT score FROM userproblemdata WHERE UserID="+str(msgauthorid)+" AND IO='"+matchname+"'").fetchone()[0]

			if outputguessed == True and str(matchguess) == str(value):
				curscore = befscore; correct = 'CORRECT'; typestr = 'guess'
				botsend = '✓ '+matchname+'('+matchinput+') = '+str(value)+'      [score: '+str(curscore)+' (+0)]'
			elif outputguessed == True and str(matchguess) != str(value):
				curscore = befscore + 2; correct = 'incorrect'; typestr = 'guess'
				botsend = '✗ '+matchname+'('+matchinput+') = '+str(value)+'      [score: '+str(curscore)+' (+2)]'
			elif submitting == False:
				curscore = befscore + 1; correct = '-'; typestr = 'query'
				botsend = matchname+'('+matchinput+') = '+str(value)+'      [score: '+str(curscore)+' (+1)]'
			else:
				curscore = befscore + 1; correct = 'waiting for confirmation...'; typestr = 'SUBMISSION'
				botsend = 'You submitted '+matchsubmission+' to iostaff.      [score: '+str(curscore)+' (+1)]'

			curquery = cur.execute("SELECT query FROM userproblemdata WHERE UserID="+str(msgauthorid)+" AND IO='"+matchname+"'").fetchone()[0] + 1
			cur.execute("UPDATE userproblemdata SET Score="+str(curscore)+", Query="+str(curquery)+" WHERE UserID="+str(msgauthorid)+" AND IO='"+matchname+"'")
			name = msg.author.name+'#'+msg.author.discriminator
			cur.execute("INSERT INTO querydata (QuerierID,LoggerID,IO,Type,IsCorrect,Query,Score,Msg,Reply) VALUES(?,?,?,?,?,?,?,?,?)",
				(msgauthorid, msg.author.id, matchname, typestr, correct, curquery, curscore, msgcontent, botsend))
			curQID = cur.execute("SELECT MAX(QueryDataID) FROM querydata").fetchone()[0]
			cur.execute("INSERT INTO querymsgdata (QueryDataID, MsgID) VALUES(?,?)", (curQID, msg.id))
			if logged == True:
				await msg.channel.send('\`\`\`'+botsend+'\`\`\`')
				if submitting == True:
					await client.get_channel(loggingchannel).send('**'+str(curQID)+'**  |  <@&'+str(staffrole)+'>  |  <@'+str(msgauthorid)+'>  |  Log by ('+msg.author.name+'#'+str(msg.author.discriminator)+') | **'+msgcontent+'**')
				else:
					await client.get_channel(loggingchannel).send('**'+str(curQID)+'**  |    |  <@'+str(msgauthorid)+'>  |  Log by ('+msg.author.name+'#'+str(msg.author.discriminator)+')  |  **'+msgcontent+'**  |  `'+botsend+'`')
			else:
				await msg.channel.send('```'+botsend+'```')
				if submitting == True:
					await client.get_channel(loggingchannel).send('**'+str(curQID)+'**  |  <@&'+str(staffrole)+'>  |  <@'+str(msgauthorid)+'>  |  ('+msg.author.name+'#'+str(msg.author.discriminator)+')  |  **'+msgcontent+'**')
				else:
					await client.get_channel(loggingchannel).send('**'+str(curQID)+'**  |    |  <@'+str(msgauthorid)+'>  |  ('+msg.author.name+'#'+str(msg.author.discriminator)+')  |  **'+msgcontent+'**  |  `'+botsend+'`')
		except ValueSendError as e:
			await msg.channel.send(str(e))

	#marking
	if regex.match(r"^mark\s*([0-9]+)\s*(correct|incorrect|obfuscated)\s*$", msgcontent) and msg.author.id in staff:
		matches = regex.match(r"^mark\s*([0-9]+)\s*(correct|incorrect|obfuscated)\s*$", msgcontent)
		matchQID = matches.group(1); matchresult = matches.group(2);
		checkcount = cur.execute("SELECT COUNT(QueryDataID) FROM querydata WHERE QueryDataID='"+matchQID+"'").fetchone()[0]
		if checkcount != 1:
			await msg.channel.send('`Error encountered! There exists '+str(checkcount)+' of this QueryDataID.`')
		else:
			fetchinfo = cur.execute("SELECT Type,IsCorrect,IO,QuerierID,Msg,Score,Query,LoggerID FROM querydata WHERE QueryDataID='"+matchQID+"'").fetchone()
			checktype = fetchinfo[0]; checkresult = fetchinfo[1]
			if checktype == 'SUBMISSION' and checkresult == 'waiting for confirmation...':
				submittedio = fetchinfo[2]; submitterID = fetchinfo[3]; submittedmsg = fetchinfo[4]; scoreatsubmit = fetchinfo[5]; queryatsubmit = fetchinfo[6]; loggerID = fetchinfo[7]
				waslogged = (submitterID != loggerID)
				cur.execute("INSERT INTO markingdata (MarkerID,SubmittedMsg,VerdictMsg) VALUES(?,?,?)",
					(msg.author.id, submittedmsg, msgcontent))
				curMDID = cur.execute("SELECT MAX(QueryDataID) FROM querydata").fetchone()[0]
				cur.execute("INSERT INTO markingmsgdata (MarkindDataID,MsgID) VALUES(?,?)", (curMDID, msg.id))
				if matchresult == 'correct':
					submitterDMchannel = await client.get_user_info(submitterID)
					botsend = '✓ "'+submittedmsg+'" was judged as correct! Score: '+str(scoreatsubmit)+', queries: '+str(queryatsubmit)+' (at submission).'
					if waslogged == False:
						await submitterDMchannel.send('```'+botsend+'```')
					cur.execute("""UPDATE userproblemdata SET ScoreAtSolve="+str(scoreatsubmit)+", QueryAtSolve="+str(queryatsubmit)+", CorrectSub='"+submittedmsg+"'
						WHERE UserID="+str(submitterID)+" AND IO='"+submittedio+"'""")
					cur.execute("UPDATE querydata SET IsCorrect='CORRECT',Reply='"+botsend+"' WHERE QueryDataID='"+matchQID+"'")
				else:
					curscore = cur.execute("SELECT score FROM userproblemdata WHERE UserID="+str(submitterID)+" AND IO='"+submittedio+"'").fetchone()[0]
					curquery = cur.execute("SELECT query FROM userproblemdata WHERE UserID="+str(submitterID)+" AND IO='"+submittedio+"'").fetchone()[0]
					submitterDMchannel = await client.get_user_info(submitterID)
					if matchresult == 'incorrect':
						botsend = '✗ "'+submittedmsg+'" was judged as incorrect. Score: '+str(curscore)+', queries: '+str(curquery)+'.'
						if waslogged == False:
							await submitterDMchannel.send('```'+botsend+'```')
						cur.execute("UPDATE querydata SET IsCorrect='incorrect',Reply='"+botsend+"' WHERE QueryDataID='"+matchQID+"'")
					else:
						if waslogged == False:
							botsend = '( ͡° ͜ʖ ͡°) "'+submittedmsg+'" was judged as obfuscated, you troll XD. Score: '+str(curscore)+', queries: '+str(curquery)+'.'
							await submitterDMchannel.send('```'+botsend+'```')
						cur.execute("UPDATE querydata SET IsCorrect='obf',Reply='"+botsend+"' WHERE QueryDataID='"+matchQID+"'")
				if waslogged == False:
					await msg.channel.send('`Updated and Forwarded.`')
				else:
					await msg.channel.send('`Updated.`')
			elif checktype == 'SUBMISSION':
				errorverdict = cur.execute("SELECT IsCorrect FROM querydata WHERE QueryDataID='"+matchQID+"'").fetchone()[0]
				await msg.channel.send('`Error encountered! Verdict of this QueryDataID is already set at '+errorverdict+'.`')
			else:
				errorchecktype = cur.execute("SELECT Type FROM querydata WHERE QueryDataID='"+matchQID+"'").fetchone()[0]
				await msg.channel.send('`Error encountered! Type of this QueryDataID is '+errorchecktype+'.`')

	#listinputs
	if regex.match(r"^listinputs\s*(.*?)\s*$", msgcontent):
		matchname = regex.match(r"^listinputs\s*(.*?)\s*$", msgcontent).group(1)
		listdata = cur.execute("SELECT Query,Score,Reply FROM querydata WHERE QuerierID="+str(msgauthorid)+" AND IO='"+matchname+"'").fetchall()
		botsend = '\n'+matchname+'\n-------------------------\n'
		if len(listdata) == 0:
			botsend = botsend+'No inputs yet.'
		else:
			botsend = botsend+'#   S   Message'
			for i in range(len(listdata)):
				botsend = botsend+'\n'+str(listdata[i][0])+' | '+str(listdata[i][1])+' | '+str(listdata[i][2])
		botsend = botsend+'\n'
		await msg.channel.send('```'+botsend+'```')

	#adding and updating problems
	if regex.match(r"^problem\s+(.*?)\s+(.*?)\s+(.*?)\s+(.*?)$", msgcontent):
		matches = regex.match(r"^problem\s+(add|update)\s+(.*?)\s+(.*?)\s+(.*?)$", msgcontent)
		matchcmd1 = matches.group(1); matchname = matches.group(2); matchdifficulty = matches.group(3); matchdescription = matches.group(4)
		if matchcmd1 == 'add':
			checkcount = cur.execute("SELECT COUNT(ProblemDataID) FROM problemdata WHERE IO = '"+matchname"'").fetchone()[0]
			if checkcount != 0:
				await msg.channel.send("That name is already taken, please try a different one.")
			else:
				cur.execute("INSERT INTO problemdata (IO,Difficulty,Description,Rating,Raters,Attempts,Solves) VALUES (?,?,?,?,?,?,?)", (matchname, matchdifficulty, matchdescription, -1, 0, 0, 0))
				thisPDID = cur.execute("SELECT MAX(ProblemDataID) FROM problemdata").fetchone()[0]
				await msg.channel.send('`Problem added.`')
				await client.get_channel(loggingchannel).send('Added new problem (ID: '+thisPDID+')\n```'+matchname+' | '+matchdescription+' | '+matchdifficulty+' -1(0) | 0 0```')
		elif matchcmd1 = 'update':
			if checkcount != 1:
				await msg.channel.send('`'+matchname+'` exists '+checkcount+' times.')
			elif:
				problemdata = cur.execute("SELECT ProblemDataID,Difficulty,Description,Rating,Raters,Attempts,Solves FROM problemdata WHERE IO='"+matchname+"'").fetchone()
				thisPDID = problemdata[0]; befpddifficulty = problemdata[1]; befpddescription = problemdata[2]; pdrating = problemdata[3]; pdraters = problemdata[4];
				pdattempts = problemdata[5]; pdsolves = problemdata[6]
				await client.get_channel(loggingchannel).send('`'+thisPDID+'` was :\n```'+matchname+' | '+befpddescription+' | '+befpddifficulty+' '+pdrating+'('+pdraters+')'+' | '+pdattempts+' '+pdsolves+'```')
				cur.execute("UPDATE problemdata SET Description='"+matchdescription+"', Difficulty='"+matchdifficulty+"' WHERE IO='"+matchname+"'")
				await client.get_channel(loggingchannel).send('`'+thisPDID+'` has been updated to:\n```'+matchname+' | '+matchdescription+' | '+matchdifficulty+' '+pdrating+'('+pdraters+')'+' | '+pdattempts+' '+pdsolves+'```')
				await msg.channel.send('`Problem updated.`')

	#set tagging
	if regex.match(r"^set\s+(.*?)\s+(include|exclude|clear)\s*(.*)$", msgcontent):
		matches = regex.match(r"^set\s+(.*?)\s+(include|exclude|clear)\s*(.*)$", msgcontent)
		matchsetname = matches.group(1); matchcmd1 = matches.group(2); matchio = matches.group(3)
		checkcount = cur.execute("SELECT COUNT(ProblemSetDataID) FROM problemsetdata WHERE SetName='"+matchsetname+"'").fetchone()[0]
		if matchcmd1 == 'clear':
			if checkcount == 0:
				await msg.channel.send('`'+matchsetname+'` is already empty.')
			else:
				listdata = cur.execute("SELECT IO FROM problemsetdata WHERE SetName='"+matchsetname+"'").fetchall()
				botlist = ''
				for i in range(len(listdata)):
					botlist = botlist+listdata[i][0]+'\n'
				if checkcount == 1:
					await msg.channel.send('1 IO has been removed from set `'+matchsetname+'`: ```'+botlist+'```')
				else:
					await msg.channel.send(checkcount+' IOs have been removed from set `'+matchsetname+'`: ```'+botlist+'```')
				cur.execute("DELETE FROM problemsetdata WHERE SetName='"+matchsetname+"'")
		elif matchcmd1 == 'include':
			checkcountio = cur.execute("SELECT COUNT(ProblemDataID) FROM problemdata WHERE IO='"+matchio+"'").fetchone()[0]
			checkcountsetio = cur.execute("SELECT COUNT(ProblemSetDataID) FROM problemsetdata WHERE SetName='"+matchsetname+"', IO='"+matchio+"'").fetchone()[0]
			if checkcountio != 1:
				await msg.channel.send('There are '+checkcountio+' IOs with the name `'+matchio+'`.')
			elif checkcountsetio == 1:
				await msg.channel.send('There is already 1 entry with the pair: `'+matchio+'` `'+matchsetname+'`.')
			elif checkcountsetio >= 2:
				await msg.channel.send('Something\'s wrong. There are '+checkcountsetio+' entries with the pair: `'+matchio+'` `'+matchsetname+'`.')
			else:
				cur.execute("INSERT INTO problemsetdata (SetName, IO) Values (?,?)", (matchsetname, matchio))
				await msg.channel.send('`'+matchio+'` is now included in set `'+matchsetname+'`.')
		elif matchcmd1 == 'exclude':
			checkcountio = cur.execute("SELECT COUNT(ProblemDataID) FROM problemdata WHERE IO='"+matchio+"'").fetchone()[0]
			checkcountsetio = cur.execute("SELECT COUNT(ProblemSetDataID) FROM problemsetdata WHERE SetName='"+matchsetname+"', IO='"+matchio+"'").fetchone()[0]
			if checkcountio == 0:
				await msg.channel.send('There are no IOs with the name `'+matchio+'`.')
			elif checkcountio != 1:
				await msg.channel.send('There are '+checkcountio+' IOs with the name `'+matchio+'`.')
			elif checkcountsetio == 0:
				await msg.channel.send('`'+matchio+'` was already excluded from set `'+matchsetname+'`.')
			else:
				cur.execute("DELETE FROM problemsetdata WHERE SetName='"+matchsetname+"', IO='"+matchio+"'")
				await msg.channel.send('`'+matchio+'` is now excluded from set `'+matchsetname+'`.')

	#set adding and deleting
	if regex.match(r"^(new|update)\s+set\s+(\S+)\s*+(.*)$", msgcontent):
		matches = regex.match(r"^(new|update)\s+set\s+(\S+)\s*+(.*)$", msgcontent)
		matchcmd1 = matches.group(1); matchsetname = matches.group(2); matchdescription = matches.group(3)
		checkcount = cur.execute("SELECT COUNT(SetDataID) FROM setdata WHERE SetName = '"+matchsetname"'").fetchone()[0]
		if matchcmd1 == 'new':
			if checkcount == 1:
				await msg.channel.send('Set already exists.')
			elif checkcount >= 1:
				await msg.channel.send('Something\'s wrong. This set exists '+checkcount+' times.')
			elif checkcount == 0:
				cur.execute("INSERT INTO setdata (SetName, Description) VALUES (?,?)", (matchsetname, matchdescription))
				curid = cur.execute("SELECT MAX(SetDataID) FROM setdata").fetchone()[0]
				await msg.channel.send('New set created:```ID: '+curid+'\nName: '+matchsetname+'\nDescrption: '+matchdescription+'```')
		elif matchcmd1 == 'update':
			if checkcount == 0:
				await msg.channel.send('This set does not exist yet. To create this set use: `new set '+matchsetname+' '+matchdescription+'`')
			elif checkcount != 1:
				await msg.channel.send('Something\'s wrong. This set exists '+checkcount+' times.')
			elif checkcount == 1:
				temp = cur.execute("SELECT SetDataID,Description FROM setdata WHERE SetName='"+matchsetname+"'").fetchone()
				setid = temp[0]; befdescription = temp[1]
				await msg.channel.send('Set updated:```ID: '+setid+'\nName: '+matchsetname+'\nPrevious Descrption: '+befdescription+'\nNew Descrption:'+matchdescription+'```')
				cur.execute("UPDATE setdata SET Description='"+matchdescription+"'' WHERE SetName='"+matchsetname+"'")

	#troll
	if regex.match(r"cambridge is way better than oxford", msgcontent):
		await msg.channel.send('I agree.')

	if regex.match(r"see\? we have majority", msgcontent):
		await msg.channel.send('Exactly, so Cambridge is better than Oxford.')

	conn.commit()

#
def isupdate(msg):
	return msg.content == "u" and (msg.author.id == tony or msg.author.id == milo)

async def update():
	pass

def io(name=None, inputs=0):
	def _value(f):
		#if name is None:
		#	name = f.__name__
		iofns[name] = {"name":name, "inputs":inputs, "f":f}
		#inregs = []
		#if type(types) is not tuple:
		#	types = (types,)
		#for typ in types:
		#	if typ is int:
		#		inregs.append(r"-?[0-9]*")
		#	elif typ is float:
		#		inregs.append(r"-?[0-9.]*")
		#	elif typ is str:
		#		inregs.append(r".*?")
		#reg = r"^(" + regex.escape(name) + r"\(" + r" *, *".join(inregs) + r"\))"
		#def proc(st): # takes message content, outputs _
		return f
	return _value

class ValueSendError(ValueError):
	pass

@io(name="iotest", inputs=2)
def iotest(a1, a2):
	try:
		return 4*int(a1) - 3*int(a2)
	except ValueError:
		try:
			return 4*float(a1) - 3*float(a2)
		except ValueError:
			raise ValueSendError("Whoops! Both parameters should be real numbers.")

@io(name="io1", inputs=2)
def io1(a1, a2):
	try:
		return int(a1) - int(a2)
	except ValueError:
		try:
			return float(a1) - float(a2)
		except ValueError:
			raise ValueSendError("Whoops! Both parameters should be real numbers.")

@io(name="io2", inputs=2)
def io2(a1, a2):
	if (int(a1) < 0) | (int(a2) < 0):
		return "Oopsies! Both parameters should be nonnegative integers."
	if int(a2) == 0:
		return "Error"
	try:
		return int(a1) % int(a2)
	except ValueError:
		raise ValueSendError("Whoops! Both parameters should be nonnegative integers.")