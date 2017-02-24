# a little stupid deckshuffling to make uwsgi happy
from api import app as application

if __name__ == "__main__":
    application.run()
