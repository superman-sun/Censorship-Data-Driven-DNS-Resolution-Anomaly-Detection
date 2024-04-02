# encoding:utf-8
"""
日期：2023年08月18日
作者：chao li
"""
from datetime import datetime
from datetime import datetime
from ripe.atlas.cousteau import AtlasResultsRequest, AtlasCreateRequest
from ripe.atlas.cousteau import AtlasStopRequest
import requests
from ripe.atlas.cousteau import (
  Ping,
  Traceroute,
  AtlasSource,
  Dns
)
import time
import json
from ripe.atlas.cousteau import AtlasStream
from ripe.atlas.cousteau import AtlasLatestRequest
from ripe.atlas.sagan import Result
import base64
import dns.message
from collections import defaultdict
import traceback
import sys
import random
sys.path.append('.')
from shared_packages.Logger import Logger
from shared_packages.read_config import SystemConfigParse
from shared_packages.db_manage import MySQL
conf_path = 'shared_packages/system.conf'
logger = Logger(show_terminal=SystemConfigParse(conf_path).read_log_show())

ATLAS_API_KEY = "your own ripe measurement key"

def read_db_config():
    """读取探测节点的IP地址"""
    db_config = SystemConfigParse(conf_path).read_db_config()
    with open('shared_packages/db_config.json', 'r', encoding='utf-8') as f:
        config = json.loads(f.read())[db_config]
        return config

def stop_request():
    atlas_request = AtlasStopRequest(msm_id=1000001, key=ATLAS_API_KEY)
    (is_success, response) = atlas_request.create()
    print(is_success,response)

def get_result_by_sagan(measurement_id):
    #通过Sagan Library返回结果
    kwargs = {
        "msm_id": measurement_id
    }
    is_success, results = AtlasLatestRequest(**kwargs).create()

    if is_success:
        for result in results:
            new_result = Result.get(result)
            print(new_result.measurement_id)
            print(new_result.responses[0].abuf.edns0.options[0].nsid) #获取NSID
            # print(new_result.raw_data)

def get_result_from_stream(measurement_id):
    #通过回调获取测量结果
    def on_result_response(*args):
        """
        Function that will be called every time we receive a new result.
        Args is a tuple, so you should use args[0] to access the real message.
        """
        print(args[0])

    atlas_stream = AtlasStream()
    atlas_stream.connect()

    channel = "result"
    # Bind function we want to run with every result message received
    atlas_stream.bind_channel(channel, on_result_response)

    # Subscribe to new stream for a measurement results
    # stream_parameters = {"startTime": 1489568000, "stopTime": 1489569100, "msm": 30001}
    stream_parameters = {"msm": measurement_id, "sendBacklog":True}
    atlas_stream.start_stream(stream_type="result", **stream_parameters)

    # Timeout all subscriptions after 5 secs. Leave seconds empty for no timeout.
    # Make sure you have this line after you start *all* your streams
    # atlas_stream.timeout(seconds=5)
    # atlas_stream.timeout()
    # # Shut down everything
    # atlas_stream.disconnect()

    try:
        atlas_stream.timeout()
    except KeyboardInterrupt:
        print("Caught keyboard exit.")
    atlas_stream.disconnect()

def get_result(measurement_id):

    #1.获取测量的基本信息
    # url = 'https://atlas.ripe.net/api/v2/measurements/%s/' % measurement_id
    # measurement_info = requests.get(url).text
    # print(measurement_info)

    #2.获取测量结果
    # url = 'https://atlas.ripe.net/api/v2/measurements/%s/results/' % measurement_id
    # result_info = requests.get(url).text
    # print(result_info)

    #3.通过类AtlasResultsRequest请求测量结果

    #3.1无过滤条件
    kwargs = {  # 不过滤
        "msm_id": measurement_id
    }

    #3.2添加过滤条件
    # kwargs = { #可以通过添加起始时间以及测量点id，实行结果过滤
    #     "msm_id": 58771842,
    #     "start": datetime(2023, 8, 19),
    #     "stop": datetime(2023, 8, 20),
    #     # "probe_ids": [1, 2, 3, 4]
    # }

    is_success, results = AtlasResultsRequest(**kwargs).create()
    if is_success:
        return True, results
    else:
        return False, None

