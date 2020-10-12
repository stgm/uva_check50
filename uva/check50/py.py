from check50.py import import_, compile
import check50
import contextlib
import io
import sys
import pathlib
import attr
import os
import imp
import subprocess
import ast
import types

class PythonException(check50.Failure):
	def __init__(self, exception):
		super().__init__(f"{exception.__class__.__name__}: {str(exception)} occured")
		self.exception = exception

class NotebookError(check50.Failure):
	pass

@attr.s(frozen=True, slots=True)
class Result:
	stdout = attr.ib()
	stdin = attr.ib()
	module = attr.ib()

class _Stdin(io.StringIO):
	def write(self, text):
		check50.log("writing {} to stdin".format(text.replace('\n', '\\n')))
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
	sys.argv = list(args)
	yield sys.argv
	sys.argv = old_argv

def source(path):
	source = ""
	with open(path) as f:
		source = f.read()
	return source

def nbconvert(notebook, dest=None):
	notebook = pathlib.Path(notebook)
	if dest == None:
		dest = notebook.with_suffix('')
	else:
		dest = pathlib.Path(dest).with_suffix('')

	check50.log(f"converting {notebook} to {dest.with_suffix('.py')}")

	# convert notebook
	with open(os.devnull, "w") as devnull:
		if subprocess.call([sys.executable, '-m', 'nbconvert', '--to', 'script', notebook, "--output", dest], stdout=devnull, stderr=devnull) != 0:
			raise NotebookError("Could not convert notebook.")

	dest = dest.with_suffix(".py")

	# remove all magic lines
	with open(dest, "r") as f:
		lines = f.readlines()
	with open(dest, "w") as f:
		f.write("".join([l for l in lines if "get_ipython" not in l]))

def run(path, argv=tuple(), stdin=tuple(), set_attributes=(("__name__", "__main__"),)):
	"""
	Lets you run a python module while configuring argv, stdin, and attributes prior to running.
	path: the path of the file to run
	argv: list of argv arguments
	set_attributes: a list of tuples [(attribute, value), ...] that are set prior to running
	"""

	path = pathlib.Path(path)
	src = source(path)
	tree = ast.parse(src)

	for node in tree.body[:]:
    	if not isinstance(node, ast.FunctionDef):
        	tree.body.remove(node)

	code = compile(p, "mod.py", 'exec')

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

		check50.log(f"importing {moduleName}")
		mod = imp.new_module(moduleName)

		# overwrite attributes
		for attr, value in set_attributes:
			setattr(mod, attr, value)

		try:
			# execute code in mod
			exec(code, mod.__dict__)
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