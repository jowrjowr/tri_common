import common.database as _database
import json as _json
import common.logger as _logger
import requests as _requests

from commands import Command, CommandException, InvalidArgument
from models.esi_endpoint import ESIEndpoint, Method


class SwaggerUpdate(Command):
    __description__ = "Update ESI endpoints."
    __metavar__ = "SWAGGER URL"

    def __call__(self, arg, **kwargs):
        super(SwaggerUpdate, self).__call__(arg, **kwargs)

        if arg is None:
            url = "https://esi.tech.ccp.is/latest/swagger.json?datasource=tranquility"
        else:
            url = arg

        try:
            swagger = _requests.get(url, timeout=10).json()
        except Exception:
            error = "Swagger file at {0} is not available".format(url)
            _logger.log(error, _logger.LogLevel.ERROR)
            raise InvalidArgument(error)

        session = _database.session()

        endpoints = session.query(ESIEndpoint)

        try:
            for path in swagger['paths']:
                for method in swagger['paths'][path]:
                    # query existing endpoint or create new one
                    endpoint = endpoints.filter_by(name=swagger['paths'][path][method]['operationId']).first()

                    if endpoint is None:
                        endpoint = ESIEndpoint(name=swagger['paths'][path][method]['operationId'])
                        new = True
                    else:
                        new = False

                    endpoint.method = Method[method.upper()]
                    endpoint.url = swagger['host'] + swagger['basePath'] + path
                    endpoint.parameters = _json.dumps(swagger['paths'][path][method]['parameters'])
                    endpoint.responses = _json.dumps(swagger['paths'][path][method]['responses'])

                    if 'security' in swagger['paths'][path][method]:
                        endpoint.security = _json.dumps(swagger['paths'][path][method]['security'])
                    else:
                        endpoint.security = "[]"

                    if new:
                        session.add(endpoint)
                        _logger.debug("Adding ESI endpoint {0}."
                                      .format(swagger['paths'][path][method]['operationId']))
                    else:
                        _logger.debug("Updating ESI endpoint {0}."
                                      .format(swagger['paths'][path][method]['operationId']))

                    session.commit()
            session.close()
        except Exception as e:
            error = "Failed to update ESI endpoints due to an unhandled exception: {0}.".format(e)
            _logger.log(error, _logger.LogLevel.ERROR)
            raise CommandException(error)

        return kwargs
