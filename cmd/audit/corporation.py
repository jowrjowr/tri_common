from cmd import Command as _Command

class Corporation(_Command):
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

