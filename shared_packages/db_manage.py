#!/usr/bin/python3
import json
import pymysql
import time

class MySQL(object):
    """对MySQLdb常用函数进行封装的类"""

    error_code = ''  # MySQL错误号码
    _instance = None  # 本类的实例
    _conn = None  # 数据库conn
    _cur = None  # 游标
    _TIMEOUT = 20  # 默认超时20秒
    _timecount = 2

    def __init__(self, db_config):
        """构造器：根据数据库连接参数，创建MySQL连接"""
        try:
            self._conn = pymysql.connect(host=db_config['host'],
                                         port=int(db_config['port']),
                                         user=db_config['user'],
                                         password=db_config['password'],
                                         db=db_config['db'],
                                         charset=db_config['charset'],
                                         cursorclass=pymysql.cursors.DictCursor)
        except pymysql.Error as e:
            # 如果没有超过预设超时时间，则再次尝试连接，
            if self._timecount < self._TIMEOUT:
                interval = 5
                self._timecount += interval
                time.sleep(interval)
                self.__init__(db_config)  # 重试
            else:
                raise e

        self._cur = self._conn.cursor()

    def get_cur(self):
        return self._conn

    def query(self, sql):
        """执行 SELECT 语句"""
        try:
            result = self._cur.execute(sql)  # 结果为查询到的数量
        except pymysql.Error as e:
            raise e
        return result

    def fetchall(self):
        """获取所有结果"""
        try:
            return self._cur.fetchall()
        except pymysql.Error as e:
            raise e

    def close(self):
        """关闭数据库连接"""
        try:
            self._cur.close()
            self._conn.close()
        except pymysql.Error as e:
            raise e

    def update(self,sql):
        """执行 UPDATE 及 DELETE 语句，无返回值"""
        try:
            self._cur.execute(sql)
            self._conn.commit()
        except pymysql.Error as e:
            raise e

    def update_many(self,sql, args):
        try:
            self._cur.execute("SET NAMES utf8")
            self._cur.executemany(sql, args)
            self._conn.commit()
        except pymysql.Error as e:
            raise e

    def execute_sql(self,sql):
        try:
            self._cur.execute(sql)
        except pymysql.Error as e:
            raise e

    def rollback(self):
        """数据库回滚操作"""
        self._conn.rollback()