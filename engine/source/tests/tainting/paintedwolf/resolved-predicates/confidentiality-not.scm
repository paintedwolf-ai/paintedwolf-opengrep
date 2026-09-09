(use-modules ((guile) #:select (string=? not)))
(define (handler value)
;; ruleid: predicate
 (sink (not (string=? value "safe"))))
(register handler)
