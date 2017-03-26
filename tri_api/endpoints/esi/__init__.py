import flask as _flask

blueprint = _flask.Blueprint(__name__.split(".")[-1], __name__,  url_prefix="/" + __name__.split(".")[-1])

# import files
from .get import get