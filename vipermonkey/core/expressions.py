#!/usr/bin/env python
"""
ViperMonkey: VBA Grammar - Expressions

ViperMonkey is a specialized engine to parse, analyze and interpret Microsoft
VBA macros (Visual Basic for Applications), mainly for malware analysis.

Author: Philippe Lagadec - http://www.decalage.info
License: BSD, see source code or documentation

Project Repository:
https://github.com/decalage2/ViperMonkey
"""

# === LICENSE ==================================================================

# ViperMonkey is copyright (c) 2015-2016 Philippe Lagadec (http://www.decalage.info)
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without modification,
# are permitted provided that the following conditions are met:
#
#  * Redistributions of source code must retain the above copyright notice, this
#    list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.


# ------------------------------------------------------------------------------
# CHANGELOG:
# 2015-02-12 v0.01 PL: - first prototype
# 2015-2016        PL: - many updates
# 2016-06-11 v0.02 PL: - split vipermonkey into several modules
# 2016-10-10 v0.03 PL: - added multiplication operator * to expressions
#                      - added floor division operator \ to expressions

__version__ = '0.03'

# ------------------------------------------------------------------------------
# TODO:

# --- IMPORTS ------------------------------------------------------------------

from identifiers import *
from lib_functions import *
from literals import *
from operators import *
import procedures
from vba_object import eval_arg

from logger import log
log.debug('importing expressions')

# --- SIMPLE NAME EXPRESSION -------------------------------------------------

class SimpleNameExpression(VBA_Object):
    """
    Identifier referring to a variable within a VBA expression:
    single identifier with no qualification or argument list
    """

    def __init__(self, original_str, location, tokens):
        super(SimpleNameExpression, self).__init__(original_str, location, tokens)
        self.name = tokens.name
        log.debug('parsed %r as SimpleNameExpression' % self)

    def __repr__(self):
        return '%s' % self.name

    def eval(self, context, params=None):
        log.debug('try eval variable/function %r' % self.name)
        try:
            value = context.get(self.name)
            log.debug('get variable %r = %r' % (self.name, value))
            if (isinstance(value, procedures.Function)):
                log.debug('evaluating function %r' % value)
                value = value.eval(context)
                log.debug('evaluated function %r = %r' % (self.name, value))
            return value
        except KeyError:
            log.error('Variable %r not found' % self.name)
            return ""


# 5.6.10 Simple Name Expressions
# A simple name expression consists of a single identifier with no qualification or argument list.

# simple-name-expression = name

# TODO:
# simple_name_expression = entity_name('name')
simple_name_expression = Optional(CaselessKeyword("ByVal").suppress()) + TODO_identifier_or_object_attrib('name')
simple_name_expression.setParseAction(SimpleNameExpression)


# --- INSTANCE EXPRESSIONS ------------------------------------------------------------

class InstanceExpression(VBA_Object):
    """
    An instance expression consists of the keyword "Me".
    It represents the current instance of the type defined by the
    enclosing class module and has this type as its value type.
    """

    def __init__(self, original_str, location, tokens):
        super(InstanceExpression, self).__init__(original_str, location, tokens)
        log.debug('parsed %r as InstanceExpression' % self)

    def __repr__(self):
        return 'Me'

    def eval(self, context, params=None):
        raise NotImplementedError


# 5.6.11 Instance Expressions
# An instance expression consists of the keyword Me.

# instance-expression = "me"

# Static semantics. An instance expression is classified as a value. The declared type of an instance
# expression is the type defined by the class module containing the enclosing procedure. It is invalid
# for an instance expression to occur within a procedural module.
# Runtime semantics. The keyword Me represents the current instance of the type defined by the
# enclosing class module and has this type as its value type.

instance_expression = CaselessKeyword('Me').suppress()
instance_expression.setParseAction(InstanceExpression)

# --- MEMBER ACCESS EXPRESSIONS ------------------------------------------------------------

# 5.6.12 Member Access Expressions
# A member access expression is used to reference a member of an entity.

