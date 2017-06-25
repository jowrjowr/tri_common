from flask import request
from tri_api import app

@app.route('/core/group/<group>/broadcast', methods=[ 'POST' ])
def core_group_broadcast(group):

    from flask import request, json, Response
    import common.logger as _logger
    from tri_core.common.broadcast import broadcast
    ipaddress = request.headers['X-Real-Ip']
    message = request.get_data()
    message = message.decode('utf-8')

    # spew at a group
    if request.method == 'POST':
        _logger.securitylog(__name__, 'broadcast to group {0}'.format(group), ipaddress=ipaddress)
        broadcast(message, group)
        return Response({}, status=200, mimetype='application/json')

