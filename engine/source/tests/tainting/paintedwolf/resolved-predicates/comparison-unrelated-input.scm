(use-modules ((guile) #:select (string=? not)))
(define (handler value)
;; ruleid: predicate
 (if (string=? "safe" "safe") (sink value) #f))
(register handler)
