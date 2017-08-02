
def maint_jabber_logs():
    import common.logger as _logger
    import common.ldaphelpers as _ldaphelpers

    import re
    import time

    # process ejabberd log files and store relevant information in the security log
    # this setup assumes the log file will be copied to a spot that does
    # not mind being truncated on a regular basis

    # the regexs will need a minor rewrite for ipv6
    accepted = r"^(\S+ \S+) .* Accepted authentication for (\S+) by ejabberd_auth_ldap from ::FFFF:(.*)$"
    failed = r"^(\S+ \S+) .* Failed authentication for (\S+) from ::FFFF:(.*)$"

    logfile = '/var/log/ejabberd/logparser/ejabberd.log'
    try:
        file = open(logfile, 'r+')
    except Exception as err:
        # the file to process is obviously not there.
        _logger.log('[' + __name__ + '] unable to open ejabberd logfile: {}'.format(err), _logger.LogLevel.ERROR)
        return

    _logger.log('[' + __name__ + '] processing ejabberd logfile', _logger.LogLevel.INFO)

    for line in file.readlines():
        match_accept = re.match(accepted, line)
        match_failed = re.match(failed, line)
        action = 'jabber login'

        if match_accept:
            date = match_accept.group(1)
            cn = match_accept.group(2)
            ip_address = match_accept.group(3)
            detail = 'successful'
        elif match_failed:
            date = match_failed.group(1)
            ip_address = match_failed.group(3)
            detail = 'failed'

            # convert the attempted login user to maybe a valid dn
            login_user = match_failed.group(2)
            user_match = re.match('^(\S+)@triumvirate.rocks', login_user)
            if user_match:
                cn = user_match.group(1)
            else:
                # can't match it to a dn so it'll be a mystery
                cn = None
        else:
            continue

        # convert a date format like the following to epoch
        # 2017-07-31 06:03:41.918
        try:
            date = time.strptime(date, "%Y-%m-%d %H:%M:%S.%f")
        except ValueError as e:
            _logger.log('[' + __name__ + '] ejabberd log data pollution: {0}'.format(e),_logger.LogLevel.ERROR)
            continue

        date = time.mktime(date)

        # (try to) fetch the charid from ldap

        result = _ldaphelpers.ldap_cn2id(__name__, cn)

        try:
            uid = result['uid']
        except Exception as e:
            uid = None

        # store into the security log

        _logger.securitylog(__name__, action, charid=uid, ipaddress=ip_address, date=date, detail=detail)

    # wipe the file and close out
    file.seek(0)
    file.truncate()
    file.close()
    _logger.log('[' + __name__ + '] finished processing ejabberd log',_logger.LogLevel.INFO)