# member-access-expression = l-expression NO-WS "." unrestricted-name
# member-access-expression =/ l-expression LINE-CONTINUATION "." unrestricted-name

# NOTE: Here we assume that all line-continuation characters have been removed,
#       so the 2nd part of member-access-expression does not apply.
#       Moreover, there may be whitespaces before the dot, due to the removal.

# Examples: varname.attrname, varname(2).attrname, varname .attrname

class MemberAccessExpression(VBA_Object):
    """
    Handle member access expressions.
    """

    def __init__(self, original_str, location, tokens):
        super(MemberAccessExpression, self).__init__(original_str, location, tokens)
        log.debug("member: tokens = %r" % tokens)
        tokens = tokens[0][0]
        log.debug("member: tokens (1) = %r" % tokens)
        self.rhs = tokens.rhs
        self.lhs = tokens.lhs
        log.debug('parsed %r as MemberAccessExpression' % self)

    def __repr__(self):
        return str(self.lhs) + "." + str(self.rhs)

    def eval(self, context, params=None):
        # TODO: Need to actually have some sort of object model. For now
        # just treat this as a variable access.
        tmp_lhs = eval_arg(self.lhs, context)
        tmp_rhs = eval_arg(self.rhs, context)

        # If the final element in the member expression is a function call,
        # the result should be the result of the function call. Otherwise treat
        # it as a fancy variable access.
        if (isinstance(self.rhs, Function_Call)):
            return tmp_rhs
        else:
            return eval_arg(str(tmp_lhs) + "." + str(tmp_rhs), context)

log.debug('l_expression = Forward()')
# need to use Forward(), because the definition of l-expression is recursive:
l_expression = Forward()

function_call_limited = Forward()
function_call = Forward()
member_object = function_call_limited | unrestricted_name
member_access_expression = Group( Group( member_object("lhs") + OneOrMore( Suppress(".") + member_object("rhs") ) ) )
member_access_expression.setParseAction(MemberAccessExpression)

# TODO: 
member_access_expression_limited = Group( Group( member_object("lhs") + Suppress(".") + unrestricted_name("rhs") ) )
#member_access_expression_limited = Group( Group( function_call_limited("lhs") + Suppress(".") + unrestricted_name("rhs") ) )
member_access_expression_limited.setParseAction(MemberAccessExpression)

# --- ARGUMENT LISTS ---------------------------------------------------------

# 5.6.16.8   AddressOf Expressions
# addressof-expression = "addressof" procedure-pointer-expression
# procedure-pointer-expression = simple-name-expression / member-access-expression

# Examples: addressof varname, addressof varname(2).attrname

# IMPORTANT: member_access_expression must come before simple_name_expression:
procedure_pointer_expression = member_access_expression | simple_name_expression
addressof_expression = CaselessKeyword("addressof").suppress() + procedure_pointer_expression

# 5.6.13.1   Argument Lists
# An argument list represents an ordered list of positional arguments and a set of named arguments
# that are used to parameterize an expression.
# argument-list = [positional-or-named-argument-list]
# positional-or-named-argument-list = *(positional-argument ",") required-positional-argument
# positional-or-named-argument-list =/   *(positional-argument ",") named-argument-list
# positional-argument = [argument-expression]
# required-positional-argument = argument-expression
# named-argument-list = named-argument *("," named-argument)
# named-argument = unrestricted-name ":""=" argument-expression
# argument-expression = ["byval"] expression
# argument-expression =/  addressof-expression

argument_expression = (Optional(CaselessKeyword("byval")) + expression) | addressof_expression

named_argument = unrestricted_name + Suppress(":=") + argument_expression
named_argument_list = delimitedList(named_argument)
required_positional_argument = argument_expression
positional_argument = Optional(argument_expression)
# IMPORTANT: here named_argument_list must come before required_positional_argument
positional_or_named_argument_list = Optional(delimitedList(positional_argument) + ",") \
                                    + (named_argument_list | required_positional_argument)
argument_list = Optional(positional_or_named_argument_list)

# --- INDEX EXPRESSIONS ------------------------------------------------------

