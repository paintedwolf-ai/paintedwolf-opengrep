(define (handler value)
;; ruleid: closure-context
 (let* ((out value) (helper (lambda (enabled) (if enabled (set! out "safe") #f)))) (helper #f) (sink out)))
(register handler)
