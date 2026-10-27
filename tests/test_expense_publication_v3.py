"""Publication must reject changed sources and preserve existing receipts."""
import json
from pathlib import Path
import pytest
from recovery import publish_expense_v3 as publisher


def configured(monkeypatch,tmp_path):
    src=tmp_path/'experiment';src.mkdir()
    baseline=tmp_path/'baseline.py';baseline.write_bytes(b'old')
    probes=tmp_path/'probes.py';probes.write_bytes(b'probe')
    (src/'task.py').write_bytes(b'new');(src/'turn-1').mkdir();(src/'turn-1/after.py').write_bytes(b'new')
    plan={'harness_sha256':publisher.sha((publisher.ROOT/'recovery/expense_feedback_v3.py').read_bytes()),'helper_sha256':{},'baseline_sha256':publisher.sha(b'old'),'probes_sha256':publisher.sha(b'probe')}
    (src/'plan.json').write_text(json.dumps(plan));(src/'result.json').write_text(json.dumps({'final_source_sha256':publisher.sha(b'new')}))
    for name,value in [('EXPERIMENT',src),('BASELINE',baseline),('PROBES',probes),('PUBLISH',tmp_path/'published')]:monkeypatch.setattr(publisher,name,value)
    return src,baseline


def test_changed_baseline_refuses_before_publication(monkeypatch,tmp_path):
    src,base=configured(monkeypatch,tmp_path);base.write_bytes(b'changed')
    with pytest.raises(ValueError,match='hash mismatch'):publisher.main()
    assert not publisher.PUBLISH.exists()


def test_existing_publication_is_never_deleted(monkeypatch,tmp_path):
    configured(monkeypatch,tmp_path);publisher.PUBLISH.mkdir();sentinel=publisher.PUBLISH/'receipt';sentinel.write_bytes(b'preserve')
    with pytest.raises(FileExistsError):publisher.main()
    assert sentinel.read_bytes()==b'preserve'
