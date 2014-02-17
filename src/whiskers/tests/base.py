import os
import unittest

import transaction

from paste.deploy.loadwsgi import appconfig
from webtest import TestApp
from pyramid import testing

from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import sessionmaker
from zope.sqlalchemy import ZopeTransactionExtension


from whiskers import main, models

here = os.path.dirname(__file__)
settings = appconfig('config:' + os.path.join(here, 'test.ini'))

test_session = scoped_session(sessionmaker(extension=ZopeTransactionExtension(keep_session=True)))


def init_testing_db():
    from sqlalchemy import create_engine
    engine = create_engine('sqlite:///:memory:')
    models.DBSession = test_session
    models.initialize_sql(engine)
    return models.DBSession


class UnitTestBase(unittest.TestCase):

    def setUp(self):
        self.session = init_testing_db()
        self.config = testing.setUp()

    def tearDown(self):
        transaction.abort()
        self.session.remove()
        testing.tearDown()


class IntegrationTestBase(unittest.TestCase):

    def setUp(self):
        self.session = init_testing_db()
        self.app = TestApp(main({}, **settings))
        self.config = testing.setUp()

    def tearDown(self):
        transaction.abort()
        self.session.remove()
        testing.tearDown()