# 5.6.13   Index Expressions
# An index expression is used to parameterize an expression by adding an argument list to its
# argument list queue.
# index-expression = l-expression "(" argument-list ")"

#index_expression = l_expression + Suppress("(") + argument_list + Suppress(")")
index_expression = simple_name_expression + Suppress("(") + simple_name_expression + Suppress(")")

# --- DICTIONARY ACCESS EXPRESSIONS ------------------------------------------------------

# 5.6.14   Dictionary Access Expressions
# A dictionary access expression is an alternate way to invoke an object's default member with a
# String parameter.
# dictionary-access-expression = l-expression  NO-WS "!" NO-WS unrestricted-name
# dictionary-access-expression =/  l-expression  LINE-CONTINUATION "!" NO-WS unrestricted-name
# dictionary-access-expression =/  l-expression  LINE-CONTINUATION "!" LINE-CONTINUATION
# unrestricted-name

# NOTE: Here we assume that all line-continuation characters have been removed,
#       so the 2nd and 3rd parts of dictionary-access-expression do not apply.
#       Moreover, there may be whitespaces before and after the "!", due to the removal.

dictionary_access_expression = l_expression + Suppress("!") + unrestricted_name

# --- WITH EXPRESSIONS ------------------------------------------------------

# 5.6.15   With Expressions
# A With expression is a member access or dictionary access expression with its <l-expression>
# implicitly supplied by the innermost enclosing With block.
# with-expression = with-member-access-expression / with-dictionary-access-expression
#
# with-member-access-expression = "." unrestricted-name
# with-dictionary-access-expression = "!" unrestricted-name

with_member_access_expression = Suppress(".") + unrestricted_name
with_dictionary_access_expression = Suppress("!") + unrestricted_name
with_expression = with_member_access_expression | with_dictionary_access_expression

# --- EXPRESSIONS ------------------------------------------------------------

# 5.6 Expressions
# An expression is a hierarchy of values, identifiers and subexpressions that evaluates to a value, or
# references an entity such as a variable, constant, procedure or type. Besides its tree of
# subexpressions, an expression also has a declared type which can be determined statically, and a
# value type which may vary depending on the runtime value of its values and subexpressions. This
# section defines the syntax of expressions, their static resolution rules and their runtime evaluation
# rules.

# expression = value-expression / l-expression
# value-expression = literal-expression / parenthesized-expression / typeof-is-expression /
# new-expression / operator-expression
# l-expression = simple-name-expression / instance-expression / member-access-expression /
# index-expression / dictionary-access-expression / with-expression

new_expression = Forward()
log.debug('l_expression <<= index_expression | simple_name_expression')
# TODO: should go from the most specific to least specific
#l_expression <<= index_expression | simple_name_expression
#l_expression <<= simple_name_expression
#l_expression << simple_name_expression
l_expression << (member_access_expression ^ new_expression) | instance_expression | dictionary_access_expression | with_expression | simple_name_expression

# TODO: Redesign l_expression to avoid recursion error...


# --- FUNCTION CALL ---------------------------------------------------------

