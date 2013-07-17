# A "simple" program so unnecessarily complicated that I can't trivially
# debug it. Mostly a self-test; if/when the tool gets good enough to make
# this program's behavior obvious, then we're probably on to something.

import json, pprint
from collections import namedtuple

import tracer

Event = namedtuple('Event', 't type val')
Sample = namedtuple('Sample', 'y')
LayerSample = namedtuple('LayerSample', 'y0 y')

class Peekable(object):
    def __init__(self, stream):
        self.stream = stream
        self.peekVal = next(self.stream, None)

    def next(self):
        if self.peekVal is None:
            raise StopIteration
        oldVal = self.peekVal
        self.peekVal = next(self.stream, None)
        return oldVal

class AttributeGetter(object):
    def __init__(self, stack=(), elide=True):
        self.___stack = stack
        self.___elide = elide
    def __getattr__(self, name):
        return AttributeGetter(self.___stack + (name,), self.___elide)
    def __getitem__(self, idx):
        return AttributeGetter(self.___stack + (idx,), self.___elide)
    def __call__(self, obj):
        for name in self.___stack:
            if not obj:
                return None
            elif isinstance(name, int):
                obj = obj[name]
            elif isinstance(obj, dict):
                obj = obj.get(name)
            else:
                obj = getattr(obj, name, None)
        return obj
getter = AttributeGetter()

def argmin(method, things):
    return sorted(things, key=method)[0] if things else None

class PushStream(object):
    def __init__(self, force):
        self.force = force
        self.queue = []
        self.closed = False
    def push(self, val):
        self.queue.append(val)
    def close(self):
        self.closed = True
    def next(self):
        while not self.queue and not self.closed:
            self.force()
        if self.closed:
            raise StopIteration
        return self.queue.pop(0)
    def __iter__(self):
        return self

def forceable(fn):
    def wrap(*args, **kwargs):
        queue = []
        gen = None
        def force():
            queue.append(next(gen))
        gen = fn(force, *args, **kwargs)
        while True:
            if queue:
                yield queue.pop(0)
            else:
                yield next(gen)
    return wrap

@forceable
def layer_stream_samples(force, stream_stream, get_samples):
    stream = next(stream_stream, None)
    if not stream: return
    window = [(Peekable(get_samples(stream)), PushStream(force))]
    yield stream, window[0][1]

    def runUntil(window, maxt=None):
        while window:
            next_in_stream, next_out_stream = argmin(getter[0].peekVal, window)
            next_evt = next_in_stream.peekVal
            if maxt is not None and next_evt.t >= maxt:
                break
            y0 = 0
            for in_stream, out_stream in window:
                in_evt = in_stream.peekVal
                out_stream.push(Event(next_evt.t, 'LayerSample',
                    LayerSample(y0, in_evt.val.y)))
                y0 += in_evt.val.y
            next(next_in_stream)
            if next_in_stream.peekVal is None:
                next_out_stream.close()
                window = filter(lambda (in_s, out_s): in_s.peekVal is not None, window)
        return window

    for new_stream in stream_stream:
        in_sample_stream = Peekable(get_samples(new_stream))
        out_sample_stream = PushStream(force)
        window = runUntil(window, maxt=in_sample_stream.peekVal.t)
        window.append((in_sample_stream, out_sample_stream))
        yield stream, out_sample_stream
    runUntil(window)

lasttracer = None

def main():
    data = json.load(open('static/reports/report-10025.json'))
    req_stream = (x for x in sorted(data, key=lambda x: x.get('startOffset')))
    for in_val, out in layer_stream_samples(req_stream,
        lambda req: (Event(req['startOffset'] + s['timeSinceStart'],
                           'Sample', Sample(s['loaded']))
                           for s in req['samples'])):
        pprint.pprint(list(iter(out)))

lasttracer = None

if __name__ == "__main__":
    lasttracer = tracer.Tracer('/tmp/trace.pickle', stash_modules=True)
    with lasttracer:
        main()
