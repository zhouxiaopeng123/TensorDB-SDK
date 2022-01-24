# coding=utf-8
"""
common API client component
for ISE /CnnExtractor /...
"""
import comm_util as _cu
import struct as _stu
import collections as _coll


class ApiError(Exception):
    """
        exception class for comm-Apis
    """

    def __init__(self, errc, errs):
        self.errc = errc
        self.errs = errs

    def __str__(self):
        return '{},{}'.format(self.errc, self.errs)

    def __repr__(self):
        return 'ApiError:' + self.__str__()


# Face Record for 3-elem part
FaceRecord3e = _coll.namedtuple('FaceRecord3e', ('idx', 'sim', 'sc_all', 'sc_top', 'sc_bot', 'params'))


class ApiCli:
    """
        'ISE'/'CnnExtractor' raw-tcp api
    """

    @staticmethod
    def __sock_recv_cmd(sock):
        d = _cu.sock_recv_all(sock, 4)
        if len(d) < 4:
            raise ApiError(-10, 'error recv cmd-len. recvbytes={}'.format(len(d)))
        cmdlen = _stu.unpack('<i', d)[0]

        if cmdlen < 0 or cmdlen > 100000000:
            raise ApiError(-1, "error parse 'cmdlen' ")
        rbt = _cu.sock_recv_all(sock, cmdlen)
        if len(rbt) < cmdlen:
            raise ApiError(-3, 'recv cmd partially! read=' + str(len(rbt)) + 'when req=' + str(cmdlen))
        return rbt

    ################################################################
    def __init__(self, addr=None, tmo=None):
        """
        Constructor
        """
        self.server_addr = addr or ('127.0.0.1', 2001)
        self.conn_tmo = tmo or 3000

    @staticmethod
    def __check_ret_err(sr: _cu.SeqReader2):
        retc = sr.rd_int()
        if retc != 0:
            errs = sr.rd_bstr()
            raise ApiError(retc, errs.decode())

    __tfm = {int: lambda val: (_stu.pack('<i', val),),
             float: lambda val: (_stu.pack('<f', val),),
             bytes: lambda val: (_stu.pack('<i', len(val)), val,)}

    def __api_cmd_comm(self, cmdid, *sargs):
        # type: (int, ...) -> _cu.SeqReader2
        sock = _cu.sock_conn_server(self.server_addr, self.conn_tmo)
        try:
            lst = []
            for a in sargs:
                lst.extend(self.__tfm[type(a)](a))
            content = b''.join(lst)
            bufcmd = b''.join((_stu.pack('<i', len(content) + 4), _stu.pack('<i', cmdid), content))
            sock.sendall(bufcmd)
            # sock.recv
            bufcmd = self.__sock_recv_cmd(sock)
            sr = _cu.SeqReader2(bufcmd)
            self.__check_ret_err(sr)
            return sr
        finally:
            sock.close()

    '''________________________________________'''

    def rt_get_all_db(self):
        sr = self.__api_cmd_comm(3)
        return [sr.rd_bstr().decode() for _ in range(sr.rd_int())]

    def rt_create_db(self, dbname):
        assert isinstance(dbname, str)
        self.__api_cmd_comm(1, dbname.encode())

    def rt_delete_db(self, dbname):
        assert isinstance(dbname, str)
        self.__api_cmd_comm(2, dbname.encode())

    def rt_push_face_fea(self, dbname, ftype, facefeat, paradata):
        assert isinstance(dbname, str) and isinstance(ftype, int) and \
               isinstance(facefeat, bytes) and isinstance(paradata, str)
        sr = self.__api_cmd_comm(10, dbname.encode(), ftype, facefeat, paradata.encode())
        return sr.rd_long()

    def rt_get_rec_ct(self, dbname):
        assert isinstance(dbname, str)
        sr = self.__api_cmd_comm(65, dbname.encode())
        return sr.rd_long()

    @staticmethod
    def __get_face_recs3(sr: _cu.SeqReader2):
        def _chkint(val, msg):
            if val < 0 or val > 1000000000:
                raise ApiError(-2, msg + str(val))

        retc = sr.rd_int()
        _chkint(retc, 'error get ImgRecord.count')

        def _readparam():
            pct = sr.rd_int()
            _chkint(pct, 'error get ImgRecord.param_ct ')
            return [sr.rd_bstr() for _i in range(pct)]

        return [FaceRecord3e(sr.rd_long(), sr.rd_float(), sr.rd_float(), sr.rd_float(), sr.rd_float(),
                             _readparam()) for _j in range(retc)]

    def rt_retrieve_face_3e(self, dbname, ftype, facefeat, where_stmt, min_sim=0.1, max_rec=8):
        # type: (str, int, bytes, str, float, int) -> list
        assert isinstance(dbname, str) and isinstance(ftype, int) and \
               isinstance(facefeat, bytes) and isinstance(where_stmt, str)
        sr = self.__api_cmd_comm(111, dbname.encode(), ftype, facefeat, where_stmt.encode(), max_rec, min_sim)
        return self.__get_face_recs3(sr)

    def rt_retrieve_face(self, dbname, facefeat, where_stmt, min_sim=0.1, max_rec=8):
        assert isinstance(dbname, str) and isinstance(facefeat, bytes) and isinstance(where_stmt, str)
        sr = self.__api_cmd_comm(11, dbname.encode(), 1, facefeat, where_stmt.encode(), max_rec, min_sim)
        def _chkint(val, msg):
            if val < 0 or val > 1000000000:
                raise ApiError(-2, msg + str(val))
        retc = sr.rd_int()
        _chkint(retc, 'error get ImgRecord.count')
        def _readparam():
            pct = sr.rd_int()
            _chkint(pct, 'error get ImgRecord.param_ct ')
            return [sr.rd_bstr() for _i in range(pct)]
        return [(sr.rd_long(), sr.rd_float(), _readparam()) for _j in range(retc)]
    
    def rt_test_io(self, dbname, chk_ct, io_ct):
        assert isinstance(dbname, str) and isinstance(chk_ct, int) and isinstance(io_ct, int)
        self.__api_cmd_comm(1200, dbname.encode(), chk_ct, io_ct)

    #############################################################

    def ff_extract_feat(self, ftype, imgdata):
        assert isinstance(ftype, int) and isinstance(imgdata, bytes)
        sr = self.__api_cmd_comm(802, ftype, imgdata)
        return sr.rd_bstr()

if __name__=='__main__':
    import async_util as _au
    import time,threading as _th
    pool = _au.TaskPool(8)
    lock = _th.Lock()
    cli = ApiCli(('127.0.0.1', 2021), 4000)
    sco = [0,0,0,0]
    t1=time.time()
    for _ in range(2000):
        def _task(sc):
            tc1=time.time()
            cli.rt_test_io('test_dilu_2kw',16,400)
            tu=time.time()-tc1
            with lock:
                sc[0]+=1
                sc[1]+=tu
        pool.push_task_fb(_task, sco)
    pool.join()
    t2=time.time()
    print("QPS=",sco[0]/(t2-t1), "avg-time(ms)=",1000.0*sco[1]/sco[0])   
    
