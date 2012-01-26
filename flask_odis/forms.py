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
    'setfield': fields.StringField,
    'sortedsetfield': fields.StringField,
    'relfield': fields.StringField,
}

def formfield_from_modelfield(field):
    data = {
        'validators': []
    }

    default = getattr(field, 'default', odis.EMPTY)

    if default != odis.EMPTY or getattr(field, 'nil', False) == True:
        data['validators'].append(validators.optional())
    else:
        data['validators'].append(validators.required())

    if default != odis.EMPTY:
        data['default'] = default

    if getattr(field, 'choices', False):
        data['choices'] = field.choices

    data['label'] = field.verbose_name or field.name

    field_type = field.__class__.__name__.lower()

    if 'choices' in data:
        form_field = fields.SelectField
        data['coerce'] = field.to_python
    else:
        form_field = translate[field_type]

    if field_type in ('setfield', 'sortedsetfield', 'relfield'):
        return fields.FieldList(form_field(**data))
    return form_field(**data)

def fields_for_model(model, fields=None, exclude=None):
    field_dict = {}

    for name, f in dict(model._fields, **model._coll_fields).items():
        if fields and not name in fields:
            continue

        if exclude and name in exclude:
            continue

        if name in ('pk',):
            continue

        field_dict[name] = formfield_from_modelfield(f)
    return field_dict

class ModelFormOptions(object):
    def __init__(self, options=None):
        self.model = getattr(options, 'model', None)
        self.fields = getattr(options, 'fields', None)
        self.exclude = getattr(options, 'exclude', None)

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
        if not super(ModelForm, self).validate(*args, **kwargs):
            return False

        if not self._obj:
            self._obj = self._meta.model()

        self.populate_obj(self._obj)
        ok = self._obj.is_valid()
        self._errors = self._obj._errors

        for k, v in self._errors.items():
            if k in self._fields:
                s()
                self._fields[k].errors = (v,)
            else:
                # todo, add to __all__
                pass

        return ok

    def populate_obj(self, obj):
        super(ModelForm, self).populate_obj(obj)

    def save(self):
        if self.errors:
            raise ValueError("Could not save because form didn't validate")

        self._obj.save()
        return self._obj
