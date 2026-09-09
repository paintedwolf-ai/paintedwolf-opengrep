(define (handler value)
;; ruleid: closure-context
 (let ((helper (lambda () value))) (sink (helper))))
(register handler)
