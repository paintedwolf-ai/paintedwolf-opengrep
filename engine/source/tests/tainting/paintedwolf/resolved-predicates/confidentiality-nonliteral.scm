(use-modules ((guile) #:select (string=? not)))
(define (handler value)
;; ruleid: predicate
 (sink (string=? value (source))))
(register handler)
