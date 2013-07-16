import cPickle
import inspect
import sys
import time
import types
from collections import namedtuple

CodeCopy = namedtuple('CodeCopy', 'filename name code lnotab')
FramePos = namedtuple('FramePos', 'lineno lasti')

class Log(object):
    def __init__(self):
        self.log = []
        self.codemap = {}

        # Not populated until finalize() is called (should be called *after*
        # unpickling if that's your thing)
        self.code = []
        self.invocations = {}

    def get_code_id(self, codecopy):
        return self.codemap.setdefault(codecopy, len(self.codemap))

    def add(self, event, val=None):
        self.log.append((time.time(), event, val))

    def finalize(self):
        revlist = sorted([(v, k) for k, v in self.codemap.items()])
        self.code = [k for v, k in revlist]
        assert all(map(lambda (k, v): self.code[v] == k, self.codemap.items()))

        for i, (ts, event, val) in enumerate(self.log):
            if event == 'call':
                code = self.code[val]
                self.invocations.setdefault(code, []).append(i)

class Tracer(object):
    def __init__(self, pickle_path=None):
        self.closed = False
        self.pickle_path = pickle_path
        self.log = Log()
    def trace(self, frame, event, arg):
        if self.closed:
            return
        val = None
        if event == 'call':
            fi = inspect.getframeinfo(frame)
            if fi.code_context:
                fi = fi._replace(code_context=tuple(fi.code_context))
            codecopy = CodeCopy(
                fi,
                frame.f_code.co_firstlineno,
                frame.f_code.co_code,
                frame.f_code.co_lnotab,
            )
            val = self.log.get_code_id(codecopy)
        elif event == 'line':
            val = FramePos(frame.f_lineno, frame.f_lasti)
        elif event == 'return':
            val = str(arg)
        self.log.add(event, val)
        return self.trace

    def hook(self):
        sys.settrace(self.trace)

    def unhook(self):
        sys.settrace(None)

    def flush(self):
        if self.closed or not self.pickle_path: return
        with open(self.pickle_path, 'w') as fp:
            cPickle.dump(self.log, fp)
        print 'flushed'

    def close(self):
        self.closed = True

    def __enter__(self):
        self.hook()

    def __exit__(self, exc_type, exc_value, traceback):
        self.unhook()
        self.flush()

    def __del__(self):
        if self.closed: return
        try:
            self.flush()
        except:
            pass
