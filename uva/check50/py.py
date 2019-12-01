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
import requests
import json

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

def validate_html(file_html, strict=False, prefix=""):
	"""
	Validate the HTML in the provided file using the W3C Validation Service
	Returns a check50.failure exception if the HTML is invalid
	file_html: the path to the file to validate, or the raw html to validate
	strict: whether or not warnings should raise a failure exception
	prefix: a prefix to add to log and failure messages
	"""

	# check whether file or html was provided
	if(os.path.exists(f"./{file_html}")):
		# file
		data = open(file, 'r').read()
	else:
		# raw html
		data = file_html

	# url, headers, timeout
	url = "https://validator.w3.org/nu/"
	private_url = url + "?out=json"
	headers = {"Content-type": "text/html; charset=utf-8", "Accept": "application/json"}
	timeout = 10

	error_message = prefix + "validator returned an unexpected error, please contact your TA"
	unvailable_message = prefix + "validator unavailable, please try again later or contact your TA"

	# run validator service
	check50.log(prefix + "Running W3C validator.")
	try:
		request = requests.post(private_url, data=data, headers=headers, timeout=timeout)
	except requests.exceptions.Timeout:
		check50.log(prefix + "validator timed out")
		raise check50.Failure(unavailable_message)
	except Exception as e:
		check50.log(prefix + f"request raised an exception: {e}")
		raise check50.Failure(error_message)

	# get JSON response
	response_data = request.json()

	# catch unexpected API errors
	if request.status_code != 200:
		check50.log(prefix + f"Validator unexpectedly returned status code {request.status_code}. {response_data["reason"]}")
		raise check50.Failure(error_message)
	
	# start with no errors and warnings
	error_count = 0
	warning_count = 0

	# get each message, count errors and warnings
	for message in response_data["messages"]:
		error_count += 1 if message["type"] == "error"
		warning_count += 1 if message["type"] == "info" and message["subtype"] == "warning"

		# handle non-document errors
		if message["type"] == "non-document-error":
			check50.log(prefix + f"validator returned a non-document-error: {message["message"]}")
			raise check50.Failure(error_message)

	check50.log(prefix + f"Found {error_count} errors and {warning_count} warnings.")
	hint = f"validate your HTML yourself and view the detailed errors and warnings at {url}"

	# throw exceptions if HTML is invalid
	if strict and (warning_count > 0 or error_count > 0):
		raise check50.Failure(prefix + f"validator returned {error_count} errors and {warning_count} warnings", hint=hint)
	elif error_count > 0:
		raise check50.Failure(prefix + f"validator returned {error_count} errors", hint=hint)