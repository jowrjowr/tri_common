
def test_tor(hostip, targetip):
    import netifaces
    import dns.resolver
    from IPy import IP

    # test if the ip in question is coming from a tor exit node
    # see: http://www.torproject.org/projects/tordnsel.html.en
    clientip_reverse = reverse_ip(targetip)
    hostip_reverse = reverse_ip(hostip)
    query = clientip_reverse + '.' + '80' + '.' + hostip_reverse + '.ip-port.exitlist.torproject.org'
    try:
        answers = dns.resolver.query(query, 'A')
        # there should NEVER be a response for non-tor clients.
        return True
    except dns.resolver.NXDOMAIN:
        # user passed
        return False

def reverse_ip(ip):
    if len(ip) <= 1:
       return ip
    l = ip.split('.')
    return '.'.join(l[::-1])
