from __future__ import absolute_import

import odis

from cgi import escape
from flask.ext.wtf import forms, fields, validators, widgets, ValidationError
from wtforms.form import FormMeta
from wtforms.widgets import html_params, HTMLString
from odis.utils import s

class SetSelectField(fields.SelectFieldBase):
    widget = widgets.Select()

    def __init__(self, label=None, validators=None, queryset=None, nil=False, **kwargs):
        super(SetSelectField, self).__init__(label, validators, **kwargs)
        self.nil = nil
        self._set_data(None)

        if queryset is not None:
            self.queryset = queryset.all()
        else:
            self.queryset = []

        self.get_label = lambda x: x

    def _get_data(self):
        if self._formdata is not None:
            for obj in self.queryset:
                if obj.pk == self._formdata:
                    self._set_data(obj)
                    break
        return self._data

    def _set_data(self, data):
        self._data = data
        self._formdata = None

    data = property(_get_data, _set_data)

    def iter_choices(self):
        if self.nil:
            yield (u'__None', u'', self.data is None)

        for obj in self.queryset:
            yield (obj.pk, self.get_label(obj), obj == self.data)

    def process_formdata(self, valuelist):
        if valuelist:
            if valuelist[0] == '__None':
                self.data = None
            else:
                self._data = None
                self._formdata = int(valuelist[0])

    def pre_validate(self, form):
        if not self.nil or self.data is not None:
            for obj in self.queryset:
                if self.data == obj:
                    break
            else:
                raise ValidationError(self.gettext('Not a valid choice'))

    def populate_obj(self, obj, name):
        setattr(obj, '_' + name + '_data', [self.data])

class RelSelectField(SetSelectField):
    def __init__(self, *args, **kwargs):
        super(RelSelectField, self).__init__(*args, **kwargs)
        self.get_label = lambda x: x.pk

    def populate_obj(self, obj, name):
        setattr(obj, '_' + name + '_data', [self.data.pk])

class CheckboxSelectMultiple(object):
    'Field must provide `iter_choices()` which yields `(value, label, selected)`.'
    def __call__(self, field, **kwargs):
        kwargs.setdefault('type', 'checkbox')

        html = [u'<ul>']

        for i, (val, label, selected) in enumerate(field.iter_choices()):
            id = u'id_%s_%s' % (field.name, i)
            options = dict(kwargs, value=val, id=id, name=field.name)

            if selected:
                options['selected'] = True

            html.append(u'<li><label %s><input %s> %s</label></li>' % (
                html_params(**{'for': id}),
                html_params(**options),
                escape(unicode(label))))

        html.append(u'</ul>')

        return HTMLString(u''.join(html))

class SetMultipleField(fields.SelectMultipleField):
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

fields_table = {
    'field': fields.StringField,
    'charfield': fields.StringField,
    'integerfield': fields.IntegerField,
    'foreignfield': fields.IntegerField,
    'datetimefield': fields.DateTimeField,
    'datefield': fields.DateField,
    'setfield': SetMultipleField,
    'sortedsetfield': fields.SelectMultipleField,
    'relfield': fields.SelectMultipleField,
}

def is_coll_field(f):
    return f.__class__.__name__.lower() in ('setfield', 'sortedsetfield', 'relfield')

def formfield_from_modelfield(field):
    field_type = field.__class__.__name__.lower()
    opts = {
        'validators': []
    }

    default = getattr(field, 'default', odis.EMPTY)

    if default != odis.EMPTY or getattr(field, 'nil', False):
        opts['validators'].append(validators.optional())

        if is_coll_field(field):
            opts['nil'] = True
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
                f.add(*data)

        return self._obj
