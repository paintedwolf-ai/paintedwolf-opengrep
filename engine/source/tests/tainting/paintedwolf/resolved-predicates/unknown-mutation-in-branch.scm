(use-modules ((guile) #:select (string=? not)))
(define (handler value)
;; ruleid: predicate
 (if (string=? value "safe") (begin (mutate value) (sink value)) #f))
(register handler)
