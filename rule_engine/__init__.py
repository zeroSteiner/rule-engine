#!/usr/bin/env python3
import ast
import operator
import re


import ply.lex as lex
import ply.yacc as yacc


################################################################################
# AST Definitions
################################################################################
class Expression(object):
    def __repr__(self):
        return "<{0} >".format(self.__class__.__name__)

    def evaluate(self, context):
        raise NotImplementedError()


class LogicExpression(Expression):
    __op = {'==': 'eq', '!=': 'ne', '=~': 'eq_re', '!~':  'ne_re', 'and': 'and', 'or': 'or'}
    __slots__ = ('type', 'left', 'right')
    def __init__(self, type_, left, right):
        self.type = type_
        self.left = left
        self.right = right

    def evaluate(self, context):
        evaluator = getattr(self, '_op_' + self.__op[self.type])
        return evaluator(context)

    def _op_eq(self, context):
        left, right = self.left.evaluate(context), self.right.evaluate(context)
        return operator.eq(left, right)

    def _op_ne(self, context):
        left, right = self.left.evaluate(context), self.right.evaluate(context)
        return operator.ne(left, right)

    def _op_eq_re(self, context):
        left, right = self.left.evaluate(context), self.right.evaluate(context)
        return context.regex(right, left) is not None

    def _op_ne_re(self, context):
        left, right = self.left.evaluate(context), self.right.evaluate(context)
        return context.regex(right, left) is None

    def _op_and(self, context):
        return bool(self.left.evaluate(context) and self.right.evaluate(context))

    def _op_or(self, context):
        return bool(self.left.evaluate(context) or self.right.evaluate(context))


class StringExpression(Expression):
    __slots__ = ('value',)
    def __init__(self, value):
        self.value = value

    def evaluate(self, context):
        return self.value


class SymbolExpression(Expression):
    __slots__ = ('name',)
    def __init__(self, name):
        self.name = name

    def evaluate(self, context):
        return context.resolve_symbol(self.name)


class Statement(object):
    __slots__ = ('expression',)
    def __init__(self, expression):
        self.expression = expression

    def evaluate(self, context):
        return self.expression.evaluate(context)


################################################################################
# Parser
################################################################################
class ParserBase(object):
    precedence = ()
    tokens = ()
    reserved = {}
    def __init__(self, debug=False):
        self.debug = debug
        # Build the lexer and parser
        self._lexer = lex.lex(module=self, debug=self.debug)
        self._parser = yacc.yacc(module=self, debug=self.debug, write_tables=self.debug)

    def parse(self, *args, **kwargs):
        kwargs['lexer'] = kwargs.pop('lexer', self._lexer)
        return self._parser.parse(*args, **kwargs)


class Parser(ParserBase):
    reserved = {
        'and': 'AND',
        'or':  'OR',
    }
    tokens = [
        'SYMBOL', 'STRING', 'LPAREN', 'RPAREN',
        'EQ', 'EQ_RE', 'NE', 'NE_RE'
    ] + list(reserved.values())

    # Tokens
    t_LPAREN           = r'\('
    t_RPAREN           = r'\)'
    t_EQ               = r'=='
    t_EQ_RE            = r'=~'
    t_NE               = r'!='
    t_NE_RE            = r'!~'
    t_STRING = r'(?P<quote>["\'])([^\\\n]|(\\.))*?(?P=quote)'

    t_ignore = ' \t'
    precedence = (
        ('left',     'AND', 'OR'),
        ('nonassoc', 'EQ', 'NE', 'EQ_RE', 'NE_RE'),  # Nonassociative operators
    )

    def t_SYMBOL(self, t):
        r'[a-zA-Z_][a-zA-Z0-9_]*'
        t.type = self.reserved.get(t.value, 'SYMBOL')
        return t

    def t_newline(self, t):
        r'\n+'
        t.lexer.lineno += t.value.count("\n")

    def t_error(self, t):
        print("Illegal character '%s'" % t.value[0])
        t.lexer.skip(1)

    # Parsing rules
    def p_statement_expr(self, p):
        'statement : expression'
        p[0] = Statement(p[1])

    def p_expression_logic(self, p):
        """
        expression : expression EQ    expression
                   | expression NE    expression
                   | expression AND   expression
                   | expression OR    expression
                   | expression EQ_RE expression
                   | expression NE_RE expression
        """
        p[0] = LogicExpression(p[2], p[1], p[3])

    def p_expression_group(self, p):
        'expression : LPAREN expression RPAREN'
        p[0] = p[2]

    def p_expression_symbol(self, p):
        'expression : SYMBOL'
        p[0] = SymbolExpression(p[1])

    def p_expression_string(self, p):
        'expression : STRING'
        p[0] = StringExpression(ast.literal_eval(p[1]))

    def p_error(self, p):
        if p:
            print("Syntax error at '%s'" % p.value)
        else:
            print("Syntax error at EOF")

################################################################################
# Rule API
################################################################################
class EvaluationContext(object):
    def __init__(self, symbols, symbol_resolver=None):
        self.symbols = symbols
        self.__symbol_resolver = symbol_resolver or operator.getitem

    def regex(self, pattern, symbol):
        return re.match(pattern, symbol)

    def resolve_symbol(self, name):
        return self.__symbol_resolver(self.symbols, name)


class Rule(object):
    parser = Parser()
    def __init__(self, rule_text):
        self.rule_ast = self.parser.parse(rule_text)

    def matches(self, thing):
        return bool(self.rule_ast.evaluate(EvaluationContext(thing)))
