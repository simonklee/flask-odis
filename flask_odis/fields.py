import itertools

from flask.ext.wtf import fields, ValidationError
from .widgets import CheckboxSelectMultiple

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
        try:
            it = itertools.imap(lambda o: o.pk, value)
            self.data = list(self.coerce(v) for v in it)
        except (ValueError, TypeError):
            self.data = None

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