def wait_for_measurement_to_complete(msm_id):
    print('探测任务id：', msm_id)

    #1.第一种方法：调用cousteau类AtlasResultsRequest获取结果，两种方法获取结果一样
    while True:
        try:
            response = get_result(msm_id)
        except Exception as e:
            print(str(e))
            time.sleep(2)
        else:
            if response:
                return response
                break
        print('等待探测任务完成......')
        time.sleep(5)

    #2.第二种方法：通过获取结果对应的api url，来获取
    # atlas_url = 'https://atlas.ripe.net/api/v2/measurements/{}/'.format(msm_id)
    # while True:
    #     try:
    #         response = requests.get(atlas_url)
    #     except requests.URLRequired as e:
    #         print(str(e))
    #         time.sleep(5)
    #     except Exception as e:
    #         print(str(e))
    #         time.sleep(2)
    #     else:
    #         j = json.loads(response.text)
    #         if j['result']:
    #             response = requests.get(j['result']).text
    #             response = json.loads(response)  # 转为列表
    #             if response:
    #                 print(response)
    #                 break
    #         # 说明已经完成，这种方法有问题，实际探测已经结束，
    #         # 但是stop_time一直没有，需要等待时间很长，不建议使用
    #         # if j['stop_time']:
    #         #     #1.通过获取结果对应的api url，来获取
    #         #     rlt_url = j['result']
    #         #     response = requests.get(rlt_url).text
    #         #     response = json.loads(response) #转为列表
    #         #     print(response[0]['fw'])
    #         #     print(response)
    #         #     break
    #     print('等待任务完成........')
    #     time.sleep(5)


