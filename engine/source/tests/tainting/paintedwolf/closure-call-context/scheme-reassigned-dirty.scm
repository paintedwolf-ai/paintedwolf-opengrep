(define (handler value)
;; ruleid: closure-context
 (let ((helper (lambda (ignored) "safe"))) (set! helper (lambda (ignored) value)) (sink (helper "safe"))))
(register handler)
