(use-modules ((guile) #:select (string=? not)))
(define (handler value)
;; ruleid: predicate
 (sink (string=? (source) "safe")))
(register handler)
