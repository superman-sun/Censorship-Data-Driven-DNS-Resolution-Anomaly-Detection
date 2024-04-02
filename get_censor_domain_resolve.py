# encoding:utf-8
"""
获取各个国家审查域名的解析结果
"""
import asyncio
import async_timeout
import time
import random
import math
import itertools
import schedule
import pika
import lzma
from datetime import datetime
import dns
import os
import dns.name
import dns.query
import dns.resolver
from dns.asyncresolver import Resolver
import dns.asyncquery
import dns.asyncresolver
from multiprocessing import Process
from multiprocessing import cpu_count  # cpu核数
from collections import defaultdict
import json
from aioping import ping
from utils_get_author_info import get_authoritative_nameserver
from shared_packages.Logger import Logger
from shared_packages.get_public_ip import get_pub_ip
from shared_packages.read_config import SystemConfigParse
from shared_packages.db_manage import MySQL
conf_path = 'shared_packages/system.conf'
logger = Logger(show_terminal=SystemConfigParse(conf_path).read_log_show())
# logger.logger.info('输出日志打印信息')

def get_process_num(process_times):
    """根据CPU数量，获取进程数量，最大不超过N个进程"""
    process_num = cpu_count()
    if process_num != 1:
        process_num = int(math.ceil(process_num*process_times))+1
    if process_num >= 8:
        process_num = 8
    return process_num


def list_split(listTemp, n):
    """分割列表，每份基本平均n个元素"""
    leth = len(listTemp)
    for i in range(0, leth, n):
        yield listTemp[i:i + n]

