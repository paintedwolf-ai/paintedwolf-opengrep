#ifndef OPENGREP_NATIVE_SCRIPT_BINDINGS_H
#define OPENGREP_NATIVE_SCRIPT_BINDINGS_H
#include <tree_sitter/api.h>
#include <caml/mlvalues.h>
value octs_create_native_parser(const TSLanguage *grammar);
#endif
