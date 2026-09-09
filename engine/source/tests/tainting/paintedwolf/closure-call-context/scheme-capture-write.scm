(define (handler value)
;; ruleid: closure-context
 (let* ((out "safe") (helper (lambda (ignored) (set! out value)))) (helper "safe") (sink out)))
(register handler)
