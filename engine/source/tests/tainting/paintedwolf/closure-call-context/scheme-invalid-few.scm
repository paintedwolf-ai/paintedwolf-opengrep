(define (handler value)
;; ok: closure-context
 (let ((helper (lambda (a b) value))) (sink (helper "safe"))))
(register handler)