class Make_Measurement(object):
    def __init__(self,id):
        self.task_id = id
        self.measurements_list = []
        self.probes_list = []
        self.domain = None
        self.dns_ip = None
        self.domain_type = None
        self.msm_id = None
        self.ping_msm_id = None

    #获取已知测量ID,对应的结果
    def search_measurement_by_id(self, msm_id):
        url = 'https://atlas.ripe.net/api/v2/measurements/%s/results/' % msm_id
        return requests.get(url).text

    # 获取已知测量group ID,对应组内测量信息
    def search_measurment_info_by_group_id(self, group_id):
        url = 'https://atlas.ripe.net/api/v2/measurements/groups/%s' % group_id
        return requests.get(url).text

    # 1.1构造ping请求
    def make_ping_request(self, target_ip):
        ping_request = Ping(af=4, target=target_ip, description="testping")
        self.measurements_list.append(ping_request)

    #1.2 构造traceroute请求
    def make_traceroute_request(self):
        traceroute_request = Traceroute(
            af=4,
            target="www.ripe.net",
            description="testing",
            protocol="ICMP",
        )
        self.measurements_list.append(traceroute_request)

    #1.3 构造DNS请求
    def make_dns_request(self, domain, dns, query_type='A', nsid=True, payload=4096, rd=True, af=4, query_class='IN', description='dns request', ):
        self.dns_ip = dns
        self.domain = domain.rsplit('_', 1)[0]

        d_type = domain.rsplit('_', 1)[1]
        if d_type == 'n':
            self.domain_type = 0 #正常域名
        elif d_type == 'c':
            self.domain_type = 1 #审查域名
        elif d_type == 'b':
            self.domain_type = 2  #黑名单域名

        dns_request = Dns(
            af=af,
            description=description,
            query_class=query_class,
            query_type=query_type,
            query_argument=self.domain,
            target=dns,
            set_rd_bit=rd,
            set_nsid_bit=nsid,
            udp_payload_size=payload,
            retry=2
        )
        self.measurements_list.append(dns_request)

    #2构造测量点probe对象
    #2.1 按国家选测量点
    def choose_probe_from_country(self, country_name, probe_num=1):
        probe_from_country = AtlasSource(
            type = "country",
            value = country_name,
            requested = probe_num,
            status = 1,
            tags = {"include": ["system-ipv4-works"]}
        )
        self.probes_list.append(probe_from_country)
    #2.2 按地区选点，WW表示从全球选点
    def choose_probe_from_area(self, area_name="WW", probe_num=2): #默认WW为全球
        probe_from_area = AtlasSource(
            type = "area",
            value = area_name,
            requested = probe_num,
            tags = {"include": ["system-ipv4-works"]}
        )
        self.probes_list.append(probe_from_area)

    # 2.2 按ASN选点，WW表示从全球选点
    def choose_probe_from_asn(self, asn="58224", probe_num=1):  # 默认WW为全球
        probe_from_area = AtlasSource(
            type="asn", #area, country, prefix, asn, probes or msm
            value=asn,
            requested=probe_num,
            tags={"include": ["system-ipv4-works"]}
        )
        self.probes_list.append(probe_from_area)
    # 2.2 选择和之前探测任务相同的探测点
    def choose_probe_from_msm(self, msm_id):  # 默认WW为全球
        probe_from_area = AtlasSource(
            type="msm",
            value=msm_id,
            requested=1
        )
        self.probes_list.append(probe_from_area)

    def get_result(self, msm_id):
        kwargs = {  # 不过滤
            "msm_id": msm_id
        }
        is_success, results = AtlasResultsRequest(**kwargs).create()
        if is_success:
            return True, results
        else:
            return False, None

    def _wait_for_measurement_to_complete(self, msm_id):
        #调用cousteau类AtlasResultsRequest获取结果，两种方法获取结果一样
        while True:
            try:
                flag, response = self.get_result(msm_id)
            except Exception as e:
                print(str(e))
                time.sleep(5)
            else:
                if flag and response:
                    return response
            print('%s 任务等待完成......' % msm_id)
            time.sleep(10)

    #3.发送测量请求
    def make_measurment(self):
        atlas_request = AtlasCreateRequest(
            start_time=datetime.utcnow(),
            key=ATLAS_API_KEY,
            # measurements=[traceroute, dns_request], #可以多组测量
            measurements= self.measurements_list,
            # sources=[probe_from_country, probe_from_area], #可以设置多组测量点
            sources= self.probes_list,
            is_oneoff=True
        )

        is_success, response = atlas_request.create()

        if is_success:
            print('测量任务ID:', response['measurements'])
            measurement_id = response['measurements'][0]
            self.msm_id = measurement_id
            if len(self.measurements_list) == 1:
                # 第一种情况，只探测一个任务时，直接访问返回测量结果
                return self._wait_for_measurement_to_complete(measurement_id) # 等待探测任务完成，完成后获取测量结果

            elif len(self.measurements_list) > 1:
                # 第二种情况，如果一组中有多个探测则执行获取各个探测的任务ID数据
                group_url = 'https://atlas.ripe.net/api/v2/measurements/groups/%s' % measurement_id
                group_info = json.loads(requests.get(group_url).text)
                return group_info['group_members']
        else:
            measurement_id = None
            print('测量任务执行失败！')
            return False

    def _get_answer_from_abuf(self, response):
        ips_list, cnames_list = [], []
        response_status = False
        edns, payload, nsid = None, None, None
        answer_len, authority_len, additional_len = 0, 0, 0
        response_size, req_flags = None, None
        authority_data, additional_data = defaultdict(list), defaultdict(list)

        rcode = response.rcode()
        rcode = dns.rcode.to_text(rcode)
        response_status = rcode

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
                answer_len += len(r)  # 计算答案部分的个数
                r = str(r.to_text())
                for i in r.split('\n'):  # 注意
                    i = i.split()
                    rc_domain, rc_type, rc_data, rc_ttl = i[0].rstrip('.'), i[3], i[4], i[1]
                    if rc_type == 'A':
                        if rc_data.strip():
                            ips_list.append('_'.join([rc_domain, rc_data, rc_ttl]))
                    elif rc_type == 'CNAME':
                        if rc_data.strip():
                            cnames_list.append('_'.join([rc_domain, rc_data[:-1].lower(), rc_ttl]))

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

        auth_addition_data = dict(filter(lambda x: x[1], auth_addition_data.items()))  # 过滤掉空的数据

        data_result = {
            "ipv4": json.dumps(ips_list),
            "cnames": json.dumps(cnames_list),
            'ipv4_status': response_status,
            'edns': edns,
            'payload': payload,
            'nsid': nsid,
            'count_lengths': json.dumps(count_lengths),
            'response_flags': json.dumps(req_flags),
            'auth_addition_data': json.dumps(auth_addition_data),
        }

        return data_result

    def insert_to_mysql(self, table_name, info):
        db_config = read_db_config()
        try:
            mysql = MySQL(db_config)
        except Exception as e:
            logger.logger.info('数据库连接失败：' + str(e))
            return

        try:
            # table_name = datetime.now().strftime("%Y_%m_%d") + '_%s_censor_resolution' % country_name
            sql = "insert into %s(task_id,ping_msm_id,probe_ip,probe_info,domain,domain_type,dns_ip,ipv4,cnames," \
                  "ipv4_status, edns, payload, nsid,count_lengths,response_flags,rtt_times, ping_req_time," \
                  "auth_addition_data) values (%s)" % (table_name, ','.join(['%s'] * 18))
            # mysql.update(sql)
            mysql.update_many(sql, [info])
        except Exception as e:
            logger.logger.info(str(e))
        finally:
            mysql.close()

    #4.解码分析响应数据
    def analyze_dns_measurment_data(self, msm_rlt, ping_time, ping_task_id):
        #1.探测点信息
        probe_id = msm_rlt[0]['prb_id']
        probe_ip = msm_rlt[0]['from']
        #根据probe的ID获取探测点信息
        probe_url = 'https://atlas.ripe.net/api/v2/probes/%s' % probe_id
        resq_info = json.loads(requests.get(probe_url).text)
        probe_info = {
            'ip': probe_ip if resq_info['address_v4'] == probe_ip else resq_info['address_v4'],
            'country': resq_info['country_code'],
            'asn': resq_info['asn_v4'],
            'net_prefix': '_'.join(resq_info['prefix_v4'].split('/')),
            'description': resq_info['description'],
            'coordinates': resq_info['geometry']['coordinates']
        }

        #2.1响应结果提取
        msm_reuslt = msm_rlt[0].get('result', None)

        if msm_reuslt:
            resp_time = msm_reuslt['rt'] #响应时间
            # resp_size = msm_reuslt['size'] #响应报文大小
            # ans_count = msm_reuslt['ANCOUNT'] #answer部分的结果记录个数
            # auth_count = msm_reuslt['NSCOUNT'] #权威部分记录的个数
            # addition_count = msm_reuslt['ARCOUNT'] #附加部分记录的个数

            #2.2解析abuf中的结果数据
            abuf_rlt = dns.message.from_wire(base64.b64decode(msm_reuslt['abuf'])) #解析结果数据解码
            ans_dict = self._get_answer_from_abuf(abuf_rlt)
        else:
            error_info = msm_rlt[0].get('error', None) # {'Timeoute':5000}
            ans_dict = {
                "ipv4": None,
                "cnames": None,
                'ipv4_status': list(error_info.keys())[0] if error_info else None,
                'edns': None,
                'payload': None,
                'nsid': None,
                'count_lengths': None,
                'response_flags': None,
                'auth_addition_data': None
            }
            resp_time = list(error_info.values())[0] if error_info else None

        if resp_time and ping_time:
            diff_time = resp_time - ping_time #响应时延-ping的时延
        else:
            diff_time = None

        data_result = {
            "task_id": self.task_id,
            "ping_msm_id": str(ping_task_id),
            "probe_ip": probe_info['ip'],
            "probe_info": json.dumps(probe_info),
            "domain": self.domain,
            "domain_type": self.domain_type,
            "dns_ip": self.dns_ip,
            "ipv4": ans_dict['ipv4'],
            "cnames": ans_dict['cnames'],
            'ipv4_status': ans_dict['ipv4_status'],
            'edns': ans_dict['edns'],
            'payload': ans_dict['payload'],
            'nsid': ans_dict['nsid'],
            'count_lengths': ans_dict['count_lengths'],
            'response_flags': ans_dict['response_flags'],
            'rtt_times': str(resp_time),
            'ping_req_time': str(round(diff_time, 6)) if diff_time else diff_time,
            'auth_addition_data': ans_dict['auth_addition_data']
        }

        return data_result

    #获取ping的路径时延
    def get_ping_time(self, task_info, single_flag=True):
        ping_time, n = 0, 0
        if single_flag:
            ping_resp = task_info
            ping_rlt = ping_resp[0]['result']
            for t in ping_rlt:
                if list(t.keys())[0] == 'rtt':
                    ping_time += t['rtt']
                    n += 1
            ping_time = ping_time / n if n else ping_time
        else:
            for t in task_info:
                if t['type'] == 'ping':
                    ping_resp = self._wait_for_measurement_to_complete(t['id'])
                    ping_rlt = ping_resp[0]['result']
                    for t in ping_rlt:
                        if list(t.keys())[0] == 'rtt':
                            ping_time += t['rtt']
                            n += 1
                    ping_time = ping_time / n if n else ping_time
                    break
        return ping_time