class Function_Call(VBA_Object):
    """
    Function call within a VBA expression
    """

    # List of interesting functions to log calls to.
    log_funcs = ["CreateProcessA", "CreateProcessW", ".run", "CreateObject"]
    
    def __init__(self, original_str, location, tokens):
        super(Function_Call, self).__init__(original_str, location, tokens)
        self.name = str(tokens.name)
        log.debug('Function_Call.name = %r' % self.name)
        assert isinstance(self.name, basestring)
        self.params = tokens.params
        log.debug('parsed %r' % self)

    def __repr__(self):
        parms = ""
        first = True
        for parm in self.params:
            if (not first):
                parms += ", "
            first = False
            parms += str(parm)
        return '%s(%r)' % (self.name, parms)

    def eval(self, context, params=None):
        params = eval_args(self.params, context=context)
        log.info('calling Function: %s(%s)' % (self.name, repr(params)[1:-1]))
        save = False
        for func in Function_Call.log_funcs:
            if (self.name.lower().endswith(func.lower())):
                save = True
                break
        if (save):
            context.report_action(self.name, repr(params)[1:-1], 'Interesting Function Call')
        try:
            f = context.get(self.name)

            # Is this actually an array access?
            if ((isinstance(f, list) and len(params) > 0)):
                tmp = f
                # Try to gues whether we are accessing a character in a string.
                if ((len(f) == 1) and (isinstance(f[0], str))):
                    tmp = f[0]
                log.debug('Array Access: %r[%r]' % (tmp, params[0]))
                index = int(params[0])
                try:
                    r = tmp[index]
                    log.debug('Returning: %r' % r)
                    return r
                except:
                    log.error('Array Access Failed: %r[%r]' % (tmp, params[0]))
                    return ""
            log.debug('Calling: %r' % f)
            if (f is not None):
                if (not(isinstance(f, str)) and
                    not(isinstance(f, list)) and
                    not(isinstance(f, unicode))):
                    return f.eval(context=context, params=params)
                elif (len(params) > 0):

                    # Looks like this is actually an array access.
                    log.debug("Looks like array access.")
                    try:
                        i = int(params[0])
                        return f[i]
                    except:
                        log.error("Array access %r[%r] failed." % (f, params[0]))
                    else:
                        log.error("Improper type for function.")
                        return None
            else:
                log.error('Function %r resolves to None' % self.name)
                return None

        except KeyError:

            # If something like Application.Run("foo", 12) is called, foo(12) will be run.
            # Try to handle that.
            func_name = str(self.name)
            if ((func_name == "Application.Run") or (func_name == "Run")):

                # Pull the name of what is being run from the 1st arg.
                new_func = params[0]

                # The remaining params are passed as arguments to the other function.
                new_params = params[1:]

                # See if we can run the other function.
                log.debug("Try indirect run of function '" + new_func + "'")
                try:
                    s = context.get(new_func)
                    return s.eval(context=context, params=new_params)
                except KeyError:
                    pass
            log.error('Function %r not found' % self.name)
            return None

# generic function call, avoiding known function names:

# comma-separated list of parameters, each of them can be an expression:
boolean_expression = Forward()
expr_list_item = expression ^ boolean_expression
expr_list = delimitedList(expr_list_item)

# TODO: check if parentheses are optional or not. If so, it can be either a variable or a function call without params
function_call <<= CaselessKeyword("nothing") | \
                  (NotAny(reserved_keywords) + (member_access_expression_limited('name') | lex_identifier('name')) + Suppress(Optional('$')) + Suppress('(') + Optional(expr_list('params')) + Suppress(')'))
function_call.setParseAction(Function_Call)

function_call_limited <<= CaselessKeyword("nothing") | \
                          (NotAny(reserved_keywords) + lex_identifier('name') + Suppress(Optional('$')) + Suppress('(') + Optional(expr_list('params')) + Suppress(')'))
function_call_limited.setParseAction(Function_Call)

# --- EXPRESSION ITEM --------------------------------------------------------

# expression item:
# - known functions first
# - then generic function call
# - then identifiers
# - finally literals (strings, integers, etc)
# expr_item = (chr_ | asc | strReverse | environ | literal | function_call | simple_name_expression)
#expr_item = (chr_ | asc | strReverse | literal | function_call | simple_name_expression)
expr_item = ( float_literal | l_expression | chr_ | function_call | simple_name_expression | asc | strReverse | literal )

# --- OPERATOR EXPRESSION ----------------------------------------------------

# expression with operator precedence:
# TODO: 5.6.9 Operator Expressions
# see MS-VBAL 5.6.9.1 Operator Precedence and Associativity

# About operators associativity:
# https://en.wikipedia.org/wiki/Operator_associativity
# "In order to reflect normal usage, addition, subtraction, multiplication,
# and division operators are usually left-associative while an exponentiation
# operator (if present) is right-associative. Any assignment operators are
# also typically right-associative."

