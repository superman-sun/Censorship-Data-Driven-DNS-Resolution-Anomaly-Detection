# encoding: utf-8
"""
读取系统配置参数
"""
import configparser as ConfigParser
import random


class SystemConfigParse(object):
    def __init__(self, system_file):
        self.cf = ConfigParser.ConfigParser()
        self.cf.read(system_file)

    def read_rabbitmq_server(self):
        """读取Kafka服务器地址"""
        hosts = []
        servers = self.cf.get("rabbitmq_server","hosts")
        for server in servers.split(','):
            server = server.split(':')
            hosts.append((server[0], server[1], server[2]))
        random.shuffle(hosts)
        return hosts

    def read_log_show(self):
        """是否将日志在终端显示"""
        show_terminal = self.cf.getboolean("log_show_terminal","show_terminal")
        return show_terminal

    def read_db_config(self):
        """是否将日志在终端显示"""
        db_config = self.cf.get("db","db_config")
        return db_config

    def read_redis_db_config(self):
        redis_config = self.cf.get("redis","redis_config")
        return redis_config

    def read_root_tld_probe(self):
        """root_tld探测节点的配置参数"""
        coroutine_num = self.cf.getint("root_tld_probe", "coroutine_num")   # 协程数量
        message_timeout = self.cf.getint("root_tld_probe", "message_timeout")  # 消息超时时间

        return dict(
            coroutine_num = coroutine_num,
            message_timeout = message_timeout
        )

    def read_root_tld_analyzing(self):
        """root_tld探测节点的配置参数"""
        keep_time = self.cf.getint("root_tld_analyzing", "keep_time")   # 协程数量
        analyzing_timeout = self.cf.getint("root_tld_analyzing", "analyzing_timeout")  # 消息超时时间

        return dict(
            keep_time=keep_time,
            analyzing_timeout=analyzing_timeout
        )

    def read_root_tld_task(self):
        """root_tld探测节点的配置参数"""
        task_timeout = self.cf.getint("root_tld_task", "task_timeout")  # 消息超时时间

        return dict(
            task_timeout=task_timeout
        )

    def read_tld_domain_probe(self):
        """tld_domain探测点的配置"""
        coroutine_num = self.cf.getint("tld_domain_probe", "coroutine_num")  # 协程数量
        process_num = self.cf.get("tld_domain_probe", "process_num")  # 消息超时时间

        return dict(
            coroutine_num=coroutine_num,
            process_num=float(process_num)
        )

    def read_dns_domain_probe(self):
        """tld_domain探测点的配置"""
        coroutine_num = self.cf.getint("dns_domain_probe", "coroutine_num")  # 协程数量
        process_ratio = self.cf.get("dns_domain_probe", "process_ratio")  # 消息超时时间
        timeout = self.cf.getint("dns_domain_probe", "timeout")
        retry_time = self.cf.getint("dns_domain_probe", "retry_time")

        return dict(
            coroutine_num=coroutine_num,
            process_ratio=float(process_ratio),
            timeout=timeout,
            retry_time=retry_time
        )

    def read_tld_domain_task(self):
        """tld_domain的配置"""
        split_num = self.cf.getint("tld_domain_task", "split_num")  # 协程数量
        message_timeout = self.cf.getint("tld_domain_task", "message_timeout")  # 协程数量

        return dict(
            split_num=split_num,
            message_timeout = message_timeout
        )

    def read_ns_domain_task(self):
        """ns_domain的配置"""
        split_num = self.cf.getint("ns_domain_task", "split_num")
        message_timeout = self.cf.getint("ns_domain_task", "message_timeout")

        return dict(
            split_num = split_num,
            message_timeout = message_timeout
        )

    def read_dns_domain_task(self):
        """dns_domain的配置"""
        split_num = self.cf.getint("dns_domain_task", "split_num")
        message_timeout = self.cf.getint("dns_domain_task", "message_timeout")

        return dict(
            split_num = split_num,
            message_timeout = message_timeout
        )

    def read_log_server(self):
        """读取日志服务器配置"""
        host = self.cf.get("log_server", "host")  # 协程数量
        port = self.cf.get("log_server", "port")  # 消息超时时间
        url = self.cf.get("log_server", "url")  # 消息超时时间

        return dict(
            host=host,
            port=port,
            url=url
        )


if __name__ == '__main__':
    system_config = SystemConfigParse('./system.conf')
    # print(system_config.read_log_show())
    # print(system_config.read_root_tld_probe())
    # print(system_config.read_root_tld_analyzing())
    # print(system_config.read_root_tld_task())
    # print(system_config.read_tld_domain_probe())
    # print(system_config.read_tld_domain_task())
    # print(system_config.read_db_config())
    # print(system_config.read_log_server())
    print(system_config.read_dns_domain_probe())
