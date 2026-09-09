(define (handler value)
;; ok: closure-context
 (let ((helper (lambda (enabled) (if enabled value "safe")))) (sink (helper #f))))
(register handler)