class probe:

    def __init__(self, process_name, tld_ns_ips, task_list, timeout, retry_time, task_id, public_ip):

        # threading.Thread.__init__(self)
        self.process_name = process_name
        self.tld_ns_ips = tld_ns_ips
        self.task_list = task_list

        self.data_result = []
        self.timeout = timeout
        self.retry_time = retry_time
        self.task_id = task_id
        self.public_ip = public_ip

    async def query_ip_cname_ns_by_local_ns(self, domain, local_dns, rdtype=dns.rdatatype.A, default_dns=False, timeout=3, retry_time=2):

        ips_list, cnames_list = [], []
        response_status, response_time = False, None
        edns, payload, nsid = None, None, None
        answer_len, authority_len, additional_len = 0, 0, 0
        response_size, req_flags = None, None
        authority_data, additional_data = defaultdict(list), defaultdict(list)

        for _ in range(retry_time):
            t1 = time.time()
            try:
                async with async_timeout.timeout(self.timeout * 2 * 2) as cm:
                    if default_dns:
                        t1 = time.time()
                        default_resolver = Resolver(configure=True)
                        # default_resolver.use_edns(payload=4096, options=[dns.edns.GenericOption(dns.edns.NSID, b'')])
                        default_resolver.use_edns(payload=4096)
                        default_resolver.timeout = timeout  # 超时时间
                        result = await default_resolver.resolve(domain, rdtype=rdtype, raise_on_no_answer=True)
                        response = result.response

                    else:
                        t1 = time.time()
                        ques = dns.message.make_query(qname=domain, rdtype=rdtype, use_edns=True)
                        ques.use_edns(payload=4096, options=[dns.edns.GenericOption(dns.edns.NSID, b'')])

                        result = await dns.asyncquery.udp_with_fallback(q=ques, where=local_dns, timeout=timeout,
                                                                        ignore_unexpected=True)
                        response = result[0]

                    rcode = response.rcode()
                    rcode = dns.rcode.to_text(rcode)
                    response_status = rcode

                    response_time = response.time  # 获取查询往返时延
                    req_flags = dns.flags.to_text(response.flags).split()  # 响应报文标识位
                    response_size = len(response.to_wire())  # 整个响应报文的长度

                    edns = response.edns  # 是否支持edsn
                    payload = response.payload  # 响应报文负载
                    for opt in response.options:
                        if opt.otype == dns.edns.NSID:
                            nsid = str(opt.data, 'utf-8')

                    # #计算authortiy,addtional个数
                    # authority_len = len(response.authority)
                    # additional_len = len(response.additional) + 1 if edns >= 0 else len(response.additional)

                    additional_len = 1 if edns >= 0 else 0

                    if rcode == 'NOERROR':
                        for r in response.answer:
                            answer_len += len(r) #计算答案部分的个数
                            r = str(r.to_text())
                            for i in r.split('\n'):  # 注意
                                i = i.split()
                                rc_domain, rc_type, rc_data, rc_ttl = i[0].rstrip('.'), i[3], i[4], i[1]
                                if rc_type == 'A':
                                    if rc_data.strip():
                                        ips_list.append('_'.join([rc_domain,rc_data, rc_ttl]))
                                elif rc_type == 'CNAME':
                                    if rc_data.strip():
                                        cnames_list.append('_'.join([rc_domain,rc_data[:-1].lower(), rc_ttl]))

                        for r in response.authority:
                            authority_len += len(r)
                            r = str(r.to_text())
                            for i in r.split('\n'):  # 注意
                                i = i.split()
                                rc_domain, rc_ttl, rc_type, rc_data = i[0][:-1].lower(), i[1], i[3], i[4]
                                # rc_data = rc_data if (rc_type =='A' or rc_type =='AAAA') else rc_data[:-1]
                                rc_data = rc_data if ((rc_type == 'A' or rc_type == 'AAAA') and rc_type != 'SOA') else rc_data[:-1]
                                if rc_type == 'SOA':
                                    rc_data = ' '.join(i[4:])
                                authority_data[rc_domain].append('_'.join([rc_ttl, rc_type, rc_data]))

                        for r in response.additional:
                            additional_len += len(r)
                            r = str(r.to_text())
                            for i in r.split('\n'):  # 注意
                                i = i.split()
                                rc_domain, rc_ttl, rc_type, rc_data = i[0][:-1].lower(), i[1], i[3], i[4]
                                # rc_data = rc_data if (rc_type == 'A' or rc_type == 'AAAA') else rc_data[:-1]
                                rc_data = rc_data if ((rc_type == 'A' or rc_type == 'AAAA') and rc_type != 'SOA') else rc_data[:-1]
                                if rc_type == 'SOA':
                                    rc_data = ' '.join(i[4:])
                                additional_data[rc_domain].append('_'.join([rc_ttl, rc_type, rc_data]))
                        ips_list.sort()
                        break
                    else:
                        continue
            except dns.resolver.NoAnswer:
                response_status = 'NoAnswer'
                response_time = time.time() - t1
                break
            except dns.resolver.NXDOMAIN:
                response_status = "NXDOMAIN"  # 尝试一次
                response_time = time.time() - t1
                break
            except dns.resolver.NoNameservers as e:
                if "REFUSED" in str(e):
                    response_status = 'REFUSED'  # 尝试一次
                else:
                    response_status = 'NoNameservers'
                response_time = time.time() - t1
                break
            except dns.resolver.Timeout:
                response_status = 'Timeout'
                response_time = time.time() - t1
            except dns.exception.Timeout:
                response_status = 'Timeout'
                response_time = time.time() - t1
            except asyncio.TimeoutError:
                response_status = 'asyncio Timeout'
                response_time = time.time() - t1
            except dns.exception.FormError:
                response_status = 'FormError'
                response_time = time.time() - t1
                break
            except Exception as e:
                if 'IPv6 addresses are 16 bytes long' == str(e):
                    response_status = 'IPv6 FormError'
                else:
                    response_status = 'OtherError:%s' % str(e)
                response_time = time.time() - t1
                break

        count_lengths = {
            "response_size": response_size,
            "answer_len": answer_len,
            "authority_len": authority_len,
            "additional_len": additional_len
        }

        auth_addition_data = {
            'auth_data': dict(authority_data),
            'addition_data': dict(additional_data)
        }
        auth_addition_data = dict(filter(lambda x: x[1], auth_addition_data.items())) #过滤掉空的数据

        return ips_list, cnames_list, response_status, edns, payload, nsid, count_lengths, req_flags,\
               str(response_time), auth_addition_data

    async def resolving_domain_ns_by_tld(self, domain, local_dns, sem):
        default_dns = False

        is_censor = False #标识域名是否为审查域名
        if domain.endswith('_censor'):
            domain = domain.rsplit('_', 1)[0]
            is_censor = True

        auth_servers = self.tld_ns_ips[domain.split('.')[-1]]
        ns_ip = random.choice(auth_servers)

        if local_dns == 'default_dns':
            default_dns = True
        async with sem:

                ipv4, cnames, ipv4_status, edns, payload, nsid, count_lengths, response_flags, \
                response_times, auth_addition_data = await self.query_ip_cname_ns_by_local_ns(domain, local_dns,
                                                     dns.rdatatype.A, default_dns, self.timeout, self.retry_time)


                ipv4_auth, cname_auth, authority_data_auth, additional_auth= \
                    await get_authoritative_nameserver(domain, ns_ip, self.timeout)

        auth_ns_data = {key: value for key, value in {
            'ipv4': ipv4_auth,
            'cname': cname_auth,
            'authority':authority_data_auth,
            'addition':additional_auth
        }.items() if value}

        data_result = {
            "task_id": self.task_id,
            "probe_ip": self.public_ip,
            "domain": domain,
            "is_censor": is_censor,
            "dns_ip": local_dns,
            "ipv4": json.dumps(ipv4),
            "cnames": json.dumps(cnames),
            'ipv4_status': ipv4_status,
            'edns': edns,
            'payload': payload,
            'nsid': nsid,
            'count_lengths': json.dumps(count_lengths),
            'response_flags': json.dumps(response_flags),
            'rtt_times':response_times,
            'ping_req_time': None,
            'auth_addition_data': json.dumps(auth_addition_data),
            'from_ns_data': json.dumps(auth_ns_data)
        }
        self.data_result.append(data_result)

    def run(self,coroutine_num):

        """
        :param target_list: list, 要查询的域名list
        :param q: queue(),进程之间传递结果的队列
        :param coroutine_num: int,协程数量，默认为500
        :return:

        """
        new_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(new_loop)
        loop = asyncio.get_event_loop()
        # 使用信号量控制协程数量，每轮协程处理这么多数据

        semaphore = asyncio.Semaphore(coroutine_num, loop=loop)
        tasks=[asyncio.ensure_future(self.resolving_domain_ns_by_tld(target[0],target[1],semaphore)) for target in self.task_list]
        loop.run_until_complete(asyncio.gather(*tasks))

        loop.close()
        semaphore.release()
        # print(self.process_name,'finished_task_num:',self.finished_task_num)
        # 最终结果存放在类中
        return self.data_result

