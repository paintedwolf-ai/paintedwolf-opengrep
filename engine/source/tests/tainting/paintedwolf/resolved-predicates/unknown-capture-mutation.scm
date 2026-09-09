(use-modules ((guile) #:select (string=? not)))
(define (handler value)
;; ruleid: predicate
 (if (string=? value "safe") (begin (mutate-captured) (sink value)) #f))
(register handler)