expression <<= (infixNotation(expr_item,
                                  [
                                      # ("^", 2, opAssoc.RIGHT), # Exponentiation
                                      # ("-", 1, opAssoc.LEFT), # Unary negation
                                      ("*", 2, opAssoc.LEFT, Multiplication),
                                      ("/", 2, opAssoc.LEFT, Division),
                                      ("\\", 2, opAssoc.LEFT, FloorDivision),
                                      (CaselessKeyword("mod"), 2, opAssoc.RIGHT, Mod),
                                      ("-", 2, opAssoc.LEFT, Subtraction),
                                      ("+", 2, opAssoc.LEFT, Sum),
                                      ("&", 2, opAssoc.LEFT, Concatenation),
                                      (CaselessKeyword("xor"), 2, opAssoc.LEFT, Xor),
                                  ]))
expression.setParseAction(lambda t: t[0])

# TODO: constant expressions (used in some statements)
# constant expression: expression without variables or function calls, that can be evaluated to a literal:
expr_const = Forward()
chr_const = Suppress(
    Combine(CaselessLiteral('Chr') + Optional(Word('BbWw', max=1)) + Optional('$')) + '(') + expr_const + Suppress(')')
chr_const.setParseAction(Chr)
asc_const = Suppress(CaselessKeyword('Asc') + '(') + expr_const + Suppress(')')
asc_const.setParseAction(Asc)
strReverse_const = Suppress(CaselessLiteral('StrReverse') + Literal('(')) + expr_const + Suppress(Literal(')'))
strReverse_const.setParseAction(StrReverse)
environ_const = Suppress(CaselessKeyword('Environ') + '(') + expr_const + Suppress(')')
environ_const.setParseAction(Environ)
expr_const_item = (chr_const | asc_const | strReverse_const | environ_const | literal)
expr_const <<= infixNotation(expr_const_item,
                             [
                                 ("+", 2, opAssoc.LEFT, Sum),
                                 ("&", 2, opAssoc.LEFT, Concatenation),
                             ])

# ----------------------------- BOOLEAN expressions --------------

class BoolExprItem(VBA_Object):
    """
    A comparison expression or other item appearing in a boolean expression.
    """

    def __init__(self, original_str, location, tokens):
        super(BoolExprItem, self).__init__(original_str, location, tokens)
        assert (len(tokens) > 0)
        self.lhs = None
        self.op = None
        self.rhs = None
        tokens = tokens[0]
        try:
            self.lhs = tokens[0]
            if (len(tokens) == 3):
                self.op = tokens[1].replace("'", "")
                self.rhs = tokens[2]
            elif (len(tokens) > 3):
                self.op = tokens[1].replace("'", "")
                self.rhs = BoolExprItem(original_str, location, [tokens[2:], None])
            else:
                log.error("BoolExprItem: Unexpected # tokens in %r" % tokens)
        except TypeError:
            self.lhs = tokens
        log.debug('parsed %r as BoolExprItem' % self)

    def __repr__(self):
        if (self.op is not None):
            return self.lhs.__repr__() + " " + self.op + " " + self.rhs.__repr__()
        elif (self.lhs is not None):
            return self.lhs.__repr__()
        else:
            log.error("BoolExprItem: Improperly parsed.")
            return ""

    def eval(self, context, params=None):

        # We always have a LHS. Evaluate that in the current context.
        lhs = self.lhs
        try:
            lhs = eval_arg(self.lhs, context)
        except AttributeError:
            pass

        # Do we have an operator or just a variable reference?
        if (self.op is None):

            # Variable reference. Return its value.
            return lhs

        # We have an operator. Get the value of the RHS.
        rhs = self.rhs
        try:
            rhs = eval_arg(self.rhs, context)
        except AttributeError:
            pass
        
        # Evaluate the expression.
        if (self.op == "="):
            return lhs == rhs
        elif (self.op == ">"):
            return lhs > rhs
        elif (self.op == "<"):
            return lhs < rhs
        elif (self.op == ">="):
            return lhs >= rhs
        elif (self.op == "<="):
            return lhs <= rhs
        elif (self.op == "<>"):
            return lhs != rhs
        else:
            log.error("BoolExprItem: Unknown operator %r" % self.op)
            return False

