from __future__ import absolute_import

import unittest
import flask
from flask import Request
from werkzeug.test import EnvironBuilder

from flask.ext.odis import odis, ModelForm
from flask.ext.wtf import Form, fields, validators

class Foo(odis.Model):
    username = odis.CharField()

class FooForm(ModelForm):
    class Meta:
        model = Foo

class BarForm(Form):
    username = fields.StringField('Username', [validators.Required()])

class Baz(odis.Model):
    users = odis.SetField()

class BazForm(ModelForm):
    class Meta:
        model = Baz

def create_request(data, method='POST'):
    builder = EnvironBuilder(method=method, data=data)
    env = builder.get_environ()
    return Request(env)

class ModelFormTestCase(unittest.TestCase):
    def setUp(self):
        self.app = flask.Flask(__name__)
        self.app.secret_key = "secret"
        self.ctx = self.app.test_request_context()
        self.ctx.push()

    def tearDown(self):
        self.ctx.pop()

    def test_simple(self):
        req = create_request(data={'username': 'foo'})

        f = FooForm(req.form, csrf_enabled=False)
        self.assertEqual(f.validate(), True)
        self.assertEqual(hasattr(f, 'username'), True)
        self.assertEqual(hasattr(f, 'pk'), False)

        obj = f.save()
        self.assertEqual(obj.username, u'foo')
        pk = obj.pk

        req = create_request(data={'username': 'bar'})
        f = FooForm(req.form, obj=obj, csrf_enabled=False)
        self.assertEqual(f.validate(), True)
        obj = f.save()
        self.assertEqual(obj.username, u'bar')
        self.assertEqual(obj.pk, pk)

    def test_invalid(self):
        tests = [
            ({}, 'empty'),
            ({'username': ''}, 'empty')
        ]

        for data, name in tests:
            req = create_request(data=data)
            f = FooForm(req.form, csrf_enabled=False)
            bb = BarForm(req.form, csrf_enabled=False)
            self.assertEqual(f.validate(), False)
            self.assertEqual(bb.validate(), False)

    def test_fieldlist(self):
        req = create_request(data={'users-0':['a'], 'users-1': ['b']})
        f = BazForm(req.form, csrf_enabled=False)
        self.assertEqual(hasattr(f, 'users'), True)
        self.assertEqual(f.validate(), True)
        self.assertEqual(len(f.users.entries), 2)
        # q.sets.sadd(*[u.pk for u in self.users[:2]])