def read_db_config():
    """读取探测节点的IP地址"""
    db_config = SystemConfigParse(conf_path).read_db_config()
    with open('shared_packages/db_config.json', 'r', encoding='utf-8') as f:
        config = json.loads(f.read())[db_config]
        return config

def insert_to_mysql(info):
    db_config = read_db_config()
    try:
        mysql = MySQL(db_config)
    except Exception as e:
        logger.logger.info('数据库连接失败：'+str(e))
        return

    try:
        table_name = datetime.now().strftime("%Y_%m_%d") + '_china_censor_resolution'
        sql = "insert into %s(task_id,probe_ip,domain,is_censor,dns_ip,ipv4,cnames," \
              "ipv4_status, edns, payload, nsid,count_lengths,response_flags,rtt_times, ping_req_time," \
              "auth_addition_data, from_ns_data) values (%s)" % (table_name, ','.join(['%s']*17))
        mysql.update_many(sql, info)
    except Exception as e:
        logger.logger.info(str(e))
    finally:
        mysql.close()

# 子进程类， 通过multiprocessing.Queue来把任务结果返回给主进程
class QueryProcess(Process):
    def __init__(self, process_name, tld_ns_ips, task_list,coroutine_num, timeout, retry_time, task_id=None, public_ip=None):
        Process.__init__(self)
        self.process_name = process_name
        self.tld_ns_ips = tld_ns_ips
        self.task_list = task_list
        self.coroutine_num=coroutine_num
        self.timeout = timeout
        self.retry_time = retry_time
        self.task_id = task_id
        self.public_ip = public_ip

        # logger.logger.info('进程%s,任务量:%s' % (self.process_name, str(len(task_list))))

    def sending_message(self, info):
        queue_name = 'save_to_mysql'
        exchange_name = 'get_probe_data'

        host_ip, username, pwd = SystemConfigParse(conf_path).read_rabbitmq_server()[0]
        user_pwd = pika.PlainCredentials(username, pwd)
        parameters = pika.ConnectionParameters(host_ip, credentials=user_pwd)

        try:
            s_conn = pika.BlockingConnection(parameters)  # 创建连接
            channel = s_conn.channel()
            channel.exchange_declare(
                exchange=exchange_name,
                exchange_type='direct',
                auto_delete=False,
            )
            channel.basic_publish(
                exchange=exchange_name,
                routing_key=queue_name,
                properties=pika.BasicProperties(  # 每个消息设置超时时间
                    expiration=str(30*60*1000), #消息超时时间，30分钟
                ),
                body=info)
            channel.close()
            s_conn.close()  # 当生产者发送完消息后，可选择关闭连接
            return True
        except Exception as e:
            logger.logger.error(str(e))
            return False

    def run(self):
        tnp = probe(self.process_name, self.tld_ns_ips, self.task_list, self.timeout, self.retry_time, self.task_id, self.public_ip)

        #探测解析事件循环
        result = tnp.run(self.coroutine_num)
        #ping命令事件循环
        dns_ping_time_dict = ping_status(self.task_list)

        for d in result:
            ping_time = dns_ping_time_dict[d['dns_ip']]
            resp_time = float(d['rtt_times'])
            if ping_time:
                diff_time = resp_time - ping_time
                d['ping_req_time'] = str(round(diff_time, 7))

        info = [tuple(d.values()) for d in result]
        #（1）探测数据直接入库
        insert_to_mysql(info)
        logger.logger.info('进程:%s结束，数据存储成功！' % self.process_name)

        #（2）探测数据传入消息队列，由内网服务器接收，再入库
        # compress_info = lzma.compress(json.dumps(info).encode())
        # f = self.sending_message(compress_info)
        #
        # if f:
        #     logger.logger.info('进程:%s结束，数据发送成功！' % self.process_name)
        # else:
        #     logger.logger.info('进程:%s 数据发送失败！' % self.process_name)
        #
        # print(result)

