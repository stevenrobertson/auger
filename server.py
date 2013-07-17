import json
import sys, pprint

from flask import Flask, render_template
from gevent.pywsgi import WSGIServer
from geventwebsocket.handler import WebSocketHandler
import tracer

app = Flask(__name__)
app.debug = True

@app.route('/')
def index():
  return render_template('index.html')

@app.route('/report.json')
def report():
  return open('/tmp/report.json').read()

@app.route('/coffee/<name>')
def coffee(name):
  return open('coffee/' + name).read()

def get_trace_log():
  import cPickle
  log = cPickle.load(open('/tmp/fizz.pickle'))
  #log = cPickle.load(open('/tmp/trace.pickle'))
  log.finalize()
  return log

@app.route('/code')
def get_code():
  log = get_trace_log()
  return render_template('code.html', enum_code=enumerate(log.code))

def find_vals(call):
  ret = []
  for ts, evt, arg in call.evts:
    if evt == 'val':
      ret.append(arg)
    elif evt == 'call':
      ret.extend(find_vals(arg))
  return ret

def convert_nested(log, call, ctx='', stack=(), mutefn=None):
  stack += (call.code,)
  ret = []
  ret.append(('call', ctx + '\\ ', '  %s # %s:%s' % (
    ' '.join([cmp.strip() for cmp in call.code.tb.code_context]),
    call.code.tb.filename, call.code.tb.lineno)))
  last_line = call.code.tb.lineno

  add_val = lambda arg: ret.append(('val', ctx + ' =  ',
        ' '.join(['%s=%s' % (k, v) for k, v in sorted(arg.items())])))

  for ts, evt, arg in call.evts:
    if evt == 'call':
      # TODO(strobe): Make this not reqire special handling. Ideally we would
      # want to mute all 'val' messages from muted functions _except_ tracer.val
      # itself.
      if mutefn and mutefn(arg.code):
        map(add_val, find_vals(arg))
      else:
        ret.extend(convert_nested(log, arg, ctx + ' |', stack, mutefn))
    elif evt == 'line':
      cls, ctx_ = '', ctx + ' |'
      if last_line < arg.lineno - 5:
        ret.append(('ellipsis', ctx_, '...'))
      elif last_line < arg.lineno:
        for i in range(last_line + 1, arg.lineno):
          ret.append(('skipped', ctx_, log.get_line(call.code, i)))
      elif last_line > arg.lineno:
        cls = 'backtrack'
        ctx_ = ctx + ' ^'
      ret.append((cls, ctx_, log.get_line(call.code, arg.lineno)))
      last_line = arg.lineno
    elif evt == 'return':
      if ret:
        last = ret.pop()
        ret.append(('ret', ctx + '/ ', last[2]))
    elif evt == 'val':
      add_val(arg)
  return ret

def mutefn(codecopy):
  # TODO(strobe): Make this extensible, obviously
  return any([
      codecopy.tb.filename == '<string>',
      'tracer.py' in codecopy.tb.filename,
    ])

@app.route('/code/fn/<code_id>')
@app.route('/code/fn/<code_id>/inv/<inv_pos>')
def get_code_fn(code_id, inv_pos=None):
  log = get_trace_log()
  code = log.code[int(code_id)]
  inv = (tracer.Invocation(code, int(inv_pos))) if inv_pos else log.invocations[code][0]
  lines = convert_nested(log, log.get_nested(inv.pos), mutefn=mutefn)

  caller_inv = log.get_caller(inv)
  caller_id = log.codemap.get(caller_inv.code) if caller_inv else None

  return render_template(
      'code_fn.html',
      code_id=code_id,
      inv=inv,
      caller_inv=log.get_caller(inv),
      caller_id=caller_id,
      fncode=lines,
      invocations=log.invocations[code])

def handle_websocket(ws):
  while True:
    message = ws.receive()
    if message is None:
      break
    else:
      message = json.loads(message)
      ws.send(json.dumps({'output': message}))

def root_handler(environ, start_response):
  path = environ['PATH_INFO']
  if path == '/ws':
    handle_websocket(environ['wsgi.websocket'])
  else:
    return app(environ, start_response)

if __name__ == "__main__":
  #srv = WSGIServer(('', 8001), root_handler, handler_class=WebSocketHandler)
  #srv.serve_forever()
  app.run(port=8001)
