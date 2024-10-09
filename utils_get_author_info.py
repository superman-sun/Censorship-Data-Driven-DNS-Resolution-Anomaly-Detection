# encoding:utf-8
"""
日期：2023年05月29日
作者：李超
"""
import dns
import tldextract
import random
from collections import defaultdict
import asyncio
import async_timeout
from dns.asyncresolver import Resolver


async def get_authoritative_nameserver(domain, tld_ns_ip, resolve_timeout):
    src_domain = domain
    n = dns.name.from_text(domain)
    depth = 3  # 从域名的第三级开始，包括根，例如www.baidu.com，则是从baidu.com.进行探测

    # 如果域名深度大于3，查看注册域名是否和探测域名一致，如果一直，该域名是直接注册在顶级的，可以直接向顶级获
    # 取NS信息，无需向下一级请求
    ext = tldextract.extract(domain)
    register_domain = ext.registered_domain.strip()

    # if len(n.labels) > 3 and (register_domain != domain):  # 当域名深度大于3(即三级及以上域名)，且注册域名不等于原域名，探测时探测注册域名，而不是原域名
    domain = register_domain
    n = dns.name.from_text(domain)
    # 配置递归DNS服务器
    default_dns_resolver = dns.asyncresolver.Resolver(configure=False)  # 测试其
    default_dns_resolver.timeout = resolve_timeout  # 默认2s
    # default_dns_resolver.lifetime = 4 #默认为4s，当请求时间超过timeout时间，但没有超过lifetime，则会重试请求；当总的请求时间超过lifetime时，报超时异常
    # 国内公共dns
    nameservers = ['114.114.114.114', '1.2.4.8', '119.29.29.29', '180.76.76.76']
    # 国外公共dns
    # nameservers = ['8.8.8.8', '1.1.1.1', '9.9.9.9', '208.67.222.222']
    random.shuffle(nameservers)
    default_dns_resolver.nameservers = nameservers

    nameserver =  tld_ns_ip
    is_last = False

    ns_ipv4 = []  # 声明

    while not is_last:
        domain_ns = []  # 每次循环初始化
        ns_ipv4 = []  # 每次循环初始化
        # nameserver = None

        s = n.split(depth)
        sub_domain = str(s[1])[:-1]

        query = dns.message.make_query(sub_domain, dns.rdatatype.NS, use_edns=True)

        for i in range(2):
            try:
                async with async_timeout.timeout(resolve_timeout * 2 * 3) as cm:
                    response = await dns.asyncquery.udp_with_fallback(query, nameserver, timeout=4,
                                                                      ignore_unexpected=True)
                    response = response[0]
                    rcode = response.rcode()
                    if rcode != dns.rcode.NOERROR:
                        if rcode == dns.rcode.NXDOMAIN:
                            # return ns_ipv4
                            break
                        else:
                            # return ns_ipv4
                            break

                    # ns存在authority或者answer字段中
                    if len(response.authority) > 0:
                        response_rc = response.authority
                    elif len(response.answer) > 0:
                        response_rc = response.answer
                    else:
                        break

                    for r in response_rc:
                        for i in str(r.to_text()).split('\n'):
                            i = i.split()
                            rc_domain, rc_ttl, rc_type, rc_data = i[0], i[1], i[3], i[4]
                            if rc_type == 'NS':
                                if rc_data.strip() and rc_domain[:-1] == sub_domain:
                                    ns_name = rc_data[:-1].lower()
                                    domain_ns.append(ns_name)
                    # ipv4地址
                    for r in response.additional:
                        for i in str(r.to_text()).split('\n'):
                            i = i.split()
                            rc_name, rc_ttl, rc_type, rc_data = i[0].lower()[:-1], i[1], i[3], i[4]
                            if rc_name in domain_ns and rc_type == 'A':
                                if rc_data.strip():  # 特别注意，有A记录才记录
                                    ns_ipv4.append(rc_data)
            except dns.exception.Timeout:
                # return ns_ipv4
                continue
            except asyncio.TimeoutError:
                # return ns_ipv4
                continue
            except Exception as e:
                # return ns_ipv4
                break

        if not domain_ns:
            break
        else:
            ns_ips = list(set(ns_ipv4))
            if ns_ips:
                nameserver = random.choice(ns_ips)
            else:
                authority_ns = random.choice(domain_ns)
                try:
                    async with async_timeout.timeout(resolve_timeout * 2 * 3) as cm:
                        nameserver_ans = await default_dns_resolver.resolve(authority_ns, 'A')
                    for tmp_nameserver in nameserver_ans:
                        nameserver = str(tmp_nameserver)
                        break
                except Exception as e:
                    break

        is_last = s[0].to_unicode() == u'@'  # 是否到最后一级
        depth += 1  # 下一级

    return await get_resolution_data(src_domain, [nameserver], resolve_timeout)

