# coding=utf-8
import ctypes as _ctp
import os as _os
import sys as _sys
import struct as _stu
from . import _comm_util as _cu
import collections as _coll
import threading as _th
import platform as _plt

__all__=['VseClient','VseError','FeatureTransformer','DataRecord']

assert _sys.version[0] == '3', 'python major version must be 3!'

#####################################################

def _s2b(strval):
    return strval.encode()

_dllname = 'vsepy_cimp'
_prefix = _os.path.split(_os.path.realpath(__file__))[0]
_system = _plt.system()
if _system=='Windows':
    _dll = _ctp.CDLL(_prefix + '/{}.dll'.format(_dllname))
elif _system=='Linux':
    _dll = _ctp.CDLL(_prefix + '/lib{}.so'.format(_dllname))
elif _system=='Darwin':
    _dll = _ctp.CDLL(_prefix + '/lib{}.dylib'.format(_dllname))
else:
    raise Exception("this platform {} is not supported!".format(_system))

_dll.transformer_init.restype = _ctp.c_void_p
_dll.transformer_transform.restype = _ctp.c_int32
_dll.transformer_get_param.restype = _ctp.c_int32

_SOCK_REUSE_FLG_DATA = _stu.pack('<i', 0x6666b003)

DataRecord = _coll.namedtuple('DataRecord', ('idx', 'sim', 'params'))

class VseError(Exception):
    """exception class for 'vse' sdk

        Attributes:

        :errc: err-code (int)
        :errs: err-message (string)
    """
    __slots__ = ('errc', 'errs')

    def __init__(self, errc, errs):
        self.errc = errc
        self.errs = errs

    def __str__(self):
        return repr(self.errc) + ',' + self.errs

    def __repr__(self):
        return 'VseError:' + self.__str__()


