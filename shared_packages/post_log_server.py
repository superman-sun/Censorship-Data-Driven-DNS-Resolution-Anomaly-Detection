import logging
import logging.handlers


class PostLog(object):
    def __init__(self, log_server):
        self.host = log_server['host']
        self.port = str(log_server['port'])
        self.url = log_server['url']

    def post_log(self, msg):
        """将日志post到web服务器"""
        logger = logging.getLogger('root')
        logger.setLevel(logging.INFO)
        http_handler = logging.handlers.HTTPHandler(
            self.host+':'+self.port,
            self.url,
            method='POST',
        )
        logger.addHandler(http_handler)
        logger.info(msg)


if __name__ == '__main__':

    log_server = {
        'host': '127.0.0.1',
        'port': '8899',
        'url': '/log'
    }
    http_log = PostLog(log_server)
    http_log.post_log('hello hi')