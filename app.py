import json, sys, asyncio, websockets, os

USERS = []

def find_user(conn):
	for user in USERS:
		if user['conn'] == conn:
			return user

def find_user_by_id(uid):
	for user in USERS:
		if user['uid'] == uid:
			return user

def get_index(uid):
	usr = find_user_by_id(uid)
	idx = USERS.index(usr)
	return idx

def set_engaged(idx,val=True):
	USERS[idx]['engaged'] = val

def get_users(usr_array):
	users = []
	for user in usr_array:
		usrdata = {
			'uid': user['uid'],
			'name': user['name'],
			'email': user['email'],
			'photo': user['photo'],
			'age': user['age'],
			'profession': user['profession'],
			'country': user['country'],
			'desc': user['desc'],
			'engaged': user['engaged']
		}
		users.append(usrdata)
	return users

async def notify_users(name,action_type):
	dt = {'type': 'user_action', 'name': name, 'action': action_type, 'users': get_users(USERS)}
	for user in USERS:
		try:
			await user['conn'].send(json.dumps(dt))
		except websockets.ConnectionClosed:
			continue


async def delete_user(conn):
	usr = find_user(conn)
	try:
		USERS.remove(usr)
	except KeyError:
		usrname = usr['name']
		print(f'{usrname} has already been removed!')
	await notify_users(usr['name'],'left')


async def register(client):
	userDetails = await client.recv()
	usr_data = json.loads(userDetails)
	usr_data.setdefault('conn',client)
	USERS.append(usr_data)
	await notify_users(usr_data['name'],'joined')

async def broadcast(msg):
	parsed_msg = json.loads(msg)
	sender = find_user_by_id(parsed_msg['from'])
	recvr = find_user_by_id(parsed_msg['to'])

	if parsed_msg['type'] == 'call_request':
		if recvr and recvr['engaged'] == False:
			data = {
				'type': 'offer',
				'sender': parsed_msg['name'],
				'id': parsed_msg['from'],
				'offer': parsed_msg['offer'],
				'candidate': parsed_msg['candidate']
			}
			await recvr['conn'].send(json.dumps(data))
		else:
			resp = {'type': 'rejected'}
			await sender['conn'].send(json.dumps(resp))

	if parsed_msg['type'] == 'call_answer':
		data = {
			'type': 'answer',
			'sender': parsed_msg['name'],
			'id': parsed_msg['from'],
			'answer': parsed_msg['answer'],
			'candidate': parsed_msg['candidate']
		}
		set_engaged(recvr['uid'])
		set_engaged(sender['uid'])
		await recvr['conn'].send(json.dumps(data))

	if parsed_msg['type'] == 'rejected':
		reject_msg = {'type': 'rejected'}
		await recvr['conn'].send(json.dumps(reject_msg))

	if parsed_msg['type'] == 'call_aborted':
		abort_msg = {'type': 'call_aborted'}
		await recvr['conn'].send(json.dumps(abort_msg))

	if parsed_msg['type'] == 'call_ended':
		idx = get_index(parsed_msg['from'])
		set_engaged(idx,False)

async def handle_client(client, path):
	await register(client)
	while True:
		try:
			client_msg = await client.recv()
			if client_msg:
				await broadcast(client_msg)
			else:
				continue
		except websockets.ConnectionClosed:
			await delete_user(client)
			break


server = websockets.serve(handle_client,"",int(os.environ['PORT']))
asyncio.get_event_loop().run_until_complete(server)
asyncio.get_event_loop().run_forever()
