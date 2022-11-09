import mattermost
import mattermost.ws as mws
import json
from time import sleep
from typing import Optional

from chatbridge.common.logger import ChatBridgeLogger
from chatbridge.core.client import ChatBridgeClient
from chatbridge.core.config import ClientConfig
from chatbridge.core.network.protocol import ChatPayload, CommandPayload
from chatbridge.impl import utils
from chatbridge.impl.mattermost.config import MattermostConfig
from chatbridge.impl.tis.protocol import OnlineQueryResult

ConfigFile = 'ChatBridge_mattermost.json'
mm_bot: Optional['MattermostBot'] = None
chatClient: Optional['MattermostChatBridgeClient'] = None


class MattermostMessage():
	def __init__(self, source):
		self.channel_id = source['broadcast']['channel_id']
		self.sender_name = source['data']['sender_name']
		strtmp = source['data']['post']
		json_ = json.loads(strtmp)
		self.msg = json_['message']


class MattermostBot():
	def __init__(self, config: MattermostConfig):
		self.config = config
		self.logger = ChatBridgeLogger('Bot', file_handler = chatClient.logger.file_handler)
		self.http_address = f'http{"s" * self.config.mattermost_ssl}://{self.config.mattermost_address}:{self.config.mattermost_port}'
		self.logger.info(f'正在连接 Mattermost ({self.http_address})')
		self.api = mattermost.MMApi(f'{self.http_address}/api')
		self.api.login(bearer = config.mattermost_token)

	def start(self):
		mws.MMws(self.event_handler, self.api, f'ws{"s" * self.config.mattermost_ssl}://{self.config.mattermost_address}:{self.config.mattermost_port}/api/v4/websocket')
		if self.config.connection_prompt:
			self._send_text('已连接 **ChatBridge**')
		self.logger.info(f'已连接 Mattermost')
		try:
			while True:
				sleep(3)
		except KeyboardInterrupt:
			self.close()
		except BaseException as e:
			self.logger.info(f'出现错误：{str(e)}')
			self.close(f'**ChatBridge**  客户端出现错误：{str(e)}')
	
	def close(self, message: str = '已断开 **ChatBridge**'):
		if self.config.connection_prompt:
			self._send_text(message)
		self.logger.info('即将退出')
		exit(0)

	def event_handler(self, mmws, event_data):
		try:
			if chatClient is None:
				return
			if event_data['event'] == 'posted':
				event = MattermostMessage(event_data)
				if (event.channel_id == self.config.channel_id) and (len(event.msg) != 0) and (event.sender_name != self.config.bot_name):
					self.logger.info(f'[Mattermost]: {event.msg}')
					args = event.msg.split(' ')
					if len(args) == 2 and args[0] == '!!online':
						client = args[1]
						if chatClient.is_online():
							command = args[0]
							chatClient.send_command(client, command)
						else:
							self._send_text(f'{client} 离线')
					else:
						chatClient.send_chat(event.msg, event.sender_name[1:])
		except:
			self._send_text('处理消息时出现问题')
			

	def _send_text(self, text):
		msg = ''
		length = 0
		lines = text.rstrip().splitlines(keepends=True)
		for i in range(len(lines)):
			msg += lines[i]
			length += len(lines[i])
			if i == len(lines) - 1 or length + len(lines[i + 1]) > 500:
				self.api.create_post(self.config.channel_id, text)
				msg = ''
				length = 0

	def send_message(self, sender: str, message: str):
		self._send_text(f'[{sender}] {message}')


class MattermostChatBridgeClient(ChatBridgeClient):
	def on_chat(self, sender: str, payload: ChatPayload):
		global mm_bot
		if mm_bot is None:
			return
		try:
			try:
				prefix, message = payload.message.split(' ', 1)
			except:
				pass
			else:
				if prefix in ('!!mm', '!!mhere'):
					payload.message = message
					mm_bot.send_message(sender, f'{"@here " * (prefix == "!!mhere")}{payload.formatted_str()}')
		except:
			self.logger.exception('处理消息时出现错误')
			mm_bot.close('处理消息时出现错误')
	
	def on_command(self, sender: str, payload: CommandPayload):
		if not payload.responded:
			return
		if payload.command == '!!online':
			result = OnlineQueryResult.deserialize(payload.result)
			mm_bot.send_text('====== 玩家列表 ======\n{}'.format('\n'.join(result.data)))


def main():
	global chatClient, mm_bot
	config: ClientConfig = utils.load_config(ConfigFile, MattermostConfig)
	chatClient = MattermostChatBridgeClient.create(config)
	utils.start_guardian(chatClient)
	print('正在启动 Mattermost Bot')
	mm_bot = MattermostBot(config)
	mm_bot.start()


if __name__ == '__main__':
	main()
