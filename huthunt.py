
def huthunt(alliance_id):
    from common.check_role import check_role
    from concurrent.futures import ThreadPoolExecutor, as_completed
    import common.ldaphelpers as _ldaphelpers
    import common.logger as _logger
    import common.request_esi
    import json

    dn = 'ou=People,dc=triumvirate,dc=rocks'
    filterstr='(&(esiAccessToken=*)(alliance={}))'.format(alliance_id)
    attrlist=['uid', 'characterName', 'corporation' ]
    code, result = _ldaphelpers.ldap_search(__name__, dn, filterstr, attrlist)

    if code == False:
        msg = 'unable to fetch ldap information: {}'.format(error)
        _logger.log('[' + __name__ + '] {}'.format(msg),_logger.LogLevel.ERROR)
        return None

    if result == None:
        msg = 'cn {0} not in ldap'.format(cn)
        _logger.log('[' + __name__ + '] {}'.format(msg),_logger.LogLevel.WARNING)
        return None


    for dn, info in result.items():

        charid = info['uid']
        corp_id = info['corporation']
        allowed_roles = ['Director', 'Station_Manager']
        code, result = check_role(__name__, charid, allowed_roles)
        if code == True:
            print('ldap dn: {0}, corp id: {1}'.format(dn, corp_id)) 
            request_url = 'core/structures?id={0}'.format(charid)
            code, result = common.request_esi.esi(__name__, request_url, 'get', base='triapi')
            if not code == 200:
                # something broke severely
                _logger.log('[' + __name__ + '] /isblue API error {0}: {1}'.format(code, result['error']), _logger.LogLevel.ERROR)

            for structure_id in result.keys():
                info = result[structure_id]
                s_name = info['name']
                s_type = info['type_name']
                s_vuln = info['vuln_dates']
                print('structure name: {0} ({1})'.format(s_name, s_type))
                print('vulnerability dates:')
                print(s_vuln)

huthunt(99006109)


