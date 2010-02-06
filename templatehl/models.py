from django.conf import settings
from django import template 
from django.template import debug, tag_re, NodeList, VariableNode, TemplateSyntaxError
from django.template import loader_tags, TextNode
from django.utils.encoding import force_unicode
from django.utils.html import escape
from django.utils.safestring import SafeData, EscapeData


class MyDebugLexer(debug.DebugLexer):
    def tokenize(self):
        "Return a list of tokens from a given template_string"
        result, upto = [], 0
        for match in tag_re.finditer(self.template_string):
            start, end = match.span()
            if start > upto:
                result.append(self.create_token(self.template_string[upto:start], (upto, start), False))
                upto = start
            result.append(self.create_token(self.template_string[start:end], (start, end), True))
            upto = end
        last_bit = self.template_string[upto:]
        if last_bit:
            result.append(self.create_token(last_bit, (upto, upto + len(last_bit)), False))
        return result

    def create_token(self, token_string, source, in_tag):
        token = super(MyDebugLexer, self).create_token(token_string, source, in_tag)
        token.source = self.origin, source
        #print self.origin # /home/jonson/pypath/opiv/templates/head.html
        return token

class MyDebugParser(debug.DebugParser):
    def enter_command(self, command, token):
        #print 'Enter comm', command
        if command.lower() == 'block':
            loader_origin = token.source[0]
            #print 'Block START', token.source, loader_origin.name
            token.origin_name = loader_origin.name
        super(MyDebugParser, self).enter_command(command, token)

    def exit_command(self):
        #self.command_stack.pop()
        #print 'Exit command'
        super(MyDebugParser, self).exit_command()

def compile_string(template_string, origin):
    "Compiles template_string into NodeList ready for rendering"
    if settings.TEMPLATE_DEBUG:
        lexer_class, parser_class = MyDebugLexer, MyDebugParser
    else:
        from django.template import Lexer, Parser
        lexer_class, parser_class = Lexer, Parser
    lexer = lexer_class(template_string, origin)
    parser = parser_class(lexer.tokenize())
    return parser.parse()

def block_description_callback(**highlight_args):
    #return u'<!-- block: %(block)s , file: %(fname)s -->' % highlight_args
    return u'<debug block="%(block)s" file="%(fname)s" />' % highlight_args

def do_block(parser, token):
    """
    Define a block that can be overridden by child templates.
    """
    bits = token.contents.split()
    if len(bits) != 2:
        raise TemplateSyntaxError, "'%s' tag takes only one argument" % bits[0]
    block_name = bits[1]
    # Keep track of the names of BlockNodes found in this template, so we can
    # check for duplication.
    try:
        if block_name in parser.__loaded_blocks:
            raise TemplateSyntaxError, "'%s' tag with name '%s' appears more than once" % (bits[0], block_name)
        parser.__loaded_blocks.append(block_name)
    except AttributeError: # parser.__loaded_blocks isn't a list yet
        parser.__loaded_blocks = [block_name]
    nodelist = parser.parse(('endblock', 'endblock %s' % block_name))

    # block origin highlight node
    if hasattr(token, 'origin_name'):
        hl_args = {
            'fname': token.origin_name,
            'block': block_name
        }
        hl_node = TextNode(block_description_callback(**hl_args))
        nodelist.append(hl_node)

    parser.delete_first_token()
    return loader_tags.BlockNode(block_name, nodelist)


# ugly kind of overloading
template.compile_string = compile_string
register = loader_tags.register
register.tag('block', do_block)
#loader_tags.do_block = do_block
