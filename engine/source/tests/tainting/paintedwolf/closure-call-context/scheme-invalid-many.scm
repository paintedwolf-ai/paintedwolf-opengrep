(define (handler value)
;; ok: closure-context
 (let ((helper (lambda () value))) (sink (helper "safe"))))
(register handler)
