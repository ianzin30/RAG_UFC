"""Full application page with isolated, synthetic dependencies. Never a production mode."""
from pathlib import Path
import sys
import tempfile
sys.path[:0] = [str(Path(__file__).resolve().parents[2]), str(Path(__file__).resolve().parents[2] / 'application')]
import streamlit as st
import streamlit_audit_support as support

if support.ACTIVE is None:
    harness = support.Harness(tempfile.mkdtemp(prefix='spark-chat-ui-fixture-')).install()
    from presentation import Page
    from presentation.sidebar import FilesPanel
    harness.patches.append(__import__('unittest.mock', fromlist=['patch']).patch.object(Page, 'list_collection_documents',
        lambda:[{'collection':'audit','file_name':'atlas.md','relative_path':'atlas.md','label':'Atlas'}]))
    harness.patches[-1].start()
    harness.patches.append(__import__('unittest.mock', fromlist=['patch']).patch.object(Page, 'list_available_collections',lambda _:['audit']))
    harness.patches[-1].start()
    harness.patches.append(__import__('unittest.mock', fromlist=['patch']).patch.object(FilesPanel, '_active_collections_root',lambda:harness.docs))
    harness.patches[-1].start()
    harness.patches.append(__import__('unittest.mock', fromlist=['patch']).patch.object(FilesPanel, 'render_upload_dropzone',lambda:st.caption('Upload desabilitado nesta fixture sintética.')))
    harness.patches[-1].start()

with st.sidebar:
    st.caption('TESTE ISOLADO — dados sintéticos, sem Spark')
    support.ACTIVE.mode = st.selectbox('Cenário simulado', ['success','error','timeout','invalid_source','invalid_focus','empty'])
    support.ACTIVE.delay = 2

from application.app import main
main()
