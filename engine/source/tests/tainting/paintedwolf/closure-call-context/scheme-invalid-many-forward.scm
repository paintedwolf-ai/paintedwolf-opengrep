(define (handler value)
;; ok: closure-context
 (let ((helper (lambda (a) a))) (sink (helper value "extra"))))
(register handler)
