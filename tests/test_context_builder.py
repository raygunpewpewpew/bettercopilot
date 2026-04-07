import os
import tempfile
from bettercopilot.context.project_detector import detect_project_type
from bettercopilot.context.file_selector import FileSelector


def test_context_detection_and_selection():
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, 'example.py')
        with open(p, 'w') as f:
            f.write('# sample')
        t = detect_project_type(d)
        assert t == 'python'
        sel = FileSelector(root=d)
        files = sel.select('python')
        assert any('example.py' in f for f in files)