def test():
    # 1.创建Ripe测量对象
    msm_task = Make_Measurement()

    # 2.构建查询内容
    msm_task.make_dns_request('www.baidu.com', '8.8.8.8')
    msm_task.make_ping_request()
    # 3.筛选测量点
    msm_task.choose_probe_from_country('US', 1)  # 国家要用缩写
    # 4.执行探测
    if len(msm_task.measurements_list) == 1:  # 只有一个探测任务时，直接返回探测结果
        msm_resp = msm_task.make_measurment()
        # 5.1 分析ping
        ping_time = msm_task.get_ping_time(msm_resp)
        # 5.2 分析DNS
        data_result = msm_task.analyze_dns_measurment_data(msm_resp, ping_time)
        #入库

    elif len(msm_task.measurements_list) > 1:  # 多个任务时，返回探测ID列表，逐个获取
        task_list = msm_task.make_measurment()
        # 5.数据分析入库
        if task_list is not False:
            # 5.1获取ping的时间
            ping_time = msm_task.get_ping_time(task_list)
            # 5.2分析DNS响应数据
            for t in task_list:
                if t['type'] == 'dns':
                    mes_resp = msm_task._wait_for_measurement_to_complete(t['id'])  # 等在获取DNS探测完成，获取响应数据
                    print(mes_resp)
                    data_result = msm_task.analyze_dns_measurment_data(mes_resp, ping_time)
                    # 入库
                    print(data_result)

