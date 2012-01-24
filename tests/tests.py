from __future__ import absolute_import

import unittest
import flask

from flask.ext.odis import odis, ModelForm

class Foo(odis.Model):
    username = odis.CharField()

class FooForm(ModelForm):
    class Meta:
        model = Foo

class ModelFormTestCase(unittest.TestCase):
    def setUp(self):
        self.app = flask.Flask(__name__)
        self.app.secret_key = "secret"
        self.ctx = self.app.test_request_context()
        self.ctx.push()

    def tearDown(self):
        self.ctx.pop()

    def test_simple(self):
        f = FooForm(csrf_enabled=False)
        self.assertEqual(f.validate(), True)
        self.assertEqual(f.is_submitted(), False)
        self.assertEqual(hasattr(f, 'username'), True)
        self.assertEqual(hasattr(f, 'pk'), True)
