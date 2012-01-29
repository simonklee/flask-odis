from __future__ import absolute_import

import unittest
import flask
from flask import Request
from werkzeug.test import EnvironBuilder

from flask.ext.odis import odis, ModelForm
from flask.ext.wtf import Form, fields, validators
from odis.utils import s

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

class Qux(odis.Model):
    users = odis.RelField(Foo)

class QuxForm(ModelForm):
    class Meta:
        model = Qux

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
        odis.r.flushdb()

    def tearDown(self):
        self.ctx.pop()
        odis.r.flushdb()

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

    def test_setfield(self):
        req = create_request(data={'users':['a', 'b']})
        f = BazForm(req.form, csrf_enabled=False)

        # users is required, but no obj was provided so no choices are valid
        self.assertEqual(hasattr(f, 'users'), True)
        self.assertEqual(f.validate(), False)

        req = create_request(data={})
        f = BazForm(req.form, csrf_enabled=False)

        # by default set field is optional
        self.assertEqual(f.validate(), True)

        obj = Baz()
        obj.save()
        obj.users.add('a', 'b')
        req = create_request(data={'users':['a', 'b']})

        # users is required, and obj with users was provided
        f = BazForm(req.form, obj=obj, csrf_enabled=False)
        self.assertEqual(f.validate(), True)
        obj_new = f.save()
        self.assertEqual(list(obj.users) == list(obj_new.users), True)

        # we can remove users, but not add
        req = create_request(data={'users':['b']})
        f = BazForm(req.form, obj=obj, csrf_enabled=False)
        self.assertEqual(f.validate(), True)
        old_users = list(obj.users)
        obj_new = f.save()
        self.assertEqual(old_users == list(obj_new.users), False)

    def test_relfield(self):
        print '\n\n  quxform #1:\n'
        req = create_request(data={'users':[1, 2]})
        f = QuxForm(req.form, csrf_enabled=False)

        # We have not created any Foo objects so no choices are valid
        self.assertEqual(hasattr(f, 'users'), True)
        self.assertEqual(f.validate(), False)

        usernames = ['foo', 'bar', 'baz', 'qux']
        [Foo(username=n).save() for n in usernames]

        print '\n  quxform #2:\n'
        req = create_request(data={'users':[1, 2, 3, 4]})
        f = QuxForm(req.form, csrf_enabled=False)

        # Any Foo pk is a valid choice
        self.assertEqual(f.validate(), True)
