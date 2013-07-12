import json
import sys

from flask import Flask, render_template
from gevent.pywsgi import WSGIServer
from geventwebsocket.handler import WebSocketHandler

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

class Tracer(object):
  def __init__(self):
    self.log = []

  def trace(self, frame, event, arg):
    self.log.append((frame, event, arg))
    return self.trace

  def dump(self, fn):
    import cPickle
    with open(fn, 'w') as fp:
      cPickle.dump(self.log, fp)

if __name__ == "__main__":
  tracer = Tracer()
  sys.settrace(tracer.trace)

  try:
    srv = WSGIServer(('', 8001), root_handler, handler_class=WebSocketHandler)
    srv.serve_forever()
  finally:
    tracer.dump('/tmp/out.foo')
