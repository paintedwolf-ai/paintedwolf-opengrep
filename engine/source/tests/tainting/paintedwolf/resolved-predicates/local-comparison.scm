(use-modules ((guile) #:select (string=? not)))
(define (handler value)
;; ruleid: predicate
 (let ((string=? (lambda args #t))) (if (string=? value "safe") (sink value) #f)))
(register handler)
