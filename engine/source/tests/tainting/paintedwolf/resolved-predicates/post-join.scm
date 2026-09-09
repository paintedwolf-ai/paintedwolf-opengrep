(use-modules ((guile) #:select (string=? not)))
(define (handler value)
;; ruleid: predicate
 (if (string=? value "safe") #t #f) (sink value))
(register handler)
