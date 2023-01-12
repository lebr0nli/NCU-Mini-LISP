import argparse
import logging
import sys
from contextlib import contextmanager
from math import prod
from types import FunctionType
from typing import Any, Callable, Type, Union

import rich.traceback
from lark import Lark, Token, Transformer, v_args
from lark.exceptions import UnexpectedCharacters, UnexpectedEOF, VisitError
from rich.logging import RichHandler

rich.traceback.install()

argparser = argparse.ArgumentParser(description="Mini Lisp interpreter")
argparser.add_argument("-d", "--debug", action="store_true", help="Enable debug mode")
argparser.add_argument(
    "filename", nargs="?", help="File to run, default will use stdin"
)
mlisp_args = argparser.parse_args()

logging.basicConfig(
    level="DEBUG" if mlisp_args.debug else "INFO",
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True)],
)

logger = logging.getLogger("mlisp")


class MiniLispParser(Lark):
    def __init__(self) -> None:
        with open("mlisp.lark") as f:
            grammar = f.read()
        super().__init__(grammar, start="program")


def lisp_type2py_type(t: str) -> Type:
    if t == "number":
        return int
    elif t == "boolean":
        return bool
    elif t == "closure":
        return FunctionType
    else:
        return Any


def py_type2list_type(t: Type) -> str:
    if t is int:
        return "number"
    elif t is bool:
        return "boolean"
    elif t is FunctionType:
        return "closure"
    return str(t)


