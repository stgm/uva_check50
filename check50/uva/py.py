from check50.py import import_, compile
import check50.api
import contextlib
import io
import sys
import pathlib
import attr
import imp

class PythonException(check50.api.Failure):
	def __init__(self, exception):
		super().__init__(f"{exception.__class__.__name__}: {str(exception)} occured")
		self.exception = exception

@attr.s(frozen=True, slots=True)
class Result:
	stdout = attr.ib()
	stdin = attr.ib()
	module = attr.ib()

class _Stdin(io.StringIO):
	def write(self, text):
		check50.api.log("writing {} to stdin".format(text.replace('\n', '\\n')))
		super().write(text)

@contextlib.contextmanager
def capture_stdout():
	f = io.StringIO()
	with contextlib.redirect_stdout(f):
		yield f

@contextlib.contextmanager
def capture_stdin():
	old_stdin = sys.stdin
	sys.stdin = _Stdin()
	yield sys.stdin
	sys.stdin = old_stdin

@contextlib.contextmanager
def set_argv(*args):
	old_argv = sys.argv
	sys.argv = args
	yield sys.argv
	sys.argv = old_argv

def source(path):
	source = ""
	with open(path) as f:
		source = f.read()
	return source

def run(path, argv=tuple(), stdin=tuple(), set_attributes=(("__name__", "__main__"),)):
	"""
	Lets you run a python module while configuring argv, stdin, and attributes prior to running.
	path: the path of the file to run
	argv: list of argv arguments
	set_attributes: a list of tuples [(attribute, value), ...] that are set prior to running
	"""

	path = pathlib.Path(path)
	src = source(path)

	mod = None
	output = ""

	if not argv:
		argv = sys.argv

	with capture_stdout() as stdout_stream, capture_stdin() as stdin_stream, set_argv(*argv):
		# fill stdin with args
		if stdin:
			for arg in stdin:
				stdin_stream.write(str(arg) + "\n")
			stdin_stream.seek(0)

		moduleName = path.stem

		mod = imp.new_module(moduleName)

		# overwrite attributes
		for attr, value in set_attributes:
			setattr(mod, attr, value)

		try:
			# execute code in mod
			exec(src, mod.__dict__)
		except EOFError:
			raise check50.Failure("You read too much input from stdin")
		except BaseException as e:
			raise PythonException(e)

		# add resulting module to sys
		sys.modules[moduleName] = mod
		#except tuple(ignoreExceptions) as e:
		#	pass

		# wrap every function in mod with Function
		# for name, func in [(name, f) for name, f in mod.__dict__.items() if callable(f)]:
		# 	if func.__module__ == moduleName:
		#		setattr(mod, name, function.Function(func))

	return Result(stdout=stdout_stream.getvalue(), stdin=stdin_stream.read(), module=mod)