#obtain ping status
def ping_status(domain_dns_list):
    """ping目标，查看是否连通"""
    async def make_ping(target_ip, semaphore, ping_times=5, timeout=2):
        async with semaphore:
            ping_delay = 0
            success_n = 0
            for t in range(ping_times):
                try:
                    delay = await ping(target_ip, timeout)
                    if delay:
                        ping_delay += delay
                        success_n += 1
                except Exception:
                    continue
            if success_n:
                ping_delay = ping_delay / success_n

            return {target_ip: ping_delay}

    dns_list = []
    [dns_list.append(d[1]) for d in domain_dns_list]
    dns_list = list(set(dns_list))

    loop_ping = asyncio.new_event_loop()
    asyncio.set_event_loop(loop_ping)
    semaphore = asyncio.Semaphore(5)

    tasks = []
    for ip in dns_list:
        tasks.append(asyncio.ensure_future(make_ping(ip, semaphore)))
    result = loop_ping.run_until_complete(asyncio.gather(*tasks))

    dns_ping_time_dict = dict()

    for each in result:
        dns_ping_time_dict.update(each)

    return dns_ping_time_dict

# 主进程，负责任务下发子进程，结果打包
def allocating_task(dns_domain_list, tld_ns_ips, process_ratio = 3, coroutine_num=20, timeout=3, retry_time=2, task_id=None, public_ip=None):
    """

    :param tld_ns_ip_list: list, 要查询的域名list
    :param coroutine_num: int,协程数量，默认为500
    :return:

    """
    process_num = get_process_num(process_ratio)  # 探测点打开的进程数量

    avg_list = list_split(dns_domain_list, math.ceil(len(dns_domain_list) / process_num))
    try:
        p_list = []
        for i, each_list in enumerate(avg_list):
            p_list.append(QueryProcess('Process-{num}'.format(num=i), tld_ns_ips, each_list,coroutine_num, timeout, retry_time, task_id, public_ip))

        logger.logger.info('总共有%s个进程！' % str(len(p_list)))

        for p in p_list:
            p.start()
        for p in p_list:
            p.join()

    except Exception as e:
        logger.logger.error(str(e))

def read_focused_domains(country_name):
    """
    数据库中读取要监测的各个国家的域名信息
    """
    focused_domains, tlds = [], []

    base_url = 'dns_domain_list/domain_of_countries'
    country_path = os.listdir(base_url)
    for p in country_path:
        p_path = os.path.join(base_url, p)
        if os.path.isfile(p_path):
            country_path.remove(p)

    for c in country_path:
        if c == country_name:
            c_path = os.path.join(base_url, c, 'blocked_1m_merge_domain.json')
            with open(c_path, 'r', encoding='utf-8') as fp:
                focused_domains = json.loads(fp.read())
            break

    tlds = [d.split('.')[-1].split('_')[0] for d in focused_domains]

    return focused_domains, list(set(tlds))

