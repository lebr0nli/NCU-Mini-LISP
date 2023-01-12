# Mini LISP

> NCU 2022 Compiler Final Project

For detailed description of this simplified lisp variant, see [project_description](./project_description/).

## Environment

- python 3.9

- dependencies:

```shell
pip install -U lark rich
```

## Usage

```text
usage: mlisp.py [-h] [-d] [filename]

Mini Lisp interpreter

positional arguments:
  filename     File to run, default will use stdin

optional arguments:
  -h, --help   show this help message and exit
  -d, --debug  Enable debug mode
```

## Try with docker

```shell
# build image
docker build .
# map stdin to test.lsp and run the script
docker run --rm -i mlisp < test.lsp
```

## Examples

```shell
$ cat test.lsp
(define add-x
    (fun (x)
        (define z
            (fun (k) (+ x k 1))
        )
        (fun (y) (+ x y (z 9)))
    )
)

(define z (add-x 10))

(print-num (z 20))
$ python mlisp.py < test.lsp
50
$ python mlisp.py test.lsp
50
$ python mlisp.py -d test.lsp
[10:45:10] DEBUG    program                                                                        mlisp.py:363
                      evaluate
                        define
                          add-x
                          fun_exp
                            fun_ids x
                            fun_body
                              define
                                z
                                fun_exp
                                  fun_ids   k
                                  fun_body
                                    plus
                                      variable      x
                                      variable      k
                                      number        1
                              fun_exp
                                fun_ids     y
                                fun_body
                                  plus
                                    variable        x
                                    variable        y
                                    named_fun_call
                                      z
                                      number        9
                      evaluate
                        define
                          z
                          named_fun_call
                            add-x
                            number  10
                      evaluate
                        print_num
                          named_fun_call
                            z
                            number  20

50
           DEBUG    program                                                                        mlisp.py:367
                      <function
                    MiniLispTransformer.__init__.<locals>.closure.<locals>._closure.<locals>._func
                    at 0x106deaaf0>
                      <function
                    MiniLispTransformer.__init__.<locals>.closure.<locals>._closure.<locals>._func
                    at 0x106dea9d0>
                      None

```
