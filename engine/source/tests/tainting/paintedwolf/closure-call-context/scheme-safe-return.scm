(define (handler value)
;; ok: closure-context
 (let ((helper (lambda args "safe"))) (sink (helper value))))
(register handler)