def main():

    # countries = {
    #     'turkey': 'TR',
    #     'syria': 'SY',
    #     'egypt': 'EG',
    #     'iraq': 'IQ',
    #     'iran': 'IR',
    # }
    # 需要配置的参数如下：

    taks_id = 0

    probe_num = 1  # 筛选多个测量点

    ping_task_id = None
    # ping_task_id = '60355388'  #是否根据以前任务选探测点

    # asn = '58224' #用于按ASN选择测量点
    country_name = 'TR'  # 国家缩写，用于按国家选择测量点

    lower_country_name = 'turkey'  # 国家名称，小写
    upper_country_name = lower_country_name.capitalize()  # 将国家名首字母变成大写


    is_test = True # 是否进行测试, 正式测试时，应置为 False

    save_table_name = '2023_09_13_%s_censor_resolution' % lower_country_name  # 入库的表名
    # 测试
    if is_test:
        # domain_list = domain_list[:1]
        # dns_list = dns_list[:1]
        domain_list = ['facebook.com_b', 'youtube.com_b']
        dns_list = ['1.1.1.1', '8.8.8.8']
    else:
        # 读取需要测量的域名和DNS列表数据
        with open('dns_domain_list/domain_of_countries/final_res.json', 'r', encoding='utf-8') as fp:
            all_domains = json.loads(fp.read())
            domain_list = all_domains[lower_country_name]
            domain_list = list(set(domain_list))

        # dns_list = 提取DNS列表，多于3个dns的国家，随机选3个
        with open('dns_domain_list/dns_of_countries/edns_result_usa.json', 'r', encoding='utf-8') as fp:
            all_dns = json.loads(fp.read())
            dns_list = all_dns[upper_country_name]
            if len(dns_list) >= 2:
                dns_list = random.sample(dns_list, 10)  # 随机选个DNS进行测量
            dns_list = ['2.188.21.130', '5.200.200.200']
            # dns_list = ['193.227.29.32']
            overseas_dns = ['8.8.8.8', '1.1.1.1']
            dns_list.extend(overseas_dns)
            dns_list = list(set(dns_list))
            random.shuffle(dns_list)

    while True:
        for dns_ip in dns_list:
            ping_time = None
            timeout_n = 0
            while True:
                # 执行ping命令，获取ping路径时延
                msm_obj = Make_Measurement(taks_id)  # 使用同一对象名，利于执行完的对象自动释放
                msm_obj.make_ping_request(dns_ip)
                if ping_task_id:
                    msm_obj.choose_probe_from_msm(msm_id=ping_task_id)
                else:
                    msm_obj.choose_probe_from_country(country_name, probe_num)  # 保证一轮次中只有第一次选点，后面使用相同测量点
                    # msm_obj.choose_probe_from_asn(asn=asn, probe_num=probe_num)
                msm_resp = msm_obj.make_measurment()
                if msm_resp is not False:
                    ping_time = msm_obj.get_ping_time(msm_resp)
                    if ping_time > 0:
                        # print('ping: %s完成,ping_time：%s' % (msm_obj.msm_id, ping_time))
                        # 获取ping任务的测量ID,用于后续测量选择相同测量点
                        ping_task_id = msm_obj.msm_id
                        break
                    else:  # 若获取ping超时，则重试一次
                        timeout_n += 1
                        if timeout_n < 3:
                            print('ping超时，重测一次.....')
                            continue
                        else:
                            break
                else:  # ping任务创建失败后，继续创建，保证ping测量任务成功
                    continue

            # 测试
            # ping_task_id = 58964013
            # ping_time = 111.33

            # 执行DNS探测
            for domain in domain_list:
                try:
                    for i in range(2):  # 任务创建失败，尝试两次
                        msm_obj = Make_Measurement(taks_id)
                        msm_obj.make_dns_request(domain, dns_ip)
                        msm_obj.choose_probe_from_msm(msm_id=ping_task_id)  # 选择ping任务一样的测量点
                        msm_resp = msm_obj.make_measurment()

                        # 测试
                        # msm_resp = msm_obj._wait_for_measurement_to_complete(58959388)
                        # ping_time = 12.444

                        if msm_resp is not False:
                            data_rlt = msm_obj.analyze_dns_measurment_data(msm_resp, ping_time, ping_task_id)
                            print('dns任务: %s完成.' % msm_obj.msm_id)
                            # 入库
                            save_info = tuple(data_rlt.values())
                            # print(save_info)
                            msm_obj.insert_to_mysql(save_table_name, save_info)
                            print('%s 入库完成.' % msm_obj.msm_id)
                            break
                        else:
                            continue

                except Exception as e:
                    print(domain, dns_ip, msm_obj.msm_id)
                    print('错误信息：', traceback.format_exc())

                time.sleep(1)

            print('-' * 20)
        break
        # taks_id += 1
        # if taks_id > 2:
        #     break
        print('------1轮执行完成------')
    print('-----整体执行完成！-------')

