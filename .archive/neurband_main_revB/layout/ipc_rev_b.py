"""Rev B layout tooling using the selected runtime's exact IPC descriptor."""
import os
from pathlib import Path
import json, uuid
from google.protobuf import descriptor_pb2, descriptor_pool, message_factory, json_format
import pynng

ROOT = Path(__file__).resolve().parents[3]
PCB = ROOT / 'boards/neurband_main/neurband_main.kicad_pcb'
RUNTIME = Path(os.environ.get('KICAD_ROOT', os.path.expanduser('~/.backplane-bend/kicad/10.99.0-bp.4')))
POOL = descriptor_pool.DescriptorPool()
fds = descriptor_pb2.FileDescriptorSet.FromString((RUNTIME/'share/backplane/api.desc').read_bytes())
pending = list(fds.file)
while pending:
    old = len(pending)
    for f in pending[:]:
        try: POOL.Add(f); pending.remove(f)
        except Exception: pass
    if len(pending) == old: raise RuntimeError('Unresolved descriptor dependencies')
def cls(name): return message_factory.GetMessageClass(POOL.FindMessageTypeByName(name))
def nm(x): return round(x*1e6)
def xy(x,y): return {'x_nm':str(nm(x)), 'y_nm':str(nm(y))}
def uid(): return {'value':str(uuid.uuid4())}
class IPC:
    def __init__(self):
        self.socket=pynng.Req0(dial='ipc:///run/user/1000/backplane/kicad/9634c94bd0de95fb/api.sock',recv_timeout=120000,send_timeout=120000)
        self.token=''
        self.doc={'type':'DOCTYPE_PCB','board_filename':PCB.name,'project':{'name':'neurband_main','path':str(PCB.parent)+'/'}}
    def call(self,name,data={}):
        msg=cls(name)(); json_format.ParseDict(data,msg,descriptor_pool=POOL)
        req=cls('kiapi.common.ApiRequest')(); req.header.client_name='works.neurband.revB'; req.header.kicad_token=self.token; req.message.Pack(msg)
        self.socket.send(req.SerializeToString()); resp=cls('kiapi.common.ApiResponse').FromString(self.socket.recv())
        self.token=resp.header.kicad_token
        if resp.status.status != 1: raise RuntimeError(str(resp.status))
        if not resp.message.type_url or resp.message.type_url.endswith('/google.protobuf.Empty'):return {}
        result=cls(resp.message.type_url.split('/')[-1]).FromString(resp.message.value)
        return json_format.MessageToDict(result,preserving_proto_field_name=True,descriptor_pool=POOL)
    def get(self,types):
        return self.call('kiapi.common.commands.GetItems',{'header':{'document':self.doc},'types':types}).get('items',[])
    def begin(self):
        self.commit=self.call('kiapi.common.commands.BeginCommit',{'header':{'document':self.doc}})['id']
        (PCB.parent/'layout/build/ipc-commit.json').write_text(json.dumps(self.commit))
        return self.commit
    def end(self,description):
        return self.call('kiapi.common.commands.EndCommit',{'header':{'document':self.doc},'id':self.commit,'action':'CMA_COMMIT','message':description})
    def save(self): return self.call('kiapi.common.commands.SaveDocument',{'document':self.doc})
    def create(self,items):
        out=self.call('kiapi.common.commands.CreateItems',{'header':{'document':self.doc},'items':items})
        bad=[x for x in out.get('created_items',[]) if x.get('status',{}).get('code')!='ISC_OK']
        if bad: raise RuntimeError(str(bad)[:2000])
        return out
    def update(self,items): return self.call('kiapi.common.commands.UpdateItems',{'header':{'document':self.doc},'items':items})
    def delete(self,ids):
        if not ids:return {}
        return self.call('kiapi.common.commands.DeleteItems',{'header':{'document':self.doc},'item_ids':[{'value':x} for x in ids]})
if __name__=='__main__':
    import sys
    ipc=IPC()
    if len(sys.argv)>1:
        data=json.loads(sys.argv[2]) if len(sys.argv)>2 else {}
        if data.pop('_board',False):data['board']=ipc.doc
        print(json.dumps(ipc.call(sys.argv[1],data),indent=2))
    else:
        print(json.dumps(ipc.call('kiapi.backplane.GetCapabilities'),indent=2))
