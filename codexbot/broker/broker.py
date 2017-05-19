import asyncio
import json
import logging
import random
import string

from codexbot.lib.rabbitmq import add_message_to_queue, init_receiver
from .api import API


class Broker:

    OK = 200
    WRONG = 400
    ERROR = 500

    def __init__(self, core, event_loop):
        logging.info("Broker started ;)")
        self.core = core
        self.event_loop = event_loop
        self.api = API(self)

    async def callback(self, channel, body, envelope, properties):
        """
        Process all messages from 'core' queue by self.API object
        :param channel:
        :param body:
        :param envelope:
        :param properties:
        :return:
        """
        try:
            logging.debug(" [x] Received %r" % body)
            await self.api.process(body.decode("utf-8"))
        except Exception as e:
            logging.error("Broker callback error")
            logging.error(e)

    async def service_to_app(self, message_data):
        """
        Find application by command and send there message data.
        
        :param message_data: 
        :return: 
        """

        chat_hash = self.get_chat_hash(message_data)

        for incoming_cmd in message_data['commands']:

            app_cmd = self.core.db.find_one(self.api.COMMANDS_COLLECTION_NAME, {
                'name': incoming_cmd['command']
            })

            if not app_cmd:
                continue

            app = self.core.db.find_one(self.api.APPS_COLLECTION_NAME, {
                'name': app_cmd['app_name']
            })

            message = json.dumps({
                'command': 'service callback',
                'payload': {
                    'command': incoming_cmd['command'],
                    'params': incoming_cmd['payload'],
                    'chat': chat_hash
                }
            })

            await self.add_to_app_queue(message, app['queue'], app['host'])

    async def add_to_app_queue(self, message, queue_name, host='localhost'):
        """
        Send message to app queue on the host 
        :param message: message string
        :param queue_name: name of destination queue
        :param host: destination host address
        :return:
        """
        await add_message_to_queue(message, queue_name, host)

    def start(self):
        """
        Receive all messages from 'core' queue to self.callback
        :return:
        """
        self.event_loop.run_until_complete(init_receiver(self.callback, "core"))

    def get_chat_hash(self, message_data):
        """
        Search chat_hash in db. If chat_hash not found, generate new and insert it to db
        
        :param message_data: 
        :return: 
        """

        chat = self.core.db.find_one('chats', {'id': message_data['chat']})

        if not chat:
            chat_hash = ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(8))

            self.core.db.insert(
                'chats',
                {
                    'id': message_data['chat'],
                     'hash': chat_hash,
                     'service': message_data['service']
                }
            )
        else:
            chat_hash = chat['hash']

        return chat_hash







