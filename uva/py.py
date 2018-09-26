import check50
import importlib

def import_(module):
    try:
        return importlib.import_module(module)
    except BaseException as e:
        raise check50.Failure(f"An exception was raised while importing {module}")
