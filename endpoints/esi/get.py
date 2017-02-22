import cachecontrol as _cachecontrol
import cachecontrol.caches as _caches
import common.database as _database
import common.logger as _logger
import flask as _flask
import json as _json
import models as _models
import requests as _requests

from . import blueprint
from models.esi_endpoint import ESIEndpoint
from templates.json_responses import *


@blueprint.route("/get/<operation_id_short>", methods=['GET'])
def get(operation_id_short):
    try:
        # check if endpoint exists
        session = _database.session()

        endpoint = session.query(ESIEndpoint).filter_by(name="get_{0}".format(operation_id_short)).first()

        if endpoint is None:
            _logger.log("ESIEndpoint \"{0}\" not found (from {1})."
                        .format("get_{0}".format(operation_id_short), _flask.request.remote_addr),
                        _logger.LogLevel.ERROR)
            return response_404()

        if len(_json.loads(endpoint.security)) > 0:
            _logger.log("Access to ESIEndpoint \"{0}\" denied (from {1})."
                        .format("get_{0}".format(operation_id_short), _flask.request.remote_addr),
                        _logger.LogLevel.WARNING)
            return response_501()

        try:
            url = endpoint.parse_url(_flask.request.args.to_dict())
        except _models.InvalidArguments as e:
            _logger.log("Access to ESIEndpoint \"{0}\" failed due to url parsing (from {1})."
                        .format("get_{0}".format(operation_id_short), _flask.request.remote_addr),
                        _logger.LogLevel.ERROR)
            return response_400(error=e)
        except Exception as e:
            _logger.log("Access to ESIEndpoint \"{0}\" failed (from {1}): {2}."
                        .format("get_{0}".format(operation_id_short), _flask.request.remote_addr, e),
                        _logger.LogLevel.CRITICAL)
            return response_500()

        cache = _cachecontrol.CacheControl(_requests.Session(), cache=_caches.FileCache('.api_cache'))

        try:
            request = cache.get(url, timeout=1)
        except _requests.ReadTimeout:
            _logger.log("Requesting ESIEndpoint \"{0}\" timed out on reading (from {1})."
                        .format("get_{0}".format(operation_id_short), _flask.request.remote_addr),
                        _logger.LogLevel.WARNING)
            return response_200(status=598)
        except _requests.ConnectTimeout:
            _logger.log("Requesting ESIEndpoint \"{0}\" timed out on connecting (from {1})."
                        .format("get_{0}".format(operation_id_short), _flask.request.remote_addr),
                        _logger.LogLevel.WARNING)
            return response_200(status=599)

        except Exception as e:
            _logger.log("Requesting ESIEndpoint \"{0}\" failed (from {1}): {2}."
                        .format("get_{0}".format(operation_id_short), _flask.request.remote_addr, e),
                        _logger.LogLevel.CRITICAL)
            return response_500()

        return response_200(status=request.status_code, payload=request.text)
    except Exception as e:
        _logger.log("Access to ESIEndpoint \"{0}\" failed (from {1}): {2}."
                    .format("get_{0}".format(operation_id_short), _flask.request.remote_addr, e),
                    _logger.LogLevel.CRITICAL)
        return response_500()
