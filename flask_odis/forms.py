from __future__ import absolute_import

import odis
import itertools

from .widgets import CheckboxSelectMultiple
from flask.ext.wtf import forms, fields, validators, ValidationError
from wtforms.form import FormMeta
from odis.utils import s

class SetMultipleField(fields.SelectMultipleField):
    '''
    ## On creating set fields

    Given a model set field on a form class.

        - Before initiating `obj` the set field on the form
          class cannot be true (unless optional).

        - We cannot extract choices from the set field before we
          have an `obj`.

        - When initialization a form instance, given `obj`, we
          can fetch choices from `obj.setfield`.

        - Creating a new instance of `obj` using a ModelForm
          with a set field which is required is not possible. We
          need to manually add viable choices when the set field
          is required and empty.

    ## On updating set fields

    Given a model set field on a form class.

        - Before initiating the form class set field choices
          cannot be computed.

        - Given `obj` on init we can fetch choices from
          `obj.setfield`. All choices computed in this way are
          by definition `selected`.

        - Adding something to the set field is invalid as the
          new option is not a valid choice.
    '''
    widget = CheckboxSelectMultiple()

    def __init__(self, *args, **kwargs):
        kwargs['choices'] = kwargs.get('choices', [])
        super(SetMultipleField, self).__init__(*args, **kwargs)

    def iter_choices(self):
        for value, label in self.choices:
            selected = self.data is not None and self.coerce(value) in self.data
            yield (value, label, selected)

    def populate_obj(self, obj, name):
       setattr(obj, '_' + name + '_data', self.data)

class SortedSetMultipleField(SetMultipleField):
    def __init__(self, *args, **kwargs):
        raise NotImplemented

class RelMultipleField(SetMultipleField):
    '''
    ## On creating rel fields.

    Given a rel field on a form class.

        - Creating a new instance of `obj` using a ModelForm
          with a rel field which is required is possible. One or
          more choices can be selected from the default choices
          created.

    ## On updating rel fields.

    Given a rel field on a form class.

        - Before initiating the form class rel field choices
          can be computed by taking the `model.relfield.model`
          and using its default queryset as choices.

        - Default choices are by definition not selected.

        - Given `obj` on init we can find selected choices by
          comparing default choices and `obj.relfield`
    '''

    def __init__(self, queryset, *args, **kwargs):
        kwargs.setdefault('coerce', int)
        super(RelMultipleField, self).__init__(*args, **kwargs)
        self.queryset = queryset.all()

    def iter_choices(self):
        print 'itererate', self.data
        for obj in self.queryset:
            selected = self.data is not None and self.coerce(obj.pk) in self.data
            yield (obj.pk, obj, selected)

    def process_data(self, value):
        print 'init', value
        values = itertools.imap(lambda o: o.pk, value)
        super(RelMultipleField, self).process_data(values)

    def process_formdata(self, valuelist):
        super(RelMultipleField, self).process_formdata(valuelist)
        print 'POST data', self.data

    def pre_validate(self, form):
        if self.data:
            values = frozenset(o.pk for o in self.queryset)
            print 'validate', self.data, values
            for d in self.data:
                if d not in values:
                    raise ValidationError(self.gettext('`%s` not a valid choice' % d))

fields_table = {
    'field': fields.StringField,
    'charfield': fields.StringField,
    'integerfield': fields.IntegerField,
    'foreignfield': fields.IntegerField,
    'datetimefield': fields.DateTimeField,
    'datefield': fields.DateField,
    'setfield': SetMultipleField,
    'sortedsetfield': SortedSetMultipleField,
    'relfield': RelMultipleField,
}

def is_coll_field(f):
    return f.__class__.__name__.lower() in ('setfield', 'sortedsetfield', 'relfield')

def formfield_from_modelfield(field):
    field_type = field.__class__.__name__.lower()
    opts = {
        'validators': []
    }

    default = getattr(field, 'default', odis.EMPTY)

    if field_type == 'relfield':
        opts['queryset'] = field.model.obj

    if is_coll_field(field):
        opts['validators'].append(validators.optional())
    elif default != odis.EMPTY or getattr(field, 'nil', False):
        opts['validators'].append(validators.optional())
    else:
        opts['validators'].append(validators.required())

    if default != odis.EMPTY:
        opts['default'] = default

    if getattr(field, 'choices', False):
        opts['choices'] = field.choices

    opts['label'] = field.verbose_name or field.name

    if 'choices' in opts:
        form_field = fields.SelectField
        #opts['coerce'] = field.to_python
    else:
        form_field = fields_table[field_type]

    return form_field(**opts)

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
            # find decleared fields
            decleared_fields = {}

            for k, v in attrs.items():
                if hasattr(v, '_formfield'):
                    decleared_fields[k] = v

            # TODO: find decleared fields in bases?
            new_cls.model_fields = fields_for_model(opts.model, opts.fields, opts.exclude)

            for name, f in dict(new_cls.model_fields, **decleared_fields).items():
                setattr(new_cls, name, f)

        return new_cls

class ModelForm(forms.Form):
    __metaclass__ = ModelFormMeta

    def __init__(self, *args, **kwargs):
        super(ModelForm, self).__init__(*args, **kwargs)
        self._obj = kwargs.get('obj' or None)

        if self._obj:
            for k in self._coll_fields():
                query = getattr(self._obj, k, None)
                field = getattr(self, k)

                if not field.choices:
                    field.choices = ((o, o) for o in query.all())

    def validate(self, *args, **kwargs):
        if not super(ModelForm, self).validate(*args, **kwargs):
            return False

        if not self._obj:
            self._obj = self._meta.model()

        self.populate_obj(self._obj)

        ok = self._obj.is_valid()
        self._errors = self._obj.errors

        for k, v in self._errors.items():
            if k in self._fields:
                self._fields[k].errors = (v,)
            else:
                # todo, add to __all__
                pass

        return ok

    def populate_obj(self, obj):
        super(ModelForm, self).populate_obj(obj)

    def _coll_fields(self):
        'find all coll_fields for the current form'
        return filter(lambda k: k in self._obj._coll_fields, self._fields)

    def save(self):
        if self._errors:
            raise ValueError("Could not save because form didn't validate")

        if not self._obj:
            self._obj = self._meta.model()

        self.populate_obj(self._obj)
        self._obj.save()
        self.save_coll()
        return self._obj

    def save_coll(self):
        for k in self._coll_fields():
            f_type = self._obj._coll_fields.get(k, None)
            f = getattr(self._obj, k, None)
            data = getattr(self._obj, '_' + k + '_data', None)

            if isinstance(f_type, odis.SetField):
                f.replace(*data)
            elif isinstance(f_type, odis.SortedSetField):
                for o in data:
                    f.add(o)
                    # TODO what about score?
            elif isinstance(f_type, odis.RelField):
                f.add(*(f_type.model.obj.get(pk=o) for o in data))

        return self._obj
