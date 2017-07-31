from flask import request
from tri_api import app

@app.route('/core/blacklist/confirmed', methods=[ 'GET' ])
def core_blacklist():

    from flask import request, json, Response
    import common.logger as _logger
    import common.ldaphelpers as _ldaphelpers
    from tri_core.common.broadcast import broadcast

    import re
    import time
    import common.request_esi

    # get all users that are confirmed blacklisted

    ipaddress = request.headers['X-Real-Ip']
    log_charid = request.args.get('log_charid')    # logging purposes
    _logger.securitylog(__name__, 'viewed blacklist [confirmed]', ipaddress=ipaddress, charid=log_charid)

    dn = 'ou=People,dc=triumvirate,dc=rocks'
    filterstr='accountStatus=banned'
    attrlist=['characterName', 'uid', 'altOf', 'banApprovedBy', 'banApprovedOn', 'banReason', 'banReportedBy', 'banDescription' ]
    code, result = _ldaphelpers.ldap_search(__name__, dn, filterstr, attrlist)

    if code == False:
        msg = 'unable to fetch ldap information: {}'.format(error)
        _logger.log('[' + __name__ + '] {}'.format(msg),_logger.LogLevel.ERROR)
        js = json.dumps({ 'error': msg })
        return Response(js, status=500, mimetype='application/json')

    # start converting the bans into friendly information

    banlist = dict()

    for dn, info in result.items():
        charname = info['characterName']
        banlist[charname] = info
        # map the times to friendlier info

        fuckyou = int(float(info['banApprovedOn']))
        banlist[charname]['banApprovedOn'] = time.strftime('%Y-%m-%d', time.localtime(fuckyou))

        # how the fuck did ban reasons/descriptions get stored this way?!

        convert = [ 'banDescription', 'banReason' ]
        for thing in convert:

            if banlist[charname][thing] == '': continue
            if banlist[charname][thing] == None: continue
            banlist[charname][thing] = re.sub('"$', '', banlist[charname][thing])
            banlist[charname][thing] = re.sub("'$", '', banlist[charname][thing])
            banlist[charname][thing] = re.sub("^b'", '', banlist[charname][thing])
            banlist[charname][thing] = re.sub('^b"', '', banlist[charname][thing])
            banlist[charname][thing] = re.sub('\\\\r', '<br>', banlist[charname][thing])
            banlist[charname][thing] = re.sub('\\\\n', '<br>', banlist[charname][thing])

        # map the main of the banned alt to a name

        if not info['altOf'] == None:
            banlist[charname]['isalt'] = True
            request_url = 'characters/{0}/?datasource=tranquility'.format(info['altOf'])
            code, result = common.request_esi.esi(__name__, request_url, 'get')

            if not code == 200:
                _logger.log('[' + function + '] /characters API error {0}: {1}'.format(code, result['error']), _logger.LogLevel.WARNING)
                banlist[charname]['altOf'] = 'Unknown'
            try:
                banlist[charname]['altOf'] = result['name']
            except KeyError as error:
                _logger.log('[' + function + '] User does not exist: {0})'.format(charid), _logger.LogLevel.ERROR)
                banlist[charname]['altOf'] = 'Unknown'
        else:
            banlist[charname]['isalt'] = False

        # map the reporter and approver's ids to names

        request_url = 'characters/{0}/?datasource=tranquility'.format(info['banApprovedBy'])
        code, result = common.request_esi.esi(__name__, request_url, 'get')

        if not code == 200:
            _logger.log('[' + function + '] /characters API error {0}: {1}'.format(code, result['error']), _logger.LogLevel.WARNING)
            banlist[charname]['banApprovedBy'] = 'Unknown'
        try:
            banlist[charname]['banApprovedBy'] = result['name']
        except KeyError as error:
            _logger.log('[' + function + '] User does not exist: {0})'.format(charid), _logger.LogLevel.ERROR)
            banlist[charname]['banApprovedBy'] = 'Unknown'

        request_url = 'characters/{0}/?datasource=tranquility'.format(info['banReportedBy'])
        code, result = common.request_esi.esi(__name__, request_url, 'get')

        if not code == 200:
            _logger.log('[' + function + '] /characters API error {0}: {1}'.format(code, result['error']), _logger.LogLevel.WARNING)
            banlist[charname]['banReportedBy'] = 'Unknown'
        try:
            banlist[charname]['banReportedBy'] = result['name']
        except KeyError as error:
            _logger.log('[' + function + '] User does not exist: {0})'.format(charid), _logger.LogLevel.ERROR)
            banlist[charname]['banReportedBy'] = 'Unknown'


    return Response(json.dumps(banlist), status=200, mimetype='application/json')

@app.route('/core/blacklist/<charid>', methods=[ 'GET' ])
def core_blacklist_details():

    from flask import request, json, Response
    import common.logger as _logger
    from tri_core.common.broadcast import broadcast
    ipaddress = request.headers['X-Real-Ip']

@app.route('/core/blacklist/<charid>/confirm', methods=[ 'POST' ])
def core_blacklist_confirm():

    from flask import request, json, Response
    import common.logger as _logger
    from tri_core.common.broadcast import broadcast
    ipaddress = request.headers['X-Real-Ip']

    _logger.securitylog(__name__, 'blacklist confirm of {0}'.format(charid), ipaddress=ipaddress)


    return Response({}, status=200, mimetype='application/json')

@app.route('/core/blacklist/<charid>/remove', methods=[ 'POST' ])
def core_blacklist_remove():

    from flask import request, json, Response
    import common.logger as _logger
    from tri_core.common.broadcast import broadcast
    ipaddress = request.headers['X-Real-Ip']

    _logger.securitylog(__name__, 'blacklist removal of {0}'.format(charid), ipaddress=ipaddress)

    return Response({}, status=200, mimetype='application/json')

# ban reasons
# 1: "shitlord"
# 2: "spy"
# 3: "rejected applicant"
# 4: "other"
