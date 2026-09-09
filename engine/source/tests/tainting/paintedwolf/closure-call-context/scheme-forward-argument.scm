(define (handler value)
;; ruleid: closure-context
 (let ((helper (lambda (input) input))) (sink (helper value))))
(register handler)