class FeatureTransformer(object):
    """特征转换类实例，提供vse所用特征的标准化转换"""
    __slots__ = ("__p",)
    __dl = _dll

    def __init__(self, client=None):
        # type: (str, VseClient) -> None
        """特征转换实例初始化。提供两种初始化方法：

        #. 基于datapath初始化。用户需要指定正确的datapath，为包含与检索引擎相同的bin文件所在目录。
        #. 基于client有效实例初始化。通过VseClient实例读取检索引擎所用的bin文件数据进行初始化（建议采用此方法）。
        """
        self.__p = None
        if client:
            assert isinstance(client, VseClient)
            data = client._get_trfm_param()
            p = self.__dl.transformer_init(data, _ctp.c_long(len(data)))
        else:
            raise Exception("no valid 'datapath' or 'client' param!")
        if not p:
            raise VseError(-1, 'c-impl: transformer_init failed')
        self.__p = _ctp.c_void_p(p)

    def __del__(self):
        if self.__p:
            self.__dl.transformer_free(self.__p)

    def __repr__(self):
        return 'FeatureTransformer({},{};{})@{}'.format(self.get_param(10),self.get_param(11),
            self.get_param(1),hex(self.__p.value))

    def get_param(self, pt):
        # type: (int) -> int
        return int( self.__dl.transformer_get_param(self.__p, _ctp.c_int32(pt)) )

    def tranform(self, rawfeat):
        # type: (bytes) -> bytes
        """执行特征转换（原生向量特征 -> 引擎标准化特征）

        :rawfeat: 原生向量二进制数据(bytes格式)
        :return: 标准化后的向量特征数据(bytes格式)，可用来入库、检索。
        """
        featlen = self.get_param(5)
        #print("featlen=",featlen)
        feat = b'\x00'*featlen
        rt = self.__dl.transformer_transform(self.__p, _ctp.c_char_p(rawfeat), _ctp.c_size_t(len(rawfeat)//4),
            feat)
        if rt:
            raise VseError(rt, b'input feature invalid')
        return feat
        

class _Long(int):
    pass

def _bstr_decode(bstr):  ##支持utf-8与gb2312
    # type: (bytes) -> str
    try:
        return bstr.decode()
    except UnicodeDecodeError:
        return bstr.decode('gb2312')

class VseClient(object):
    """Vse向量搜索引擎访问API类"""

    @staticmethod
    def __sock_recv_cmd(sock):
        d = _cu.sock_recv_all(sock, 4)
        if len(d) < 4:
            raise VseError(-10, 'error recv cmd-len. recvbytes={}'.format(len(d)))
        cmdlen = _stu.unpack('<i', d)[0]

        if cmdlen < 0 or cmdlen > 100000000:
            raise VseError(-1, "error parse 'cmdlen' ")
        rbt = _cu.sock_recv_all(sock, cmdlen)
        if len(rbt) < cmdlen:
            raise VseError(-3, 'recv cmd partially! read=' + str(len(rbt)) + 'when req=' + str(cmdlen))
        return rbt

    @staticmethod
    def __check_ret_err(sr: _cu.SeqReader2):
        retc = sr.rd_int()
        if retc != 0:
            errs = sr.rd_bstr()
            raise VseError(retc, _bstr_decode(errs))

    __tfm = {int: lambda val: (_stu.pack('<i', val),),
             float: lambda val: (_stu.pack('<f', val),),
             _Long: lambda val: (_stu.pack('<q', val),),
             bytes: lambda val: (_stu.pack('<i', len(val)), val,)}

    def __api_cmd_comm(self, cmdid, *sargs):
        # type: (int, ...) -> _cu.SeqReader2
        #sock = _cu.sock_conn_server(self.server_addr, self.conn_tmo)
        sock = self.__pool_get_sock()
        try:
            lst = [_stu.pack('<i', cmdid)]
            for a in sargs:
                lst.extend(self.__tfm[type(a)](a))
            ctx_len = sum(map(len,lst))
            lst.insert(0, _stu.pack('<i', ctx_len))
            bufcmd = b''.join(lst)
            sock.sendall(bufcmd)
            # sock.recv
            bufcmd = self.__sock_recv_cmd(sock)
            try:
                sock.sendall(_SOCK_REUSE_FLG_DATA)
                self.__pool_put_sock(sock)
                sock = None
            except:
                pass
                #print("_SOCK_REUSE_FLG_DATA send failed!")
            sr = _cu.SeqReader2(bufcmd)
            self.__check_ret_err(sr)
            return sr
        finally:
            if sock:
                sock.close()

        
    def __init__(self, addr, tmo=None):
        # type: (tuple, int|None) -> None
        """初始化实例并配置连接地址

        :addr: 以(ip,port)形式的网络地址，如：('127.0.0.1', 2018)
        :tmo: API访问连接超时时间（单位ms）。注意，VseClient实例下所有API均为阻塞模式工作，均支持多线程访问。
                当遇到网络拥塞或者业务执行过长情况，单个API可能执行时间长，可以通过此参数设置合理值。默认值为4000。
        """
        self.server_addr = addr or ('127.0.0.1', 2001)
        self.conn_tmo = tmo or 3000
        self._spool = _coll.deque(maxlen=16)
        self._lck = _th.Lock()

    def __pool_get_sock(self):
        with self._lck:
            if len(self._spool)>0:
                #print("reuse pop!!")
                return self._spool.pop()
        return _cu.sock_conn_server(self.server_addr, self.conn_tmo)
    
    def __pool_put_sock(self, sock):
        with self._lck:
            if len(self._spool)<self._spool.maxlen:
                self._spool.append(sock)
                #print("reuse push!!")
                return
        sock.close()

    def _get_trfm_param(self):
        # type: () -> bytes
        return self.__api_cmd_comm(1001).left_data()

    @staticmethod
    def __get_vse_recs(sr: _cu.SeqReader2):
        def _chkint(val, msg):
            if val < 0 or val > 1000000000:
                raise VseError(-2, msg + str(val))

        retc = sr.rd_int()
        _chkint(retc, 'error get ImgRecord.count')

        def _readparam():
            pct = sr.rd_int()
            _chkint(pct, 'error get ImgRecord.param_ct ')
            return [sr.rd_bstr() for _ in range(pct)]

        return [DataRecord(sr.rd_long(), sr.rd_float(), _readparam()) for _ in range(retc)]

    def enum_all_dbs(self):
        # type: () -> list[str]
        """枚举所有库

        :return: 所有库名列表
        """
        sr = self.__api_cmd_comm(3)
        return [sr.rd_bstr().decode() for _ in range(sr.rd_int())]

    def create_db(self, dbname):
        # type: (str) -> None
        """新创建一个库

        :dbname: 库名称（注意，库命名需要遵循变量命名规则，即：字母+数字+下划线，但是首字符需为字母）
        """
        assert isinstance(dbname,str)
        self.__api_cmd_comm(1, _s2b(dbname))
    
    def delete_db(self, dbname):
        # type: (str) -> None
        """删除一个库

        :dbname: 库名称（注意，删除前需要保证没有其他用户或者线程对当前库进行操作，否则可能引发异常）
        """
        assert isinstance(dbname,str)
        self.__api_cmd_comm(2, _s2b(dbname))

    def get_db_record_count(self, dbname):
        # type: (str) -> int
        """获得指定库里记录个数

        :dbname: 库名称
        :return: 本库的记录个数
        """
        assert isinstance(dbname,str)
        sr = self.__api_cmd_comm(65, _s2b(dbname))
        return sr.rd_long()

    def push_record(self, dbname, feat, bindpara=''):
        # type: (str, bytes, str) -> int
        """向指定库插入记录（特征&绑定数据）

        :dbname: 库名称
        :feat: 待入库的标准化特征数据（需FeatureTransformer.transform后的结果，非原生特征数据！）
        :bp: 绑定参数值列表（对于当前版本vse的绑定参数为定制化参数）
        :return: 记录uid值(>=0，库表级全局唯一)

        | 注：当前vse版本支持的binding-data共6个字段，分别为：uint64,int64,int64,float32,float32,str(255)

        对于输入参数bp来说：
            #. 可以留空，那么字段均按默认值(数字为0，字符串为空字串)
            #. 可以指定值，格式为以“|”符进行分隔的字符串。对于不指定的位置可以留空。如：'0|1|2|3.3|4.4|testhhh' 或 '\|87347\|\|5e3\|\|'
        """
        assert isinstance(dbname, str) and isinstance(feat, bytes)
        sr = self.__api_cmd_comm(10, _s2b(dbname), 1, feat, _s2b(bindpara))
        return sr.rd_long()
    
    def retrieve_records(self, dbname, feat, wherestmt='', min_sim=0.1, max_rec=8):
        # type: (str, bytes, str, float, int) -> list[tuple]
        """在指定库执行向量相似检索，返回按相似度（从高到低）排序后的结果

        :dbname: 库名称
        :feat: 待检索的标准化特征数据（需FeatureTransformer.transform后的结果，非原生特征数据！）
        :min_sim: 最小相似度阈值。特征相似度小于此阈值的结果将被过滤。
        :max_rec: 最大返回结果数。基于相似度排序和阈值过滤后结果数如果超过此值，将截断。
        :return: 检索结果记录的列表。外部容器为list，每条结果为一个tuple，具体格式为：(记录uid,相似度值,参数列表)。

        每个子项内容为:
                * 记录uid：同push_record返回值,delete_record参数值。为系统内分配的记录唯一id
                * 相似度值：值域为[0,1.0]的相似度得分值。对于完全相同的向量相似度为1，完全不相同的向量相似度为0
                * 参数列表：格式为list[bytes]的binding-data数据。与push_record插入到记录中的数据对应。对于当前版本vse，binding-data数量为6，格式可见push_record说明
        """
        assert isinstance(dbname, str) and isinstance(feat, bytes)
        sr = self.__api_cmd_comm(11, _s2b(dbname), 1, feat, _s2b(wherestmt), max_rec, float(min_sim))
        return self.__get_vse_recs(sr)

    def delete_record(self, dbname, ridx):
        # type: (str, int) -> None
        """根据索引删除记录

          :dbname: 数据库名
          :ridx: 待删除记录索引值
        """
        assert isinstance(dbname, str) and isinstance(ridx, int)
        self.__api_cmd_comm(14, _s2b(dbname), _Long(ridx))
    
    def delete_record_ws(self, dbname, ws):
        # type: (str, str) -> None
        assert isinstance(dbname, str) and isinstance(ws, str) 
        self.__api_cmd_comm(21, _s2b(dbname), _s2b(ws))

    def rt_test_io(self, dbname, chk_ct, io_ct):
        assert isinstance(dbname, str) and isinstance(chk_ct, int) and isinstance(io_ct, int)
        self.__api_cmd_comm(1200, dbname.encode(), chk_ct, io_ct)

    def scan_repair1(self, dbname):
        assert isinstance(dbname, str) 
        return self.__api_cmd_comm(1101, _s2b(dbname)).rd_int()


'''testing code'''

if __name__=='__main__':
    l= _Long(111)
    print(type(l))