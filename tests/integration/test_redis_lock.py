import time
from uuid import uuid4

import pytest
from redis import Redis
from redis.exceptions import LockNotOwnedError

from settings import settings

pytestmark = pytest.mark.infrastructure


def test_lock_excludes_concurrent_owner_and_expired_owner_cannot_release():
    redis = Redis.from_url(str(settings.dictionary_lock_url))
    name = f"test:lock:{uuid4()}"
    first = redis.lock(name, timeout=1, blocking=False)
    second = redis.lock(name, timeout=5, blocking=False)
    assert first.acquire()
    assert not second.acquire()
    time.sleep(1.05)
    assert second.acquire()
    with pytest.raises(LockNotOwnedError):
        first.release()
    second.release()
