(define (handler value)
;; ok: closure-context
 (let* ((out value) (helper (lambda (ignored) (set! out "safe")))) (helper "safe") (sink out)))
(register handler)
