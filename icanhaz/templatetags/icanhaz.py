from django import template
from django.template import Template

from ..conf import conf
from ..loading import find, ICanHazTemplateNotFound



register = template.Library()



class ICanHazNode(template.Node):
    def __init__(self, name):
        self.name = template.Variable(name)


    def render(self, context):
        name = self.name.resolve(context)

        try:
            filepath = find(name)
            fp = open(filepath, "r")
            output = fp.read()
            t = Template(output)
            output = t.render(context)
            fp.close()
            output = ('<script id="%s" type="text/html">\n'
                      % name) + output + "\n</script>\n"
        except (IOError, ICanHazTemplateNotFound):
            output = ""
            if conf.DEBUG:
                raise

        return output



@register.tag
def icanhaz(parser, token):
    """
    Finds the ICanHaz template for the given name and renders it surrounded by
    the requisite ICanHaz <script> tags.

    """
    bits = token.contents.split()
    if len(bits) not in [2, 3]:
        raise template.TemplateSyntaxError(
            "'icanhaz' tag takes one argument: the name/id of the template")
    return ICanHazNode(bits[1])


class VerbatimNode(template.Node):
    def __init__(self, text_and_nodes):
        self.text_and_nodes = text_and_nodes

    def render(self, context):
        output = ""

        # If its text we concatenate it, otherwise it's a node and we render it
        for bit in self.text_and_nodes:
            if isinstance(bit, basestring):
                output += bit
            else:
                output += bit.render(context)

        return output

@register.tag
def verbatim(parser, token):
    """
    Copied from https://gist.github.com/893408

    Wrap {% verbatim %} and {% endverbatim %} around those
    blocks of jQuery templates to avoid conflict with django variable templates {{ }}

    this template tag allows you to use tags like url {% url name %}, {% trans "bar" %} or {% csrf_token %}
    on mustache templates.

    Thanks to Miguel Angel Araujo & Eric Florenzano for this code
    """
    text_and_nodes = []
    while 1:
        token = parser.tokens.pop(0)
        if token.contents == 'endverbatim':
            break

        if token.token_type == template.TOKEN_VAR:
            text_and_nodes.append('{{')
            text_and_nodes.append(token.contents)

        elif token.token_type == template.TOKEN_TEXT:
            text_and_nodes.append(token.contents)

        elif token.token_type == template.TOKEN_BLOCK:
            try:
                command = token.contents.split()[0]
            except IndexError:
                parser.empty_block_tag(token)

            try:
                compile_func = parser.tags[command]
            except KeyError:
                parser.invalid_block_tag(token, command, None)
            try:
                node = compile_func(parser, token)
            except template.TemplateSyntaxError, e:
                if not parser.compile_function_error(token, e):
                    raise

            text_and_nodes.append(node)

        if token.token_type == template.TOKEN_VAR:
            text_and_nodes.append('}}')

    return VerbatimNode(text_and_nodes)
