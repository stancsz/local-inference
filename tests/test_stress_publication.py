import hashlib
import pytest
from stress.verify_publication import byte_identity


def test_fixture_identity_includes_actual_bytes_and_recorded_digest():
    raw=b'original\r\n'
    byte_identity(raw,raw,raw,hashlib.sha256(raw).hexdigest())


@pytest.mark.parametrize('changed',range(4))
def test_rejects_changed_published_original_index_or_recorded_digest(changed):
    raw=b'original\r\n'
    values=[raw,raw,raw,hashlib.sha256(raw).hexdigest()]
    values[changed]=b'original\n' if changed<3 else hashlib.sha256(b'other').hexdigest()
    with pytest.raises(ValueError):
        byte_identity(*values)