def read_dns_servers(country_name, public_dns_count):
    """
    配置DNS列表
    """
    dns_servers = []

    #中国添加国内公共DNS与运营商DNS和测量点自身DNS;其他国家只有开放DNS和国外DNS
    if country_name == 'China':
        # 1.国内公共DNS
        public_dns = ['114.114.114.114', '180.76.76.76', '1.2.4.8', '119.29.29.29', '123.125.81.6']
        # 2.移动、电信、联通各选4个
        isp_dns = ["115.49.102.133", "111.160.120.242", "101.68.223.155", "110.53.163.188", "112.54.162.162",
                   "112.30.100.68", "112.2.18.43", "112.2.18.42", "106.122.201.119", "106.122.170.112", "1.202.140.166",
                   "101.227.182.100"]
        #3. 测量点默认DSN
        default_dns = ['default_dns']
    else:
        public_dns = []
        isp_dns = []
        default_dns = []

    #3.开放DSN
    base_url = 'dns_domain_list/dns_of_countries/public_dns_server.json'
    with open(base_url, 'r', encoding='utf-8') as fp:
        dns_info = json.loads(fp.read())[country_name][:public_dns_count]
        open_dns = [d[0] for d in dns_info]

    #4.国外公共DNS
    overseas_dns = ['8.8.8.8', '1.1.1.1', '9.9.9.9', '64.6.64.6', '208.67.222.2']

    dns_servers.extend(public_dns)
    dns_servers.extend(isp_dns)
    dns_servers.extend(default_dns)
    dns_servers.extend(open_dns)
    dns_servers.extend(overseas_dns)

    return list(set(dns_servers))

def read_tld_servers(tlds):
    """获取顶级域名的IPv4和IPv6地址"""
    # db_config = read_db_config()
    db_config = {
        "host": "ip address",
        "user": "root",
        "password": "",
        "db": "detect_dns_lc",
        "port": 36868,
        "charset": "utf8"
    }
    mysql = MySQL(db_config)
    sql = "SELECT tld, server_ipv4 FROM tld_servers_instance WHERE tld IN (%s)" % ','.join(["'%s'"] * len(tlds))
    sql = sql % tuple(tlds)
    mysql.query(sql)
    tld_data = mysql.fetchall()
    mysql.close()
    focused_tld_servers = {}
    for tld in tld_data:
        servers = []
        ip_set = tld['server_ipv4'].split(';')
        for ip in ip_set:
            if ip:
                servers.extend(ip.split(','))
        focused_tld_servers[tld['tld']] = servers
    return focused_tld_servers

def main():
    with open('shared_packages/task_id.json', 'r', encoding='utf-8') as fp:
        task_id = json.loads(fp.read())['task_id']

    public_ip = get_pub_ip()
    if not public_ip:  # 如果无法获取本地IP，则程序结束
        return

    country_name = 'china'
    focused_domains, tlds = read_focused_domains(country_name)
    dns_servers = read_dns_servers(country_name, 10)
    tld_ns_ips = read_tld_servers(tlds)

    # 测试
    # focused_domains = ['www.baidu.com']
    # dns_servers = ['42.159.153.39']

    domain_dns = list(itertools.product(focused_domains, dns_servers))
    random.shuffle(domain_dns)

    allocating_task(domain_dns, tld_ns_ips, process_ratio=2, coroutine_num=30, timeout=6, retry_time=2,
                    task_id=task_id, public_ip=public_ip)

    #修改taks_id的值
    with open('shared_packages/task_id.json', 'r+', encoding='utf-8') as fp:
        conf_data = json.load(fp)
        conf_data['task_id'] += 1
        fp.seek(0) #移动游标到开头
        fp.truncate() #清空文件所有内容
        json.dump(conf_data, fp)

def run_main():
    # schedule.every(5).minutes.do(main_test, task_id) #每个5分钟执行一次
    # schedule.every(5).seconds.do(main_test, task_id)   #每隔5秒执行一次
    #schedule.every().day.at("09:00").do(main, task_id)  # 设置每天在 10:00 执行 main() 函数

    schedule.every().day.at("08:00").do(main)
    schedule.every().day.at("14:00").do(main)
    schedule.every().day.at("20:00").do(main)

    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == '__main__':
    # run_main()

    count = 0
    while True:
        main()
        count += 1
        logger.logger.info('第----%s------轮次执行完成！' % count)
        if count % 3 ==0: #每次连续执行3次，然后再隔8小时执行
            # time.sleep(8*3600) #
            break
