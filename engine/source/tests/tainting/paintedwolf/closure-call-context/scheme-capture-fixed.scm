(define (handler value)
;; ruleid: closure-context
 (let ((helper (lambda (ignored) value))) (sink (helper "safe"))))
(register handler)
