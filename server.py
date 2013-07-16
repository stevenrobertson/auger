import json
import sys

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
  log = cPickle.load(open('/tmp/trace.pickle'))
  log.finalize()
  return log

@app.route('/code')
def get_code():
  log = get_trace_log()
  return render_template('code.html', code=enumerate(log.code))

@app.route('/code/fn/<code_id>')
def get_code_fn(code_id):
  log = get_trace_log()
  code = log.code[int(code_id)]

  print code

  return render_template('code_fn.html', code_id=code_id,
      invocations=log.invocations[code])

@app.route('/code/fn/<code_id>/inv/<inv_id>')
def get_code_fn_inv(code_id, inv_id):
  log = get_trace_log()
  code = log.code[int(code_id)]

  return render_template('code_fn.html', code_id=code_id,
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