def get_domain_test():
    taks_id = 0
    probe_num = 1  # 筛选多个测量点

    country_name = 'TR'  # 国家缩写，用于按国家选择测量点
    lower_country_name = 'turkey'  # 国家名称，小写
    upper_country_name = lower_country_name.capitalize()  # 将国家名首字母变成大写

    is_test = True  # 是否进行测试, 正式测试时，应置为 False

    save_table_name = '2023_09_13_%s_censor_resolution' % lower_country_name  # 入库的表名
    # 测试
    if is_test:
        # domain_list = domain_list[:1]
        # dns_list = dns_list[:1]
        domain_list = ['facebook.com_b', 'youtube.com_b']
        dns_list = ['1.1.1.1', '8.8.8.8']

    while True:
        for dns_ip in dns_list:
            ping_time = None
            timeout_n = 0
            # 执行DNS探测
            for domain in domain_list:
                try:
                    for i in range(2):  # 任务创建失败，尝试两次
                        msm_obj = Make_Measurement(taks_id)
                        msm_obj.make_dns_request(domain, dns_ip)
                        msm_obj.choose_probe_from_msm(msm_id=ping_task_id)  # 选择ping任务一样的测量点
                        msm_resp = msm_obj.make_measurment()

                        # 测试
                        # msm_resp = msm_obj._wait_for_measurement_to_complete(58959388)
                        # ping_time = 12.444

                        if msm_resp is not False:
                            data_rlt = msm_obj.analyze_dns_measurment_data(msm_resp, ping_time, ping_task_id)
                            print('dns任务: %s完成.' % msm_obj.msm_id)
                            # 入库
                            # save_info = tuple(data_rlt.values())
                            print(save_info)
                            # msm_obj.insert_to_mysql(save_table_name, save_info)
                            print('%s 入库完成.' % msm_obj.msm_id)
                            break
                        else:
                            continue
                except Exception as e:
                    print(domain, dns_ip, msm_obj.msm_id)
                    print('错误信息：', traceback.format_exc())

                time.sleep(1)

            print('-' * 20)
        break
        # taks_id += 1
        # if taks_id > 2:
        #     break
        print('------1轮执行完成------')
    print('-----整体执行完成！-------')

if __name__ == '__main__':
    main()