@v_args(inline=True)
class MiniLispTransformer(Transformer):
    def __init__(self) -> None:
        self._globals: dict[str, Union[int, bool, Callable]] = {}

        @contextmanager
        def evaluate_closure(
            c: Callable, _globals: dict[str, Union[int, bool, Callable]] = None
        ) -> Callable:
            saved_globals = c._globals
            if _globals is not None:
                c._globals = _globals
            yield c
            c._globals = saved_globals

        def closure(*args: list[Any], _type: Union[str, list[str]]) -> Callable:
            types = [_type] * len(args) if type(_type) is str else _type
            if len(types) < len(args):
                types.extend([Any] * (len(args) - len(types)))

            def _closure(func: Callable) -> Callable:
                def _func() -> Any:
                    new_args = []
                    for arg, t in zip(args, types):
                        py_t = lisp_type2py_type(t)
                        # evaluate the arg first
                        new_arg = arg
                        if type(arg) is FunctionType:
                            with evaluate_closure(arg, _globals=_func._globals):
                                new_arg = arg()
                        elif type(arg) is str:
                            new_arg = _func._globals.get(arg)
                            if new_arg is None:
                                new_arg = self._globals.get(arg)
                            if new_arg is None:
                                raise NameError(f"Symbol {arg!r} is not defined")
                        new_args.append(new_arg)
                        # do type checking
                        if py_t is not Any:
                            if type(new_args[-1]) is not py_t:
                                raise TypeError(
                                    f"Expected {t!r} but got {py_type2list_type(type(new_args[-1]))!r}"
                                )
                    return func(*new_args)

                _func._globals = {}

                return _func

            return _closure

        self.closure: Callable = closure
        self.evaluate_closure: Callable = evaluate_closure

    def number(self, token: Token) -> int:
        return int(token)

    def boolean(self, token: Token) -> bool:
        return str(token) == "#t"

    def variable(self, token: Token) -> str:
        return str(token)

    def evaluate(self, exp: Union[int, bool, Callable]) -> Union[int, bool, Callable]:
        if type(exp) is FunctionType:
            return exp()
        elif type(exp) is str:
            val = self._globals.get(exp)
            if val is None:
                raise NameError(f"Symbol {val!r} is not defined")
            return val
        return exp

    def plus(
        self, x: Union[int, Callable], *xs: tuple[Union[int, Callable]]
    ) -> Callable:
        @self.closure(x, *xs, _type="number")
        def _plus(x: int, *xs: tuple[int]) -> int:
            return x + sum(xs)

        return _plus

    def minus(self, x: Union[int, Callable], y: Union[int, Callable]) -> Callable:
        @self.closure(x, y, _type="number")
        def _minus(x: int, y: int) -> int:
            return x - y

        return _minus

    def multiply(
        self, x: Union[int, Callable], *xs: tuple[Union[int, Callable]]
    ) -> Callable:
        @self.closure(x, *xs, _type="number")
        def _multiply(x: int, *xs: tuple[int]) -> int:
            return x * prod(xs)

        return _multiply

    def divide(self, x: Union[int, Callable], y: Union[int, Callable]) -> Callable:
        @self.closure(x, y, _type="number")
        def _divide(x: int, y: int) -> int:
            return x // y

        return _divide

    def modulus(self, x: Union[int, Callable], y: Union[int, Callable]) -> Callable:
        @self.closure(x, y, _type="number")
        def _modulus(x: int, y: int) -> int:
            return x % y

        return _modulus

    def greater(self, x: Union[int, Callable], y: Union[int, Callable]) -> Callable:
        @self.closure(x, y, _type="number")
        def _greater(x: int, y: int) -> bool:
            return x > y

        return _greater

    def smaller(self, x: Union[int, Callable], y: Union[int, Callable]) -> Callable:
        @self.closure(x, y, _type="number")
        def _smaller(x: int, y: int) -> bool:
            return x < y

        return _smaller

    def equal(self, x: Union[int, Callable], y: Union[int, Callable]) -> Callable:
        @self.closure(x, y, _type="number")
        def _equal(x: int, y: int) -> bool:
            return x == y

        return _equal

    def and_op(
        self, x: Union[bool, Callable], *xs: tuple[Union[bool, Callable]]
    ) -> Callable:
        @self.closure(x, *xs, _type="boolean")
        def _and_op(x: bool, *xs: tuple[bool]) -> bool:
            return x and all(xs)

        return _and_op

    def or_op(
        self, x: Union[bool, Callable], *xs: tuple[Union[bool, Callable]]
    ) -> Callable:
        @self.closure(x, *xs, _type="boolean")
        def _or_op(x: bool, *xs: tuple[bool]) -> bool:
            return x or any(xs)

        return _or_op

    def not_op(self, x: Union[bool, Callable]) -> Callable:
        @self.closure(x, _type="boolean")
        def _not_op(x: bool) -> bool:
            return not x

        return _not_op

    def define(self, var_name: Token, value: Union[int, bool, Callable]) -> None:
        @self.closure(value, _type="any")
        def _define(value: Union[int, bool, Callable]) -> None:
            if _define.scope.get(str(var_name)) is not None:
                raise NameError(f"Symbol {str(var_name)!r} is already defined")
            _define.scope[str(var_name)] = value
            return value

        _define.scope = self._globals

        return _define

    def fun_ids(self, *names: tuple[Token]) -> tuple:
        return tuple(t.value for t in names)

    def fun_body(
        self, *args: tuple[Union[int, bool, Callable]]
    ) -> tuple[tuple[Callable], Callable]:
        return args[:-1], args[-1]

    def fun_exp(
        self, fun_ids: tuple[str], fun_body: Union[int, bool, Callable]
    ) -> Callable:
        fun_body_define_stmts, fun_body_exp = fun_body

        @self.closure(_type="any")
        def _fun_exp() -> Callable:
            _fun_body_exp = (
                fun_body_exp
                if type(fun_body_exp) is FunctionType
                else self.closure(fun_body_exp, _type="any")(lambda x: x)
            )

            def bind(
                *params: tuple[Union[int, bool, Callable]]
            ) -> Union[int, bool, Callable]:
                if len(params) != len(fun_ids):
                    raise TypeError(
                        f"Required {len(fun_ids)} arguments but got {len(params)} arguments"
                    )
                for name, value in zip(fun_ids, params):
                    _fun_body_exp._globals[name] = value
                for define_stmt in fun_body_define_stmts:
                    define_stmt.scope = _fun_body_exp._globals
                    define_stmt._globals = _fun_body_exp._globals
                    define_stmt()

            _fun_body_exp.bind = bind
            return _fun_body_exp

        return _fun_exp

    def anoymous_fun_call(
        self, fun_exp: Callable, *params: tuple[Union[int, bool, Callable]]
    ) -> Callable:
        @self.closure(fun_exp, *params, _type=["closure", "any"])
        def _anoymous_fun_call(
            fun_body: Callable, *params: tuple[Union[int, bool]]
        ) -> Union[int, bool, Callable]:
            with self.evaluate_closure(
                fun_body, _globals=_anoymous_fun_call._globals | fun_body._globals
            ):
                # logger.debug(f"Calling anoymous function")
                fun_body.bind(*params)
                # logger.debug(f"{fun_body._globals=}")
                val = fun_body()
                if type(val) is FunctionType:
                    val._globals = fun_body._globals
                return val

        return _anoymous_fun_call

    def named_fun_call(
        self, fun_name: Token, *params: tuple[Union[int, bool, Callable]]
    ) -> Callable:
        @self.closure(fun_name.value, *params, _type=["closure", "any"])
        def _named_fun_call(
            fun_body: Callable, *params: tuple[Union[int, bool]]
        ) -> Union[int, bool]:
            with self.evaluate_closure(
                fun_body, _globals=_named_fun_call._globals | fun_body._globals
            ):
                # logger.debug(
                #     f"Calling named function {fun_name.value!r}\n{_named_fun_call._globals=}"
                # )
                fun_body.bind(*params)
                # logger.debug(f"{fun_body._globals=}")
                val = fun_body()
                if type(val) is FunctionType:
                    val._globals = fun_body._globals
                return val

        return _named_fun_call

    def if_then_else(
        self,
        test_exp: bool,
        then_exp: Union[int, bool, Callable],
        else_exp: Union[int, bool, Callable],
    ) -> Union[int, bool, Callable]:
        @self.closure(test_exp, _type="boolean")
        def _if_then_else(test_exp: bool) -> Union[int, bool, Callable]:
            exec_exp = then_exp if test_exp else else_exp
            if type(exec_exp) is not FunctionType:
                exec_exp = self.closure(exec_exp, _type="any")(lambda x: x)
            with self.evaluate_closure(exec_exp, _globals=_if_then_else._globals):
                return exec_exp()

        return _if_then_else

    def print_num(self, v: Union[int, bool, Callable]) -> None:
        @self.closure(v, _type="number")
        def _print_num(v: int) -> None:
            print(v)

        return _print_num

    def print_bool(self, v: Union[int, bool, Callable]) -> None:
        @self.closure(v, _type="boolean")
        def _print_bool(v: bool) -> None:
            print("#t" if v else "#f")

        return _print_bool


def main() -> None:
    if mlisp_args.filename:
        with open(mlisp_args.filename) as f:
            data = f.read()
    else:
        data = "".join(sys.stdin)
    parser = MiniLispParser()
    try:
        tree = parser.parse(data)
    except UnexpectedCharacters as e:
        print(f"Syntax errorm, unexpected character: {e.char}")
        print(e._context)
        return
    except UnexpectedEOF as e:
        print("Syntax error, unexpected EOF")
        return
    except Exception as e:
        print("Syntax error")
        return
    logger.debug(tree.pretty())
    transformer = MiniLispTransformer()
    try:
        result = transformer.transform(tree)
        logger.debug(result.pretty())
    except VisitError as e:
        if isinstance(e.orig_exc, TypeError):
            print(f"Type Error: {e.orig_exc}")
        elif isinstance(e.orig_exc, NameError):
            print(f"Name Error: {e.orig_exc}")
        elif isinstance(e.orig_exc, RecursionError):
            print("Recursion Error: Maximum recursion depth exceeded")
        else:
            print("Runtime Error")
            logger.debug(e)


if __name__ == "__main__":
    main()
