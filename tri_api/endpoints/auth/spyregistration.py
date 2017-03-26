#!/usr/bin/python3

def auth_spyregister():

    from flask import Flask, request, url_for, json, Response
    from flask import Flask, g, session, redirect, request, url_for, jsonify
    from requests_oauthlib import OAuth2Session
    import common.request_esi
    import common.logger as _logger
    import MySQLdb as mysql
    import common.database as DATABASE
    import requests
    import json

    OAUTH2_CLIENT_ID = '295122632507129856'
    OAUTH2_CLIENT_SECRET = 'WzwA1KaM6oEBmf9pl1UMJ_Czqt4BGqYx'
    OAUTH2_REDIRECT_URI = 'http://auth.triumvirate.rocks:5001/callback'



def auth_spyregister_callback():
    pass
