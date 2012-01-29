from cgi import escape
from wtforms.widgets import html_params, HTMLString

class CheckboxSelectMultiple(object):
    'Field must provide `iter_choices()` which yields `(value, label, selected)`.'
    def __call__(self, field, **kwargs):
        kwargs.setdefault('type', 'checkbox')

        html = [u'<ul>']

        for i, (val, label, selected) in enumerate(field.iter_choices()):
            id = u'id_%s_%s' % (field.name, i)
            options = dict(kwargs, value=val, id=id, name=field.name)

            if selected:
                print 'was selected'
                options['checked'] = True

            html.append(u'<li><label %s><input %s> %s</label></li>' % (
                html_params(**{'for': id}),
                html_params(**options),
                escape(unicode(label))))

        html.append(u'</ul>')

        return HTMLString(u''.join(html))