async def get_resolution_data(domain, tld_ns_ips, resolve_timeout):
    #获取域名最近权威服务器
    ipv4, cname, authority_data, additional_data = [], [], defaultdict(list), defaultdict(list)
    if tld_ns_ips:
        ques_a = dns.message.make_query(qname=domain, rdtype=dns.rdatatype.A)
        # ques_aaaa = dns.message.make_query(qname=domain, rdtype=dns.rdatatype.AAAA)

        for i in range(2):
            result_a = []
            auth_ns = random.choice(tld_ns_ips)
            try:
                async with async_timeout.timeout(resolve_timeout*2*3):
                    result_a = await dns.asyncquery.udp_with_fallback(q=ques_a, where=auth_ns, timeout=resolve_timeout,
                                                            ignore_unexpected=True)
            except Exception as e:
                pass
            if not result_a:
                continue
            else:
                if result_a:
                    response = result_a[0]
                    # print(response)
                    for r in response.answer:
                        r = str(r.to_text())
                        for i in r.split('\n'):  # 注意
                            i = i.split()
                            rc_domain, rc_type, rc_data, rc_ttl = i[0][:-1], i[3], i[4], i[1]
                            if rc_type == 'A':
                                if rc_data.strip():
                                    ipv4.append('_'.join([rc_domain,rc_data,rc_ttl]))
                            elif rc_type == 'CNAME':
                                if rc_data.strip():
                                    cname.append('_'.join([rc_domain,rc_data[:-1],rc_ttl]))

                    if len(response.authority) > 0:
                        for r in response.authority:
                            r = str(r.to_text())
                            for i in r.split('\n'):  # 注意
                                i = i.split()
                                rc_domain, rc_ttl, rc_type, rc_data = i[0][:-1].lower(), i[1], i[3], i[4]
                                # rc_data = rc_data if (rc_type =='A' or rc_type =='AAAA') else rc_data[:-1]
                                rc_data = rc_data if ((rc_type == 'A' or rc_type == 'AAAA') and rc_type != 'SOA') else rc_data[:-1]
                                if rc_type == 'SOA':
                                    rc_data = ' '.join(i[4:])
                                authority_data[rc_domain].append('_'.join([rc_ttl, rc_type, rc_data]))
                    if len(response.additional) > 0:
                        for r in response.additional:
                            r = str(r.to_text())
                            for i in r.split('\n'):  # 注意
                                i = i.split()
                                rc_domain, rc_ttl, rc_type, rc_data = i[0][:-1].lower(), i[1], i[3], i[4]
                                # rc_data = rc_data if (rc_type == 'A' or rc_type == 'AAAA') else rc_data[:-1]
                                rc_data = rc_data if ((rc_type == 'A' or rc_type == 'AAAA') and rc_type != 'SOA') else rc_data[:-1]
                                if rc_type == 'SOA':
                                    rc_data = ' '.join(i[4:])
                                additional_data[rc_domain].append('_'.join([rc_ttl, rc_type, rc_data]))

                break

    ipv4.sort()
    cname = list(set(cname))
    cname.sort()

    return ipv4, cname, dict(authority_data), dict(additional_data)

if __name__ == '__main__':
    # d = 'news.china.com'
    # x = tldextract.TLDExtract(cache_dir=False)(d)
    # x2 = tldextract.extract(d)
    # print(x.registered_domain.strip())
    # print(x2.registered_domain.strip())
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop = asyncio.get_event_loop()
        semaphore = asyncio.Semaphore(500, loop=loop)
        domain_dns_list=['www.cdb.com.cn']
        tld_ns= {
            'cn':'203.119.25.1',
            'com':'192.5.6.30'
        }

        futures = [asyncio.ensure_future(get_authoritative_nameserver(k,tld_ns['cn'], 3)) for k in domain_dns_list]
        rlt = loop.run_until_complete(asyncio.gather(*futures))
        semaphore.release()
        loop.close()
        print(rlt)
    except Exception as e:
        raise e
        print(str(e))