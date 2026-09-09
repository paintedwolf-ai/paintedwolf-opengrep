#| (sink (source)) #| nested comment |# |#
#; (sink (source))
#; #; (source) (sink (source))
'(sink (source))
(quote (sink (source)))
#((sink (source)))
"(sink (source))"
(define (quoted)
  (sink '(source))
  (sink (quote (source)))
  (sink `(source))
  (sink `((source) ,"fixed"))
  ;; ruleid: flow
  (sink `(literal ,(source)))
  ;; ruleid: flow
  (sink (quasiquote (literal (unquote (source)))))
  ;; ruleid: flow
  (sink `(literal ,@(source)))
  (sink ``(literal ,(source)))
  ;; ruleid: flow
  (sink ``(literal ,,(source)))
  ;; ruleid: flow
  (sink `#(literal ,(source))))
(define (unicode-name)
  (let ((|v\x61;lue| (source)))
    ;; ruleid: flow
    (sink value)))
