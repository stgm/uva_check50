from check50.py import import_
import contextlib
import io

@contextlib.contextmanager
def capture_stdout():
    f = io.StringIO()
    with contextlib.redirect_stdout(f):
        yield f
