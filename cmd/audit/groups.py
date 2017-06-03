from cmd import Command as _Command

class CorporationTokens(_Command):
    arg = "CORP_ID"
    help = "audit corporation"
    group = "vg_audit"

    @staticmethod
    def execute(**kwargs):
        import ldap
        import ldap.modlist
        import common.logger as _logger
        import common.credentials.ldap as _ldap

        # get corporation
        def get_corporation(corp_id):
            from common.api import base_url
            import common.request_esi

            request_url = base_url + 'corporations/{0}/?datasource=tranquility'.format(corp_id)
            code, result = common.request_esi.esi(__name__, request_url, 'get')

            if code == 403:
                # invalid corp id
                _logger.log('[' + __name__ + '] attempting to audit invalid corp id {0}'.format(kwargs['argument']),
                            _logger.LogLevel.WARNING)
                print("ERROR: Invalid CORP_ID")
                return
            elif not code == 200:
                # something broke severely
                _logger.log('[' + __name__ + '] corporation API error for corp {0} ({1}: {2})'
                            .format(corp_id, code, result['error']),
                            _logger.LogLevel.ERROR)
                return

            return result

        corp = get_corporation(kwargs['argument'])

        _logger.log('[' + __name__ + '] auditing corporation {0}/{1}'
                    .format(kwargs['argument'], corp['corporation_name']), _logger.LogLevel.INFO)

        ldap_conn = ldap.initialize(_ldap.ldap_host, bytes_mode=False)

        try:
            ldap_conn.simple_bind_s(_ldap.admin_dn, _ldap.admin_dn_password)
        except ldap.LDAPError as error:
            _logger.log('[' + __name__ + '] LDAP connection error: {}'.format(error), _logger.LogLevel.ERROR)



        # get corporation members from ldap
        try:
            users = ldap_conn.search_s('ou=People,dc=triumvirate,dc=rocks', ldap.SCOPE_SUBTREE,
                                       filterstr='(&(objectclass=pilot)(corporation={0}))'.format(kwargs['argument']),
                                       attrlist=['characterName', 'uid', 'corporation', 'esiAccessToken',
                                                 'authGroup', 'altOf'])
            _logger.log('[' + __name__ + '] auditing {0} pilots from {1}'
                        .format(users.__len__(), kwargs['argument']), _logger.LogLevel.INFO)


        except ldap.LDAPError as error:
            _logger.log('[' + __name__ + '] unable to fetch ldap users: {}'.format(error), _logger.LogLevel.ERROR)
            return

        if kwargs.get('verbose', True):
            print("Auditing {0} [{1}] ({2}/{3})"
                  .format(corp['corporation_name'], corp['ticker'], users.__len__(), corp['member_count']))

        # grab first char id of list and grab corp member list and output missing tokens
        def get_member_list(users, corp_id):
            from common.api import base_url
            import common.request_esi

            if users.__len__() > 0:
                user = users[0]
                _, x = user
                char_id = int(x['uid'][0].decode('utf-8'))
            else:
                _logger.log('[' + __name__ + '] corporation {0} has no ldap entries'
                            .format(kwargs['argument']), _logger.LogLevel.ERROR)

                print("No members found.")

                raise Exception

            request_url = base_url + 'corporations/{0}/members/?datasource=tranquility'.format(corp_id)
            code, result = common.request_esi.esi(__name__, request_url, 'get', charid=char_id)

            if not code == 200:
                # something broke severely
                _logger.log('[' + __name__ + '] corporation/members API error for corp {0} ({1}: {2})'
                            .format(corp_id, code, result['error']),
                            _logger.LogLevel.ERROR)

                raise Exception

            return result

        # get member list
        try:
            member_list = get_member_list(users, kwargs['argument'])
        except:
            return

        member_id_list = [str(member['character_id']) for member in member_list]
        user_id_list = [str(user[1]['uid'][0].decode('utf-8')) for user in users]

        missing_members = sorted(list(set(member_id_list) - set(user_id_list)))

        # get character names from missing IDs
        def get_member_names(ids):
            from common.api import base_url
            import common.request_esi

            request_url = base_url + 'characters/names/?character_ids={0}&datasource=tranquility'.format('%2C'.join(ids))
            code, result = common.request_esi.esi(__name__, request_url, 'get')

            if not code == 200:
                # something broke severely
                _logger.log('[' + __name__ + '] character/names API error for ids {0} ({1}: {2})'
                            .format(', '.join(ids), code, result['error']),
                            _logger.LogLevel.ERROR)
                _logger.log('[' + __name__ + '] request_url: {0}'
                            .format(request_url),
                            _logger.LogLevel.ERROR)

                raise Exception

            return result

        try:
            missing_members_names = sorted(get_member_names(missing_members))
        except:
            return

        if kwargs.get('verbose', True):
            print("Missing Tokens: {0}".format(', '.join([char['character_name'] for char in missing_members_names])))

        kwargs['missing-{0}'.format(kwargs['argument'])] = missing_members_names

        return kwargs
