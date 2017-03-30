#!/usr/bin/python3

def core_jumpbridge():

    from flask import request, Response, send_file

    import qrcode
    import numpy
    import io
    import base64
    import os
    import common.logger as _logger
    import requests
    import json

    from Crypto import Random
    from Crypto.Cipher import AES
    from PIL import Image, ImageColor

    key = '6u6Wm19hSr8ksjf8'
    salt = 'iemvjfhsiemcjdmz'

    if 'id' not in request.args:
        js = json.dumps({ 'code': -1, 'error': 'need an id to generate a jb map'})
        resp = Response(js, status=401, mimetype='application/json')
        return resp

    try:
        id = int(request.args['id'])
    except ValueError:
        js = json.dumps({ 'code': -1, 'error': 'id parameter must be integer'})
        resp = Response(js, status=401, mimetype='application/json')
        return resp

    # jump bridge size parameter

    if 'size' not in request.args:
        size = 'large'
    else:
        size = request.args['size']

    charid = int(request.args['id'])

    # pad charid to 16 bytes using null characters

    charid = str(charid).ljust(16, '\0')
    charid = str.encode(charid)
    key = str.encode(key)

    crypt = AES.new(key, AES.MODE_CBC, salt)
    ciphertext = crypt.encrypt(charid)
    ciphertext = base64.b64encode(ciphertext)

    # there is a well definted limit on how much data can be put in a qr code
    # http://www.qrcode.com/en/about/version.html

    # H is the version with most error correction

    qr = qrcode.QRCode(
        version=2,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=3,
        border=0,
    )
    qr.add_data(ciphertext)
    qr_image = qr.make_image()

    if size == 'large':
        jumpbridge = Image.open('tri_api/endpoints/core/tri_jbmap.png')
    elif size == 'small':
        jumpbridge = Image.open('tri_api/endpoints/core/tri_jbmap_small.png')

    # make sure we are on the same "image mode" page

    qr_image = qr_image.convert(mode='RGB')
    jumpbridge = jumpbridge.convert(mode='RGB')

    # http://stackoverflow.com/questions/6483489/change-the-color-of-all-pixels-with-another-color
    # this method is ... aggressive on memory/cpu but the qr image itself is small!

    numpy.set_printoptions(threshold=numpy.nan)
    data = numpy.array(qr_image)
    r1, g1, b1 = 0, 0, 0 # original black in RGB
    r2, g2, b2 = 255, 255, 235

    red, green, blue = data[:,:,0], data[:,:,1], data[:,:,2]
    mask = (red == r1) & (green == r1) & (blue == b1)
    data[:,:,:3][mask] = [r2, g2, b2]

    # load the image back as a PIL object
    qr_image = Image.fromarray(data)

    # pillow coordinate system starts at the top left corner of an image

    qr_x, qr_y = qr_image.size
    jb_x, jb_y = jumpbridge.size

    topleft = (0, 0, qr_x, qr_y)
    topright = (jb_x - qr_x, 0, jb_x, qr_y)
    lowerleft = (0, jb_y - qr_y, qr_x, jb_y)
    lowerright = (jb_x - qr_x, jb_y - qr_y, jb_x, jb_y)

    # add the qr codes to the specific spots
    if size == 'large':
        offset1 = (850, 690, qr_x + 850, qr_y + 690)
        offset2 = (2000, 1775, qr_x + 2000, qr_y + 1775)
        offset3 = (1400, 2050, qr_x + 1400, qr_y + 2050)
        offset4 = (2100, 177, qr_x + 2100, qr_y + 177)
        offset5 = (3000, 1000, qr_x + 3000, qr_y + 1000)
        offset6 = (3700, 450, qr_x + 3700, qr_y + 450)
        offsets = [ topright, lowerleft, lowerright, offset1, offset2, offset3, offset4, offset5, offset6 ]
    elif size == 'small':
        offset1 = (1140, 361, qr_x + 1140, qr_y + 361)
        offset2 = (840, 775, qr_x + 840, qr_y + 775)
        offset3 = (312, 245, qr_x + 312, qr_y + 245)
        offsets = [ topright, lowerleft, lowerright, offset1, offset2, offset3 ]

    for offset in offsets:
        jumpbridge.paste(qr_image, box=offset)

    # write the image to a string object
    output = io.BytesIO()
    jumpbridge.save(output, format='PNG')
    output.seek(0)
    return send_file(output, mimetype='image/png')

