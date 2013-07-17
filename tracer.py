import cPickle
import inspect
import os
import sys
import time
import types
from collections import namedtuple

CodeCopy = namedtuple('CodeCopy', 'tb code lnotab')
FramePos = namedtuple('FramePos', 'lineno lasti')
Invocation = namedtuple('Invocation', 'code pos')
Call = namedtuple('Call', 'code evts')

class Log(object):
    def __init__(self):
        self.log = []
        self.codemap = {}

        # Not populated until finalize() is called (should be called *after*
        # unpickling if that's your thing)
        self.code = []
        self.invocations = {}
        self.modules = {}

    def get_code_id(self, codecopy):
        return self.codemap.setdefault(codecopy, len(self.codemap))

    def stash_module(self, codecopy):
        fn = codecopy.tb.filename
        if fn not in self.modules:
            fp = fn.rsplit('.', 1)[0] + '.py'
            val = None
            if os.path.exists(fp):
                val = open(fp).read().split('\n')
            self.modules[codecopy.tb.filename] = val

    def get_line(self, codecopy, lineno):
      fn = codecopy.tb.filename
      m = self.modules.get(fn)
      return (m[lineno-1] if m and len(m) > lineno - 1
              else '<<%s line %s>>' % (fn, lineno))

    def get_caller(self, invocation):
      stack_depth = 0
      for i in range(invocation.pos - 1, -1, -1):
        ts, evt, arg = self.log[i]
        if evt == 'return':
          stack_depth += 1
        if evt == 'call':
          if stack_depth == 0:
            return Invocation(self.code[arg], i)
          stack_depth -= 1
      return None

    def add(self, event, val=None):
        self.log.append((time.time(), event, val))

    def finalize(self):
        revlist = sorted([(v, k) for k, v in self.codemap.items()])
        self.code = [k for v, k in revlist]
        assert all(map(lambda (k, v): self.code[v] == k, self.codemap.items()))

        for i, (ts, event, val) in enumerate(self.log):
            if event == 'call':
                code = self.code[val]
                self.invocations.setdefault(code, []).append(Invocation(code, i))

    def get_nested(self, startpos):
      return self._get_nested(startpos)[0]

    def _get_nested(self, startpos):
      ts, evt, arg = self.log[startpos]
      assert evt == 'call'
      code = self.code[arg]
      evts = []

      i = startpos + 1
      while i < len(self.log):
        ts, evt, arg = self.log[i]
        if evt == 'call':
          arg, i = self._get_nested(i)
        else:
          i += 1
        evts.append((ts, evt, arg))
        if evt == 'return':
          break
      return Call(code, tuple(evts)), i

class Tracer(object):
    def __init__(self, pickle_path=None, stash_modules=False):
        self.closed = False
        self.pickle_path = pickle_path
        self.stash_modules = stash_modules
        self.log = Log()

    def trace(self, frame, event, arg):
        if self.closed:
            return
        val = None
        if event == 'call':
            tb = inspect.getframeinfo(frame)
            tb = tb._replace(code_context=tuple(tb.code_context or ()))
            codecopy = CodeCopy(
                tb,
                frame.f_code.co_code,
                frame.f_code.co_lnotab,
            )
            val = self.log.get_code_id(codecopy)
            if self.stash_modules:
                self.log.stash_module(codecopy)

        elif event == 'line':
            val = FramePos(frame.f_lineno, frame.f_lasti)
        elif event == 'return':
            val = str(arg)
        self.log.add(event, val)
        return self.trace

    def val(self, **kwargs):
      self.log.add('val', kwargs)

    def hook(self):
        sys.settrace(self.trace)

    def unhook(self):
        sys.settrace(None)

    def flush(self):
        if self.closed or not self.pickle_path: return
        with open(self.pickle_path, 'w') as fp:
            cPickle.dump(self.log, fp)

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

def val(**kwargs):
  trace = sys.gettrace()
  if trace and hasattr(trace, 'im_self') and hasattr(trace.im_self, 'val'):
    trace.im_self.val(**kwargs)
