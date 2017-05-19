from cmd import Command as _Command

class _ESIError(Exception):
    pass

class Capitals(_Command):
    arg = "LOCATIONID"
    help = "audit tri capitals"
    group = "tri_audit"

    @staticmethod
    def execute(**kwargs):
        import ldap
        import ldap.modlist
        import common.logger as _logger
        import common.credentials.ldap as _ldap

        _logger.log('[' + __name__ + '] auditing tri capitals', _logger.LogLevel.INFO)

        ldap_conn = ldap.initialize(_ldap.ldap_host, bytes_mode=False)

        try:
            ldap_conn.simple_bind_s(_ldap.admin_dn,
                                    _ldap.admin_dn_password)
        except ldap.LDAPError as error:
            _logger.log('[' + __name__ + '] LDAP connection error: {}'.format(error),
                        _logger.LogLevel.ERROR)

        # fetch all tri users
        try:
            users = ldap_conn.search_s('ou=People,dc=triumvirate,dc=rocks', ldap.SCOPE_SUBTREE,
                                       filterstr='(&(objectclass=pilot)(authGroup=trisupers))',
                                       attrlist=['characterName', 'uid', 'corporation', 'alliance', 'esiAccessToken',
                                                 'authGroup'])
            _logger.log('[' + __name__ + '] auditing {} tri pilots'.format(users.__len__()), _logger.LogLevel.INFO)
        except ldap.LDAPError as error:
            _logger.log('[' + __name__ + '] unable to fetch ldap users: {}'.format(error), _logger.LogLevel.ERROR)
            return

        bad_users = {}

        for user in users:
            dn, x = user

            character_id = int(x['uid'][0].decode('utf-8'))
            corporation_id = int(x['corporation'][0].decode('utf-8'))
            alliance_id = int(x['alliance'][0].decode('utf-8'))

            _logger.log('[' + __name__ + '] auditing {0}/{1}'.format(character_id, corporation_id),
                        _logger.LogLevel.INFO)

            # TODO: Implement alt tokens

            try:
                result = capital_check(character_id, kwargs['argument'])

                c_count = result['Chimera'] + result['Nidhoggur']
                d_count = result['Naglfar'] + result['Phoenix']
                f_count = result['Minokawa']

                _logger.log('[' + __name__ + '] pilot {0}/{1} owns {2} carriers, {3} dreads and {4} fax'
                            .format(character_id, corporation_id, c_count, d_count, f_count), _logger.LogLevel.INFO)

                if c_count == 0 or d_count == 0 or f_count == 0:
                    _logger.log('[' + __name__ + '] adding pilot {0}/{1} to bads list'
                                .format(character_id, corporation_id), _logger.LogLevel.WARNING)
                    bad_users[character_id] = result

                _logger.log('[' + __name__ + '] audit success for {0}/{1}'.format(character_id, corporation_id),
                            _logger.LogLevel.INFO)

            except _ESIError:
                _logger.log('[' + __name__ + '] failed to audit {0}/{1}'.format(character_id, corporation_id),
                            _logger.LogLevel.WARNING)

        return kwargs


def capital_check(char_id, location_id):
    from common.api import base_url
    import common.request_esi
    import common.logger as _logger

    request_url = base_url + 'characters/{0}/assets/?datasource=tranquility'.format(char_id)
    code, result = common.request_esi.esi(__name__, request_url, 'get', charid=char_id)

    count = {
        'Chimera': 0,
        'Nidhoggur': 0,
        'Naglfar': 0,
        'Phoenix': 0,
        'Minokawa': 0
    }

    if not code == 200:
        # something broke severely
        _logger.log('[' + __name__ + '] character assets API error for char {0} ({1}: {2})'
                    .format(char_id, code, result['error']),
                    _logger.LogLevel.ERROR)
        raise _ESIError

    for item in result:
        if item['location_id'] == location_id:
            if item['type_id'] == 23915:
                count['Chimera'] += 1
            elif item['type_id'] == 24483:
                count['Nidhoggur'] += 1
            elif item['type_id'] == 19722:
                count['Naglfar'] += 1
            elif item['type_id'] == 19726:
                count['Phoenix'] += 1
            elif item['type_id'] == 37605:
                count['Minokawa'] += 1

    return count
