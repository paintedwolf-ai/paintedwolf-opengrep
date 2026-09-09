module G = AST_generic

(* Builtin ancestry is defined by the Python exception hierarchy:
 * https://docs.python.org/3/library/exceptions.html#exception-hierarchy *)
let parents =
  [
    ("ArithmeticError", [ "Exception" ]);
    ("AssertionError", [ "Exception" ]);
    ("AttributeError", [ "Exception" ]);
    ("BaseException", []);
    ("BaseExceptionGroup", [ "BaseException" ]);
    ("BlockingIOError", [ "OSError" ]);
    ("BrokenPipeError", [ "ConnectionError" ]);
    ("BufferError", [ "Exception" ]);
    ("BytesWarning", [ "Warning" ]);
    ("ChildProcessError", [ "OSError" ]);
    ("ConnectionAbortedError", [ "ConnectionError" ]);
    ("ConnectionError", [ "OSError" ]);
    ("ConnectionRefusedError", [ "ConnectionError" ]);
    ("ConnectionResetError", [ "ConnectionError" ]);
    ("DeprecationWarning", [ "Warning" ]);
    ("EOFError", [ "Exception" ]);
    ("Exception", [ "BaseException" ]);
    ("ExceptionGroup", [ "BaseExceptionGroup"; "Exception" ]);
    ("FileExistsError", [ "OSError" ]);
    ("FileNotFoundError", [ "OSError" ]);
    ("FloatingPointError", [ "ArithmeticError" ]);
    ("FutureWarning", [ "Warning" ]);
    ("GeneratorExit", [ "BaseException" ]);
    ("ImportError", [ "Exception" ]);
    ("ImportWarning", [ "Warning" ]);
    ("IndentationError", [ "SyntaxError" ]);
    ("IndexError", [ "LookupError" ]);
    ("InterruptedError", [ "OSError" ]);
    ("IsADirectoryError", [ "OSError" ]);
    ("KeyError", [ "LookupError" ]);
    ("KeyboardInterrupt", [ "BaseException" ]);
    ("LookupError", [ "Exception" ]);
    ("MemoryError", [ "Exception" ]);
    ("ModuleNotFoundError", [ "ImportError" ]);
    ("NameError", [ "Exception" ]);
    ("NotADirectoryError", [ "OSError" ]);
    ("NotImplementedError", [ "RuntimeError" ]);
    ("OSError", [ "Exception" ]);
    ("OverflowError", [ "ArithmeticError" ]);
    ("PendingDeprecationWarning", [ "Warning" ]);
    ("PermissionError", [ "OSError" ]);
    ("ProcessLookupError", [ "OSError" ]);
    ("PythonFinalizationError", [ "RuntimeError" ]);
    ("RecursionError", [ "RuntimeError" ]);
    ("ReferenceError", [ "Exception" ]);
    ("ResourceWarning", [ "Warning" ]);
    ("RuntimeError", [ "Exception" ]);
    ("RuntimeWarning", [ "Warning" ]);
    ("StopAsyncIteration", [ "Exception" ]);
    ("StopIteration", [ "Exception" ]);
    ("SyntaxError", [ "Exception" ]);
    ("SyntaxWarning", [ "Warning" ]);
    ("SystemError", [ "Exception" ]);
    ("SystemExit", [ "BaseException" ]);
    ("TabError", [ "IndentationError" ]);
    ("TimeoutError", [ "OSError" ]);
    ("TypeError", [ "Exception" ]);
    ("UnboundLocalError", [ "NameError" ]);
    ("UnicodeDecodeError", [ "UnicodeError" ]);
    ("UnicodeEncodeError", [ "UnicodeError" ]);
    ("UnicodeError", [ "ValueError" ]);
    ("UnicodeTranslateError", [ "UnicodeError" ]);
    ("UnicodeWarning", [ "Warning" ]);
    ("UserWarning", [ "Warning" ]);
    ("ValueError", [ "Exception" ]);
    ("Warning", [ "Exception" ]);
    ("ZeroDivisionError", [ "ArithmeticError" ]);
  ]

let simple_constructors =
  [
    "ArithmeticError";
    "AssertionError";
    "BaseException";
    "BufferError";
    "BytesWarning";
    "DeprecationWarning";
    "EOFError";
    "Exception";
    "FloatingPointError";
    "FutureWarning";
    "GeneratorExit";
    "ImportWarning";
    "IndexError";
    "KeyError";
    "KeyboardInterrupt";
    "LookupError";
    "MemoryError";
    "NotImplementedError";
    "OverflowError";
    "PendingDeprecationWarning";
    "PythonFinalizationError";
    "RecursionError";
    "ReferenceError";
    "ResourceWarning";
    "RuntimeError";
    "RuntimeWarning";
    "StopAsyncIteration";
    "SyntaxWarning";
    "SystemError";
    "TypeError";
    "UnboundLocalError";
    "UnicodeError";
    "UnicodeWarning";
    "UserWarning";
    "ValueError";
    "Warning";
    "ZeroDivisionError";
  ]

let builtin_name = function
  | G.Id ((name, _), info) when Option.is_none !(info.G.id_resolved) ->
      let name =
        match name with
        | "IOError"
        | "EnvironmentError" ->
            "OSError"
        | name -> name
      in
      if List.mem_assoc name parents then Some name else None
  | _ -> None

let constructor expression arguments =
  match expression.G.e with
  | G.N name -> (
      match builtin_name name with
      | Some name
        when List.mem name simple_constructors
             && List.for_all
                  (function
                    | G.Arg _ -> true
                    | _ -> false)
                  arguments ->
          Some name
      | _ -> None)
  | _ -> None

let collect_types convert values =
  List.fold_left
    (fun previous value ->
      Option.bind previous (fun previous ->
          Option.map (fun names -> previous @ names) (convert value)))
    (Some []) values

let rec expression_types expression =
  match expression.G.e with
  | G.N name -> Option.map (fun name -> [ name ]) (builtin_name name)
  | G.Container (G.Tuple, (_, values, _)) ->
      collect_types expression_types values
  | _ -> None

let rec catch_types type_ =
  match type_.G.t with
  | G.TyExpr expression -> expression_types expression
  | G.TyN name -> Option.map (fun name -> [ name ]) (builtin_name name)
  | G.TyTuple (_, types, _) -> collect_types catch_types types
  | _ -> None

let rec is_subclass actual expected =
  String.equal actual expected
  || List.exists
       (fun parent -> is_subclass parent expected)
       (Option.value ~default:[] (List.assoc_opt actual parents))
