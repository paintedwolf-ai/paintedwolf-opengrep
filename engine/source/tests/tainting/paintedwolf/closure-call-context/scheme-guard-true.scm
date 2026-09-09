(define (handler value)
;; ruleid: closure-context
 (let ((helper (lambda (enabled) (if enabled value "safe")))) (sink (helper #t))))
(register handler)
