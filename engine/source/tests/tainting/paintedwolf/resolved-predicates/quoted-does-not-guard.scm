(use-modules ((guile) #:select (string=? not)))
(define (handler value)
;; ruleid: predicate
 '(string=? value "safe") (sink value))
(register handler)
