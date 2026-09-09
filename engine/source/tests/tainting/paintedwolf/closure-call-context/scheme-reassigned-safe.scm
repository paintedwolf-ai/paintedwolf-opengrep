(define (handler value)
;; ok: closure-context
 (let ((helper (lambda (ignored) value))) (set! helper (lambda (ignored) "safe")) (sink (helper "safe"))))
(register handler)