bool_expr_item = infixNotation(expression,
                               [
                                   ("=", 2, opAssoc.LEFT),
                                   (">", 2, opAssoc.LEFT),
                                   ("<", 2, opAssoc.LEFT),
                                   (">=", 2, opAssoc.LEFT),
                                   ("<=", 2, opAssoc.LEFT),
                                   ("<>", 2, opAssoc.LEFT)
                               ])
bool_expr_item.setParseAction(BoolExprItem)

class BoolExpr(VBA_Object):
    """
    A boolean expression.
    """

    def __init__(self, original_str, location, tokens):
        super(BoolExpr, self).__init__(original_str, location, tokens)
        tokens = tokens[0]
        # Binary boolean operator.
        if ((not hasattr(tokens, "length")) or (len(tokens) > 2)):
            self.lhs = tokens
            try:
                self.lhs = tokens[0]
            except:
                pass
            self.op = None
            self.rhs = None
            try:
                self.op = tokens[1]
                self.rhs = BoolExpr(original_str, location, [tokens[2:], None])
            except:
                pass

        # Unary boolean operator.
        else:
            self.op = tokens[0]
            self.rhs = tokens[1]
            self.lhs = None
            
        log.debug('parsed %r as BoolExpr' % self)

    def __repr__(self):
        if (self.op is not None):
            if (self.lhs is not None):
                return self.lhs.__repr__() + " " + self.op + " " + self.rhs.__repr__()
            else:
                return self.op + " " + self.rhs.__repr__()
        elif (self.lhs is not None):
            return self.lhs.__repr__()
        else:
            log.error("BoolExpr: Improperly parsed.")
            return ""

    def eval(self, context, params=None):

        # Unary operator?
        if (self.lhs is None):

            # We have only a RHS. Evaluate it.
            rhs = None
            try:
                rhs = eval_arg(self.rhs, context)
            except:
                log.error("Boolxpr: Cannot eval " + self.__repr__() + ".")
                return ''

            # Evalue the unary expression.
            if (self.op.lower() == "not"):
                return (not rhs)
            else:
                log.error("BoolExpr: Unknown unary op " + str(self.op))
                return ''
                
        # If we get here we always have a LHS. Evaluate that in the current context.
        lhs = self.lhs
        try:
            lhs = eval_arg(self.lhs, context)
        except AttributeError:
            pass

        # Do we have an operator or just a variable reference?
        if (self.op is None):

            # Variable reference. Return its value.
            return lhs

        # We have an operator. Get the value of the RHS.
        rhs = self.rhs
        try:
            rhs = eval_arg(self.rhs, context)
        except AttributeError:
            pass

        # Evaluate the expression.
        if ((self.op.lower() == "and") or (self.op.lower() == "andalso")):
            return lhs and rhs
        elif ((self.op.lower() == "or") or (self.op.lower() == "orelse")):
            return lhs or rhs
        else:
            log.error("BoolExpr: Unknown operator %r" % self.op)
            return False
    
boolean_expression <<= infixNotation(bool_expr_item,
                                     [
                                         (CaselessKeyword("Not"), 1, opAssoc.RIGHT),
                                         (CaselessKeyword("And"), 2, opAssoc.LEFT),
                                         (CaselessKeyword("AndAlso"), 2, opAssoc.LEFT),
                                         (CaselessKeyword("Or"), 2, opAssoc.LEFT),
                                         (CaselessKeyword("OrElse"), 2, opAssoc.LEFT)
                                     ])
boolean_expression.setParseAction(BoolExpr)

# --- NEW EXPRESSION --------------------------------------------------------------

class New_Expression(VBA_Object):
    def __init__(self, original_str, location, tokens):
        super(New_Expression, self).__init__(original_str, location, tokens)
        self.obj = tokens.expression
        log.debug('parsed %r' % self)

    def __repr__(self):
        return ('New %r' % self.obj)

    def eval(self, context, params=None):
        # TODO: Not sure how to handle this. For now just return what is being created.
        return self.obj

new_expression << CaselessKeyword('New').suppress() + expression('expression')
new_expression.setParseAction(New_Expression)
