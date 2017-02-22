import enum as _enum
import json as _json
import models as _models
import sqlalchemy as _sql
import urllib.parse as _urlparse

from models import Base, Model


class Method(_enum.Enum):
    GET = 1
    POST = 2
    HEAD = 3
    OPTIONS = 4
    DELETE = 5
    PUT = 6
    TRACE = 7
    CONNECT = 8


class ESIEndpoint(Model, Base):
    method = _sql.Column(_sql.Enum(Method))
    url = _sql.Column(_sql.String(128))
    parameters = _sql.Column(_sql.Text)
    responses = _sql.Column(_sql.Text)
    security = _sql.Column(_sql.Text)

    def parse_url(self, values):
        url = ""
        query = {}

        for parameter in _json.loads(self.parameters):
            # set parameter to default if not supplied
            if parameter['name'] not in values and 'default' in parameter:
                values[parameter['name']] = parameter['default']
            elif parameter.get('required', False) and parameter['name'] not in values:
                # raise exception if required parameter not supplied
                raise _models.InvalidArguments("Failed to parse ESIEndpoint URL as the parameter {0} was no supplied"
                                               .format(parameter['name']))

            # if parameter is an enum check if valid
            if 'enum' in parameter:
                if values[parameter['name']] not in parameter['enum']:
                    raise _models.InvalidArguments("Failed to parse ESIEndpoint URL as the parameter {0} was invalid"
                                                   .format(parameter['name']))

            if parameter['in'] == 'path':
                url = self.url.replace("{" + parameter['name'] + "}", str(values[parameter['name']]))
            elif parameter['in'] == 'query':
                query[parameter['name']] = values[parameter['name']]
            else:
                raise Exception("Parameter {0} has unkown \"in\" value {1}"
                                .format(parameter['name'], parameter['in']))

            # build url and return
            return 'https://' + url + "?" + _urlparse.urlencode(query)
