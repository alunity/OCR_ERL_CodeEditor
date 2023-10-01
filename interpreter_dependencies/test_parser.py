import json
from typing import Iterable, Optional, Type, Callable
from unittest import TestCase

from lexer import Lexer
from parsed_ast import Node, GlobDecl, ArrayDecl, Identifier, IntLiteral, AddOp, MulOp, PowOp, GoToInstr, StrLiteral, NumLiteral, Param, ClassMember, ClassDecl, BoolLiteral
from parsed_token import KNOWN_TOKEN_VALS
from parser import Parser
from tokenizer import Tokenizer


class TestParser(TestCase):
    EXPECTED: dict

    @classmethod
    def setUpClass(cls) -> None:
        with open("parser_test_data.json", "r") as file:
            cls.EXPECTED = json.load(file)

    def setUp(self):
        self.__NODE_TRANSLATORS: dict[Type, Callable] = {
            Node: self.__node_inst2dict,
            GlobDecl: self.__glob_decl2dict,
            ArrayDecl: self.__array_decl2dict,
            Identifier: self.__id2dict,
            IntLiteral: self.__literal2dict,
            StrLiteral: self.__literal2dict,
            NumLiteral: self.__literal2dict,
            BoolLiteral: self.__literal2dict,
            AddOp: self.__operator2dict,
            MulOp: self.__operator2dict,
            PowOp: self.__operator2dict,
            GoToInstr: self.__goto_instr2dict,
            Param: self.__param2dict,
            ClassDecl: self.__class_decl2dict,
            ClassMember: self.__class_member2dict
        }
        self.__NODE_HIERARCHY = {}
        self.maxDiff = None

    def tearDown(self) -> None:
        self.__parser = None
        self.__lexer = None
        self.__tokenizer = None
        self.__NODE_TRANSLATORS = None

    def test_parse_no_lines(self):
        self.__init_parser([])
        self.assertIsNone(self.__parser.parse())

    def test_parse_empty_lines(self):
        self.__init_parser([""] * 100)
        self.assertIsNone(self.__parser.parse())

    def test_parse_whitespace_lines(self):
        self.__init_parser([" " * 100] * 100)
        self.assertIsNone(self.__parser.parse())

    def test_arr_decl(self):
        self.__init_parser(["array x[2,y]"])
        self.__test_node(self.__parser.parse(), "test_arr_decl")

    def test_global_arr_decl(self):
        self.__init_parser(["global array y[3, 5]"])
        self.__test_node(self.__parser.parse(), "test_global_arr_decl")

    def test_arr_decl_no_dims(self):
        with self.assertRaises(SyntaxError) as ex:
            self.__init_parser(["global array y[]"])
            self.__parser.parse()
        self.assertEqual(str(ex.exception), "Syntax error: list of expressions expected")

    def test_arr_decl_no_id(self):
        with self.assertRaises(SyntaxError):
            self.__init_parser(["global array []"])
            self.__parser.parse()

    def test_arr_decl_no_array(self):
        #
        # With no array keyword, the parser should think the statement is a variable assignment
        #
        with self.assertRaises(SyntaxError):
            self.__init_parser(["global x[3,3]"])
            self.__parser.parse()

    def test_var_assign(self):
        self.__init_parser(["x = 3"])
        self.__test_node(self.__parser.parse(), "test_var_assign")

    def test_var_assign_unary_minus(self):
        self.__init_parser(["x = -3 * 5"])
        self.__test_node(self.__parser.parse(), "test_var_assign_unary_minus")

    def test_var_assign_with_expr(self):
        self.__init_parser(["x = 3 + 4 * 5"])
        self.__test_node(self.__parser.parse(), "test_var_assign_with_expr")

    def test_var_assign_with_bool_expr(self):
        self.__init_parser(["x = y == \"3\""])
        self.__test_node(self.__parser.parse(), "test_var_assign_with_bool_expr")

    def test_var_assign_with_longer_bool_expr(self):
        self.__init_parser(["x = NOT (y == 3.09 OR 4 != 6) AND y > 7"])
        self.__test_node(self.__parser.parse(), "test_var_assign_with_longer_bool_expr")

    def test_var_assign_with_longer_expr(self):
        self.__init_parser(["x = -3.2 + 4 * 5 / (5 - 2 ^ 2) MOD (3 DIV 2)"])
        self.__test_node(self.__parser.parse(), "test_var_assign_with_longer_expr")

    def test_field_assign(self):
        self.__init_parser(["x.y = 3"])
        self.__test_node(self.__parser.parse(), "test_field_assign")

    def test_indexed_field_assign(self):
        self.__init_parser(["x.y[0] = 3"])
        self.__test_node(self.__parser.parse(), "test_indexed_field_assign")

    def test_matrix_element_assign(self):
        self.__init_parser(["x.y[0,1] = -3"])
        self.__test_node(self.__parser.parse(), "test_matrix_element_assign")

    def test_field_of_variable_index_assign(self):
        self.__init_parser(["x.y[f(.3)] = 3"])
        self.__test_node(self.__parser.parse(), "test_field_of_variable_index_assign")

    def test_mixed_assign(self):
        self.__init_parser(["x.y[f(g(u.v[1, 2]))] = h(i, k.l[m.o.p, q])"])
        self.__test_node(self.__parser.parse(), "test_mixed_assign")

    def test_callable_member_assign(self):
        self.__init_parser(["f(a).b = c"])
        self.__test_node(self.__parser.parse(), "test_callable_member_assign")

    def test_sub_callable_member_assign(self):
        self.__init_parser(["a.f(b).c = d"])
        self.__test_node(self.__parser.parse(), "test_sub_callable_member_assign")

    def test_long_sub_callable_member_assign(self):
        self.__init_parser(["a.f(b)[c].d = e"])
        self.__test_node(self.__parser.parse(), "test_long_sub_callable_member_assign")

    def test_if_statement(self):
        self.__init_parser([
            "if x == 3 then",
            "x = \"4\"",
            "elseif x == \"4\" then",
            "y = 6.25 + x",
            "else",
            "y = x ^ 2",
            "endif",
        ])
        self.__test_node(self.__parser.parse(), "test_if_statement")

    def test_if_else_if_statement(self):
        self.__init_parser([
            "if x == 3 then",
            "x = 4",
            "elseif x == 4 then",
            "y = -6.0232 + x",
            "endif"
        ])
        self.__test_node(self.__parser.parse(), "test_if_else_if_statement")

    def test_if_statement_with_inner_if(self):
        self.__init_parser([
            "if x == 6 then",
            "    y = 7",
            "    if x == 100 then",
            "        y.z = 3 * 6 ^ x",
            "    endif",
            "elseif x == 7 then",
            "    y.z = 6 * x + x - 3",
            "else",
            "    y.z = (6 + x) == (y DIV 2)",
            "endif"
        ])
        self.__test_node(self.__parser.parse(), "test_if_statement_with_inner_if")

    def test_for_loop(self):
        self.__init_parser([
            "for i = 0 to x",
            "y = i * 2",
            "a = i * 3",
            "next i",
        ])
        self.__test_node(self.__parser.parse(), "test_for_loop")

    def test_for_loop_nested(self):
        self.__init_parser([
            "for i = 0 to n",
            "z = i",
            "for j = 0 to n",
            "x = j",
            "y = i",
            "next j",
            "next i"
        ])
        self.__test_node(self.__parser.parse(), "test_for_loop_nested")

    def test_while_loop(self):
        self.__init_parser([
            "while x == y.z OR 9 == 0",
            "x = \"no \" + x",
            "z = z ^ 2",
            "endwhile"
        ])
        self.__test_node(self.__parser.parse(), "test_while_loop")

    def test_nested_while_loops(self):
        self.__init_parser([
            "while x == y.z AND j == k",
            "x = \"not equal to y.z\"",
            "while a != b",
            "x = y + 1",
            "endwhile",
            "endwhile",
        ])

    def test_do_until_loop(self):
        self.__init_parser([
            "do",
            "x = 3",
            "y = 4 * 6",
            "continue",
            "until y == 24"
        ])
        self.__test_node(self.__parser.parse(), "test_do_until_loop")

    def test_switch_case(self):
        self.__init_parser([
            "switch x:",
            "    case 2:",
            "        x = x ^ 2",
            "    case 3:",
            "        x = 45454 + x",
            "    default:",
            "        x = \"valid case not found\"",
            "endswitch"
        ])
        self.__test_node(self.__parser.parse(), "test_switch_case")

    def test_switch_case_just_default(self):
        self.__init_parser([
            "switch x:",
            "    default:",
            "        x = x ^ 2",
            "endswitch"
        ])
        self.__test_node(self.__parser.parse(), "test_switch_case_just_default")

    def test_switch_case_no_default(self):
        self.__init_parser([
            "switch x:",
            "    case 3444:",
            "        x = x ^ (1 / 2)",
            "endswitch",
        ])
        self.__test_node(self.__parser.parse(), "test_switch_case_no_default")

    def test_mixed_loops_and_ifs(self):
        self.__init_parser([
            "x = 0",
            "if x == 0 then",
            "    for i = 0 to 1000 ^ y",
            "        x = (x + i) ^ 2",
            "    next i",
            "elseif x == k.z[3] then",
            "    do",
            "        j = 0",
            "        while j <= (y MOD 3)",
            "            k.z[j] = y DIV j",
            "            j = j + 1",
            "        endwhile",
            "    until x != k.z[3]",
            "endif"
        ])
        self.__test_node(self.__parser.parse(), "test_mixed_loops_and_ifs")

    def test_print(self):
        self.__init_parser([
            "print(x, y, x + 2, x ^ 2 - 2, f(z.a[3]), b.l.y)"
        ])
        self.__test_node(self.__parser.parse(), "test_print")

    def test_fun_decl(self):
        self.__init_parser([
            "function sum(a, b, c)",
            "    return a + b + c",
            "endfunction",
        ])
        self.__test_node(self.__parser.parse(), "test_fun_decl")

    def test_fun_decl_long_block(self):
        self.__init_parser([
            "function complex_func(a, b, c, d)",
            "    for i = 0 to a",
            "        a = a DIV b MOD c ^ d",
            "        b = b + 1",
            "        if a < b then",
            "            a = a + 1",
            "            c = c DIV 2",
            "        elseif a == b then",
            "            do",
            "                c = c MOD d",
            "            until c == a",
            "        else",
            "            break",
            "        endif",
            "    next i",
            "    return a + b + c + d",
            "endfunction"
        ])
        self.__test_node(self.__parser.parse(), "test_fun_decl_long_block")

    def test_fun_decl_ref_types(self):
        self.__init_parser([
            "function f(a:byRef, b:byVal, c)",
            "    return a * b * c",
            "endfunction",
        ])
        self.__test_node(self.__parser.parse(), "test_fun_decl_ref_types")

    def test_fun_call_no_assign(self):
        self.__init_parser([
            "f()",
            "a.b.c.d()",
            "a.b.c.d(e,f[g],h)",
            "a.b(c,d).e.f(g,h[i])"
        ])
        self.__test_node(self.__parser.parse(), "test_fun_call_no_assign")

    def test_fun_call_in_assign(self):
        self.__init_parser([
            "x = f()",
            "global y = obj1.obj2.f1(a,b).obj3.f2(c,d)"
        ])
        self.__test_node(self.__parser.parse(), "test_fun_call_in_assign")

    def test_proc_decl(self):
        self.__init_parser([
            "procedure sum(a:byRef, b:byVal, c)",
            "    global result = a + b + c",
            "    return",
            "endprocedure"
        ])
        self.__test_node(self.__parser.parse(), "test_proc_decl")

    # will not be testing calling of procedures as there is no distinction made at parsing level
    # between procedure calls and function calls when carried out as singular instructions

    def test_fun_expr(self):
        self.__init_parser([
            "a = int(x)",
            "b = float(y)",
            "c = str(x.y.z)",
            'd = input("Enter a value here: ")',
        ])
        self.__test_node(self.__parser.parse(), "test_fun_expr")

    def test_nested_fun_expr(self):
        self.__init_parser([
            "x.y[0] = int(a.b + str(float(int(str(float(input(\"Enter a number: \")))))))"
        ])
        self.__test_node(self.__parser.parse(), "test_nested_fun_expr")

    def test_str_functions(self):
        self.__init_parser([
            "print(x.y.z.s.length)",
            "print(x.y.z[0].s.substring(2,0))"
        ])
        self.__test_node(self.__parser.parse(), "test_str_functions")

    def test_file_functions(self):
        self.__init_parser([
            "x = openRead(\"filename.txt\")",
            "line = x.readLine()",
            "y = x.writeLine(\"another\" + \" line\")",
            "z = x.endOfFile()",
            "a.b = openWrite(\"filename2.txt\")",
            "x.close()",
            "a.b.close()",
        ])
        self.__test_node(self.__parser.parse(), "test_file_functions")

    def test_class_decl_simple(self):
        self.__init_parser([
            "class A",
            "    __val",
            "    procedure new(val)",
            "        __val = val",
            "    endprocedure",
            "endclass",
        ])
        self.__test_node(self.__parser.parse(), "test_class_decl_simple")

    def test_class_decl_inherit(self):
        self.__init_parser([
            "class B inherits A",
            "    private __val",
            "    public val",
            "    procedure new(v)",
            "        super.new()",
            "        val = v",
            "    endprocedure",
            "endclass",
        ])
        self.__test_node(self.__parser.parse(), "test_class_decl_inherit")

    def test_class_instantiate(self):
        self.__init_parser([
            'a = new A("a" + "b", 3 ^ 2 DIV 6, 2 / 5)'
        ])
        self.__test_node(self.__parser.parse(), "test_class_instantiate")

    # Used for debug

    # def test(self):
    #     self.__init_parser([
    #         "x = 0",
    #         "while x > 2",
    #         "   x = x * 2",
    #         "endwhile",
    #         "x = 2 ^ x",
    #     ])
    #     self.__test_node(self.__parser.parse(), "test")

    # ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- #

    def __test_node(self, node: Optional[Node], expected_json_key: str):
        expected_dict: dict = TestParser.EXPECTED[expected_json_key]
        node_dict: dict = self.__node2dict(node, self.__get_translated_type(type(node)))
        self.assertDictEqual(expected_dict, node_dict)

    @staticmethod
    def __get_node_class(node: Node) -> str:
        """Gets the name of the class that the current node belongs to.

        :param node: AST node to get class name of.
        :return: name of node's class, with no qualifiers.
        """
        return node.__class__.__name__

    def __get_translated_type(self, typ: Type, exclude_current: bool = False) -> Type:
        """Gets the closest ancestor of the given type that has a translating method associated with it.

        :param typ: node type whose translated ancestor to get.
        :param exclude_current: whether to consider the current type its own ancestor or not. It defaults to false.
        :return: ancestor type with a translator.
        """
        if typ not in self.__NODE_HIERARCHY:
            def translated_parent(parent: Type) -> Type:
                if parent in self.__NODE_TRANSLATORS:
                    return parent
                assert len(parent.__bases__) > 0, f"Type {parent.__name__} has no parent"
                return translated_parent(parent.__bases__[0])

            assert len(typ.__bases__) > 0, f"Type {typ.__name__} has no parent"
            self.__NODE_HIERARCHY[typ] = translated_parent(typ.__bases__[0])
        return typ if not exclude_current and typ in self.__NODE_TRANSLATORS else self.__NODE_HIERARCHY[typ]

    def __node2dict(self, node: Node, as_of_type: Type = None) -> dict:
        """Converts the given node into a dictionary that can be used in comparisons.

        :param node: AST node to convert
        :param as_of_type: type to interpret the node as. If None then it is assumed the node's real type. If not None, then it must be an ancestor of the node's type that has a
        translating method associated with it.
        :return: dictionary containing the node's blueprint
        """
        as_of_type = type(node) if as_of_type is None else as_of_type
        assert isinstance(node,
                          as_of_type), f"Node type {TestParser.__get_node_class(node)} does not extend {as_of_type.__name__}"
        assert as_of_type in self.__NODE_TRANSLATORS, f"No translator for type {str(as_of_type)}"
        return self.__NODE_TRANSLATORS[as_of_type](node)

    def __node_inst2dict(self, node: Node) -> dict:
        sub_nodes: list[dict] = [self.__node2dict(sn, self.__get_translated_type(type(sn))) for sn in node.sub_nodes]
        return {TestParser.__get_node_class(node): {Node.SUB_NODES_FIELD: sub_nodes} if sub_nodes else {}}

    def __glob_decl2dict(self, glob_decl: GlobDecl) -> dict:
        result: dict = self.__node2dict(glob_decl, self.__get_translated_type(GlobDecl, True))
        result[TestParser.__get_node_class(glob_decl)][GlobDecl.IS_GLOBAL_FIELD] = str(glob_decl.is_global)
        return result

    def __array_decl2dict(self, array_decl: ArrayDecl) -> dict:
        result: dict = self.__node2dict(array_decl, self.__get_translated_type(ArrayDecl, True))
        node_type = TestParser.__get_node_class(array_decl)
        result[node_type][ArrayDecl.NAME_FIELD] = array_decl.name
        result[node_type][ArrayDecl.DIMS_FIELD] = [self.__node2dict(node) for node in array_decl.dims]
        return result

    def __operator2dict(self, operator: AddOp | MulOp | PowOp):
        result: dict = self.__node2dict(operator, self.__get_translated_type(operator.__class__, True))
        result[TestParser.__get_node_class(operator)][operator.__class__.VAL_FIELD] = KNOWN_TOKEN_VALS[operator.val].value
        return result

    def __id2dict(self, identifier: Identifier) -> dict:
        result: dict = self.__node2dict(identifier, self.__get_translated_type(Identifier, True))
        result[TestParser.__get_node_class(identifier)][Identifier.NAME_FIELD] = identifier.name
        return result

    def __literal2dict(self, literal: IntLiteral | StrLiteral | NumLiteral | BoolLiteral) -> dict:
        result: dict = self.__node2dict(literal, self.__get_translated_type(literal.__class__, True))
        result[TestParser.__get_node_class(literal)][literal.__class__.VAL_FIELD] = literal.val
        return result

    def __goto_instr2dict(self, go_to_instr: GoToInstr) -> dict:
        result: dict = self.__node2dict(go_to_instr, self.__get_translated_type(GoToInstr, True))
        result[TestParser.__get_node_class(go_to_instr)][GoToInstr.VAL_FIELD] = KNOWN_TOKEN_VALS[go_to_instr.val].value
        return result

    def __param2dict(self, param: Param) -> dict:
        result: dict = self.__node2dict(param, self.__get_translated_type(Param, True))
        result[TestParser.__get_node_class(param)][Param.IS_BYREF_FIELD] = str(param.is_byref)
        result[TestParser.__get_node_class(param)][Param.NAME_FIELD] = param.name
        return result

    def __class_decl2dict(self, class_decl: ClassDecl) -> dict:
        result: dict = self.__node2dict(class_decl, self.__get_translated_type(ClassDecl, True))
        result[TestParser.__get_node_class(class_decl)][ClassDecl.PARENT_FIELD] = class_decl.parent
        return result

    def __class_member2dict(self, class_member: ClassMember) -> dict:
        result: dict = self.__node2dict(class_member, self.__get_translated_type(ClassMember, True))
        result[TestParser.__get_node_class(class_member)][ClassMember.IS_PUBLIC_FIELD] = str(class_member.is_public)
        return result
    # ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- #

    def __init_parser(self, lines: Iterable[str]):
        self.__tokenizer = Tokenizer()
        self.__lexer = Lexer(self.__tokenizer, lines)
        self.__parser = Parser(self.__lexer)