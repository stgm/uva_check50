import check50
import os
import requests
import json

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
		data = open(file, 'rb').read()
	else:
		# raw html
		data = file_html.encode()

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
		check50.log(prefix + f"Validator unexpectedly returned status code {request.status_code}. {response_data['reason']}")
		raise check50.Failure(error_message)
	
	# start with no errors and warnings
	error_count = 0
	warning_count = 0

	# get each message, count errors and warnings
	for message in response_data["messages"]:
		if message["type"] == "error":
			error_count += 1
		if message["type"] == "info":
			warning_count += 1

		# handle non-document errors
		if message["type"] == "non-document-error":
			check50.log(prefix + f"validator returned a non-document-error: {message['message']}")
			raise check50.Failure(error_message)

	check50.log(prefix + f"Found {error_count} errors and {warning_count} warnings.")
	hint = f"validate your HTML yourself and view the detailed errors and warnings at {url}"

	# throw exceptions if HTML is invalid
	if strict and (warning_count > 0 or error_count > 0):
		raise check50.Failure(prefix + f"validator returned {error_count} errors and {warning_count} warnings", help=hint)
	elif error_count > 0:
		raise check50.Failure(prefix + f"validator returned {error_count} errors", help=hint)