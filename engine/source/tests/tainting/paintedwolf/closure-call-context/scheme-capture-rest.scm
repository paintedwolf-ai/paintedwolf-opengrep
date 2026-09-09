(define (handler value)
;; ruleid: closure-context
 (let ((helper (lambda args value))) (sink (helper "safe" "more"))))
(register handler)
