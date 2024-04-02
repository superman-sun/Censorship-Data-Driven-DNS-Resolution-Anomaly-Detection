#encoding:utf-8
"""
系统运行日志类
"""

import os
import sys
import logging
from logging import handlers


class Logger(object):
    """程序运行日志管理"""
    # 日志级别关系映射
    level_relations = {
        'debug': logging.DEBUG,
        'info': logging.INFO,
        'warning': logging.WARNING,
        'error': logging.ERROR,
        'crit': logging.CRITICAL
    }

    file_name = os.path.basename(sys.argv[0])
    file_name = '.'.join(file_name.split('.')[:-1])+'.log'  # 默认日志文件名称，为运行文件名称

    def __init__(self, filename=file_name, file_path='./log/', level='info', interval=1, when='D', backup_count = 5,
                 fmt='%(asctime)s - %(filename)s[line:%(lineno)d] - %(levelname)s: %(message)s', show_terminal=False):
        """ 初始化日志类
            # 默认日志文件名称为，为程序运行文件名称+.log，否则为指定
            # 默认保持路径为程序当前运行路径
            默认为显示级别为info，日志生成间隔时间为1，默认单位为天，备份半个月的记录
            show_terminal，是否在终端显示，默认为不显示
        """
        folder = os.path.exists(file_path)
        if not folder:  # 判断是否存在文件夹如果不存在则创建为文件夹
            try:
                os.makedirs(file_path)  # makedirs 创建文件时如果路径不存在会创建这个路径
            except Exception as e:
                raise e
        filename = os.path.join(file_path, filename)
        self.logger = logging.getLogger(filename)
        format_str = logging.Formatter(fmt)  # 设置日志格式
        if not self.logger.handlers:
            self.logger.setLevel(self.level_relations.get(level))  # 设置日志级别
            th = handlers.TimedRotatingFileHandler(filename=filename, interval=interval, when=when,
                                                   backupCount=backup_count)
            th.setFormatter(format_str)  # 设置文件里写入的格式
            self.logger.addHandler(th)
            if show_terminal:
                sh = logging.StreamHandler()  # 往屏幕上输出
                sh.setFormatter(format_str)  # 设置屏幕上显示的格式
                self.logger.addHandler(sh)  # 把对象加到logger里


if __name__ == '__main__':
    log = Logger(show_terminal=True,level='debug')
    domain = "baidu.com"
    log.logger.debug('debug %s' % domain)
    log.logger.info('info')
    log.logger.warning('警告')
    log.logger.error('报错')
    log.logger.warning('警告')