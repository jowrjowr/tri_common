def sendmetric(function, prefix, group, metric, value):
    import graphitesend
    import logging
    import common.logger as _logger

    # metrics!
    # use a wrapper script to ease up the amount of bloat this adds to normal code

    # get log level to decide whether to enable graphite debugger output
    debug = logging.getLogger().isEnabledFor(logging.CRITICAL)

    # setup the graphite logger
    try:
        graphite = graphitesend.init(
            debug=debug,
            connect_on_create=True,
            graphite_server='localhost',
            prefix=prefix,
            group=group,
        )
    except Exception as err:
        _logger.log('[' + function + '] graphite error: ' + str(err), _logger.LogLevel.DEBUG)

    try:
        g_result = graphite.send(metric, value)
        _logger.log('[' + function + '] graphite output: ' + str(g_result), _logger.LogLevel.DEBUG)
    except Exception as err:
        # don't really care.
        _logger.log('[' + function + '] graphite error: ' + str(err), _logger.LogLevel.DEBUG)

