# coding=utf-8
"""
@author: ltmit
"""
import sys as _sys
import time
import threading as _th
import traceback as _tb
if _sys.version[0] == '2':
    import Queue as _que
else:
    import queue as _que

class AsyncHandler(_th.Thread):
    def __init__(self, que_size=0):
        _th.Thread.__init__(self)
        self._que = _que.Queue(que_size)
        self.quit_flag = 0

    def run(self):
        try:
            while not self.quit_flag:
                obj = self._que.get()
                if obj is None: break
                self.handle(obj)
            self.texit(None)
        except Exception as e:
            self.texit(e)

    def push(self, obj, block=True):
        if block:
            self._que.put(obj)
            return True
        else:
            try:
                self._que.put_nowait(obj)
                return True
            except:
                return False

    # callbacks
    def handle(self, obj):
        pass

    def texit(self, e):
        if e:
            print(e)


class ReadWriteLock(object):
    def __init__(self):
        self.__monitor = _th.Lock()
        self.__exclude = _th.Lock()
        self.__readers = 0

    def acquire_read(self):
        with self.__monitor:
            self.__readers += 1
            if self.__readers == 1:
                self.__exclude.acquire()

    def release_read(self):
        with self.__monitor:
            self.__readers -= 1
            if self.__readers == 0:
                self.__exclude.release()

    def acquire_write(self):
        self.__exclude.acquire()

    def release_write(self):
        self.__exclude.release()

    def rlock(self):  # for 'with' statement
        class _rlw:
            def __init__(self, rw):
                self.__rw = rw

            def __enter__(self):
                self.__rw.acquire_read()

            def __exit__(self, typ, val, trac):
                self.__rw.release_read()
                return False

        return _rlw(self)

    def wlock(self):
        class _wlw:
            def __init__(self, rw):
                self.__rw = rw

            def __enter__(self):
                self.__rw.acquire_write()

            def __exit__(self, typ, val, trac):
                self.__rw.release_write()
                return False

        return _wlw(self)


'''---------------------------------------------'''


class TaskPool:
    def __init__(self, thread_ct=4, que_size=4):
        self.__que = _que.Queue(que_size)
        self.__threads = []

        def tproc(q):
            while True:
                e = q.get()
                try:
                    e.proc()
                finally:
                    q.task_done()

        while thread_ct > 0:
            t = _th.Thread(target=tproc, args=(self.__que,))
            self.__threads.append(t)
            t.setDaemon(True)
            t.start()
            thread_ct -= 1
            # print t

    def push_task(self, task, block=True):
        """task class need to implement 'proc()' method"""
        self.__que.put(task, block)

    def push_task_fb(self, func, *args):
        class _dumtask:
            def proc(self):
                try:
                    func(*args)
                except:
                    _tb.print_exc()
                    exit(1)
        self.__que.put(_dumtask(), True)

    def join(self):
        # print self.__que.qsize()
        self.__que.join()


class TimerClz(_th.Thread):
    def __init__(self, intval):
        _th.Thread.__init__(self)
        self._intval = intval

    def timer_proc(self):
        pass

    def run(self):
        while 1:
            time.sleep(self._intval)
            if self.timer_proc() == StopIteration:
                break

    def start_timer(self):
        self.setDaemon(True)
        _th.Thread.start(self)


if __name__ == '__main__':
    class testt(TimerClz):
        def __init__(self):
            TimerClz.__init__(self, 0.8)

        def timer_proc(self):
            print(time.time())


    t = testt()
    t.start_timer()
    time.sleep(11)
