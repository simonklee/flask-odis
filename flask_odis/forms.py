from __future__ import absolute_import

import odis

from flask.ext.wtf import forms, fields, validators
from wtforms.form import FormMeta
from odis.utils import s

translate = {
    'field': fields.StringField,
    'charfield': fields.StringField,
    'integerfield': fields.IntegerField,
    'foreignfield': fields.IntegerField,
    'datetimefield': fields.DateTimeField,
    'datefield': fields.DateField,
    'relfield': fields.IntegerField
}

def formfield_from_modelfield(field):
    data = {
        'validators': []
    }

    if getattr(field, 'default' or False):
        data['validators'].append(validators.optional())
    else:
        data['validators'].append(validators.required())

    if getattr(field, 'choices' or False):
        data['choices'] = field.choices

    default = getattr(field, 'default' or None)
    if default != odis.EMPTY:
        data['default'] = default

    data['label'] = field.verbose_name or field.name

    if 'choices' in data:
        form_field = fields.SelectField
        data['coerce'] = field.to_python
    else:
        form_field = translate[field.__class__.__name__.lower()]

    return form_field(**data)

class ModelFormOptions(object):
    def __init__(self, options=None):
        self.model = getattr(options, 'model', None)
        self.fields = getattr(options, 'fields', None)
        self.exclude = getattr(options, 'exclude', None)

def fields_for_model(model, fields=None, exclude=None):
    field_dict = {}

    for name, f in model._fields.items():
        if fields and not name in fields:
            continue

        if exclude and name in exclude:
            continue

        if name in ('pk',):
            continue

        field_dict[name] = formfield_from_modelfield(f)

    return field_dict

class ModelFormMeta(FormMeta):
    def __new__(cls, name, bases, attrs):
        new_cls = FormMeta.__new__(cls, name, bases, attrs)
        opts = new_cls._meta = ModelFormOptions(getattr(new_cls, 'Meta', None))

        if opts.model:
            fields = fields_for_model(opts.model, opts.fields, opts.exclude)

            for name, f in fields.items():
                setattr(new_cls, name, f)

        return new_cls

class ModelForm(forms.Form):
    __metaclass__ = ModelFormMeta

    def __init__(self, *args, **kwargs):
        super(ModelForm, self).__init__(*args, **kwargs)
        self._obj = kwargs.get('obj' or None)

    def validate(self, *args, **kwargs):
        ok = super(ModelForm, self).validate(*args, **kwargs)

        if not ok:
            return ok

        if not self._obj:
            self._obj = self._meta.model()

        self._obj = self._obj.from_dict(self.data, to_python=True)
        ok = self._obj.is_valid()
        self._errors = self._obj._errors
        #TODO: add errors to each form field
        return ok

    def save(self):
        if self.errors:
            raise ValueError("Could not save because form didn't validate")

        self._obj.save()
        return self._obj
