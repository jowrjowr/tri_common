import common.logger as _logger
import common.ldaphelpers as _ldaphelpers
import common.request_esi

def check_role(function, charid, roles):

    # check to make sure that the user has the expected corp roles

    request_url = 'characters/{0}/roles/?datasource=tranquility'.format(charid)
    code, result = common.request_esi.esi(__name__, request_url, method='get', charid=charid, version='v1')
    if not code == 200:
        error = 'unable to get character roles for {0}: ({1}) {2}'.format(charid, code, result['error'])
        _logger.log('[' + function + ']' + error,_logger.LogLevel.ERROR)
        return 'error', error

    char_roles = set(result)
    intersection = char_roles.intersection(roles)

    if len(intersection) > 0:
        return True, ''
    else:
        return False, ''
