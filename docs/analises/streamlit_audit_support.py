"""Isolated audit fixture; production presentation and persistence stay unmodified."""
from pathlib import Path
import copy
import importlib
import sys
import tempfile
import time
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'application'))
ACTIVE=None


class BrokenWrite:
    def write_text(self,*args,**kwargs):raise OSError('Synthetic storage failure')


class StoragePath:
    def __init__(self,path):self.path=Path(path)
    @property
    def parent(self):return self.path.parent
    def exists(self):return self.path.exists()
    def read_text(self,**kwargs):return self.path.read_text(**kwargs)
    def with_name(self,name):return BrokenWrite()
    def __str__(self):return str(self.path)


class Harness:
    def __init__(self,directory):
        self.root=Path(directory);self.root.mkdir(parents=True,exist_ok=True)
        self.docs=self.root/'collections';self.docs.mkdir(exist_ok=True)
        (self.docs/'atlas.md').write_text('# Atlas\nAtlas é financiado por Aurora.\n')
        self.storage=self.root/'chats.json'
        self.mode='success';self.endpoint='https://synthetic.invalid/a';self.delay=0
        self.fail_storage=False;self.during_call=None;self.calls=[];self.loads=[];self.models=[]
        self.instances=[];self.patches=[]
        self.config={'llm':{'provider':'vllm','model':'audit-A'},'rag_v2':{'device':'cpu'},
            'llm_models':{'options':[{'label':'Audit A','model_name':'audit-A'},{'label':'Audit B','model_name':'audit-B'}]}}

    def install(self):
        global ACTIVE
        ACTIVE=self
        from presentation.chat import Chat
        from presentation.chat_sessions import Storage
        from presentation.shared import MarkdownPreview
        from service import RuntimeConfig
        def replace(obj,name,value):
            p=patch.object(obj,name,value);p.start();self.patches.append(p)
        replace(RuntimeConfig,'_read_config_document',lambda:copy.deepcopy(self.config))
        RuntimeConfig.reset_runtime_config_cache()
        replace(Chat,'RAGService',FakeRAG)
        replace(Storage,'CHAT_STORAGE_PATH',self.storage)
        original_write=Storage._write
        def write(path,state):
            if self.fail_storage:raise OSError('Synthetic storage failure')
            return original_write(path,state)
        replace(Storage,'_write',write)
        replace(MarkdownPreview,'_collections_root',lambda collections_root=None:self.docs.resolve())
        return self

    def close(self):
        from service import RuntimeConfig
        for p in reversed(self.patches):p.stop()
        RuntimeConfig.reset_runtime_config_cache()

    def response(self):
        text='Atlas é financiado por Aurora.'
        source={'document_name':'Atlas','relative_path':'atlas.md','source':str(self.docs/'atlas.md'),
            'evidence_id':'E1','chunk_id':'C1','parent_id':'P1','excerpt':text,
            'provenance':[],'focus_spans':[{'start':text.index('Aurora'),'end':text.index('Aurora')+6,'quote':'Aurora','claim_ids':['K1']}],
            'focus_status':'focused'}
        result={'trace_version':2,'route':'retrieval','answer_text':text,'resolved_question':'Quem financia Atlas?',
            'status':'answered','sources':[copy.deepcopy(source)],'cited_sources':[copy.deepcopy(source)],
            'evidence':[{'evidence_id':'E1','parent_id':'P1','chunk_id':'C1','text':text}],
            'claims':[{'claim_id':'K1','evidence_ids':['E1'],'text':text}]}
        if self.mode=='empty':result['answer_text']='   '
        if self.mode in ('abstain','clarification'):
            result.update(answer_text='Não há evidência suficiente.' if self.mode=='abstain' else 'Qual projeto você quer consultar?',
                status='abstained' if self.mode=='abstain' else 'clarification_required',cited_sources=[],claims=[])
        if self.mode=='empty_sources':result['cited_sources']=[]
        if self.mode=='duplicate_sources':result['cited_sources']*=2
        if self.mode=='duplicate_distinct':result['cited_sources']+=[copy.deepcopy(result['cited_sources'][0])]
        if self.mode=='wrong_source':result['cited_sources'][0]['evidence_id']='E999'
        if self.mode=='invalid_source':result['cited_sources'][0]['provenance']=[None]
        if self.mode=='missing_file':result['cited_sources'][0].update(relative_path='missing.md',source='',source_name='missing.md',document_name='Missing')
        if self.mode=='invalid_focus':result['cited_sources'][0]['focus_spans']=[{'start':0,'end':5,'quote':'Aurora','claim_ids':['K1']}]
        return result


class FakeRAG:
    def __init__(self,model_name):
        self.h=ACTIVE;self.model_name=model_name;self.endpoint=self.h.endpoint
        self.collection=None;self.callback=None;self.h.instances.append(self)
    def set_model(self,model_name):self.model_name=model_name;self.h.models.append(model_name)
    def set_collection_progress_callback(self,cb):self.collection_cb=cb
    def load_collection(self,collections):
        self.collection=list(collections);self.h.loads.append(list(collections))
        if self.mode_is('load_error'):raise RuntimeError('Synthetic collection failure')
        if self.collection_cb:self.collection_cb({'event':'collection_cache_restored'})
    def mode_is(self,name):return self.h.mode==name
    def set_response_status_callback(self,cb):self.callback=cb
    def ask_question_with_trace(self,question,history):
        import streamlit as st
        self.h.calls.append({'question':question,'history':copy.deepcopy(history),'model':self.model_name,
            'endpoint':self.endpoint,'collection':copy.deepcopy(self.collection),
            'chat_id':st.session_state.active_chat_id,'logical_internal_calls':3})
        if self.callback:self.callback({'stage':'retrieval','message':'Buscando evidências sintéticas...'})
        if self.h.delay:time.sleep(self.h.delay)
        if self.h.during_call:self.h.during_call(st)
        if self.mode_is('timeout'):raise TimeoutError('Synthetic remote outcome unknown')
        if self.mode_is('error'):raise RuntimeError('Synthetic generation failure')
        return self.h.response()


def render():
    import streamlit as st
    from presentation import chat_sessions
    from presentation.chat import Chat
    from presentation.shared.SessionState import initialize_app_session_state
    st.set_page_config(page_title='Auditoria isolada do chat',layout='wide')
    initialize_app_session_state()
    chat_sessions.initialize_chat_sessions(default_collection=['audit'],default_model='audit-A')
    Chat.show(Chat.render_model_toolbar())


def visual_render():
    """Only used by an explicitly launched, local audit server."""
    import streamlit as st
    global ACTIVE
    if ACTIVE is None:Harness(tempfile.mkdtemp(prefix='streamlit-audit-ui-')).install()
    with st.sidebar:
        st.caption('DADOS SINTÉTICOS · SEM MODELO REAL')
        ACTIVE.mode=st.selectbox('Cenário',['success','error','timeout','empty','empty_sources','missing_file','invalid_focus','duplicate_sources','wrong_source','invalid_source','abstain','clarification'])
        ACTIVE.delay=st.slider('Espera simulada',0,5,2)
    from presentation.shared.Styles import apply_global_styles
    apply_global_styles('dark')
    render()
