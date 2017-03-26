#!/usr/bin/python3

from flask import Flask, Blueprint, Response

app = Flask(__name__)
import tri_api.views



