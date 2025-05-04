from files_server import create_app
from gevent.pywsgi import WSGIServer

app = create_app('production')

if __name__ == '__main__':
    #app.run(host='0.0.0.0', port=5000) 
    server = WSGIServer(('0.0.0.0', 5000), app)
    server.serve_forever()