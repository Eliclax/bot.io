import discord
import cmds
import importlib

client = discord.Client()
loggingchannel = 471641874025676801

#def readjson(path):
#	with open(path) as fil:
#		return json.load(fil)


with open("./auth.txt","r") as f:
	auth = f.read()


@client.event
async def on_ready():
	await cmds.update()
	#await client.change_presence(game=discord.Game(name=cmds.pref+"help")) # chagne keyword game to activity
	print("yoy, io bot online")

@client.event
async def on_message(msg):
	await cmds.process(msg, client)
	if cmds.isupdate(msg):
		importlib.reload(cmds)
		await cmds.update()
		await client.get_channel(loggingchannel).send('updated')
		print("updated")
		await msg.channel.send("updated")


client.run(auth)