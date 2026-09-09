(define (handler value)
;; ok: closure-context
 (let ((helper (lambda (a b) a))) (sink (helper value))))
(register handler)
