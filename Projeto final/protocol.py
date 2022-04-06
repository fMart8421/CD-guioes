
def JoinMessage(ID : int):
	alive_msg =  {"command": "JOIN" , "data": ID}
	return alive_msg

def DoneMessage():
	done_msg = {"command":"DONE"}
	return done_msg