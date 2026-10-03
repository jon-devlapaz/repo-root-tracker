"""Disposable bonsai review server. All data is synthetic and stays in memory.

python tests/serve_bonsai_review.py --port 7856 --case quiet
"""
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from urllib.parse import urlparse, parse_qs
from bonsai_review import DASHBOARD, fixture_data


def serve(port, case, pixel_tree=False):
    data=fixture_data(case)
    dashboard=DASHBOARD.read_text()
    if pixel_tree:
        from pixel_bonsai_preview import pixel_dashboard
        dashboard=pixel_dashboard(dashboard)
    organization={'version':1,'revision':0,'exists':False,'pins':[],'collections':[],
                  'assignments':{},'grouping':'collection','sort':'name'}
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            url=urlparse(self.path)
            if url.path=='/':
                body=dashboard.replace('__HOME__','/review',1).encode()
                kind='text/html; charset=utf-8'
            else:
                if url.path=='/api/repos':
                    value=[{'path':p} for p in data]
                elif url.path=='/api/repos/status':
                    value=data.get(parse_qs(url.query).get('path',[''])[0],{'error':'Unknown fixture'})
                elif url.path=='/api/repo':
                    value={'path':parse_qs(url.query).get('path',[''])[0],'branch':'main','commits':[],'branches':[],'changed_files':[]}
                elif url.path=='/api/organization':
                    value=organization
                elif url.path=='/api/github':
                    value={'has_github':False}
                else:
                    value=[]
                body=json.dumps(value).encode();kind='application/json'
            self.send_response(200);self.send_header('Content-Type',kind)
            self.end_headers();self.wfile.write(body)
        def do_PUT(self):
            if urlparse(self.path).path!='/api/organization':
                self.send_error(405);return
            payload=json.loads(self.rfile.read(int(self.headers.get('Content-Length','0'))))
            organization.update({k:v for k,v in payload.items() if k!='base_revision'})
            organization.update(revision=organization['revision']+1,exists=True)
            self.send_response(200);self.send_header('Content-Type','application/json');self.end_headers()
            self.wfile.write(json.dumps(organization).encode())
        def log_message(self,*args):
            pass
    print(f'Synthetic {case} board: http://127.0.0.1:{port}/#/board',flush=True)
    ThreadingHTTPServer(('127.0.0.1',port),Handler).serve_forever()


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--port',type=int,default=7856)
    parser.add_argument('--case',choices=['quiet','crowded','attention'],default='quiet')
    parser.add_argument('--pixel-tree',action='store_true',help='Try the pixel family on cedar and its worktree')
    args=parser.parse_args();serve(args.port,args.case,args.pixel_tree)
