(use-modules ((guile) #:select (string=? not)))
(define (handler value)
;; ruleid: predicate
 (if (not (string=? value "safe")) (sink value) #f))
(register handler)
