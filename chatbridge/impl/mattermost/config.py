from chatbridge.core.config import ClientConfig


class MattermostConfig(ClientConfig):
	mattermost_ssl: bool = True
	mattermost_address: str = '127.0.0.1'
	mattermost_port: int = 8065
	mattermost_token: str = ''
	connection_prompt: bool = True
	channel_id: str = ''
	bot_name: str = ''
