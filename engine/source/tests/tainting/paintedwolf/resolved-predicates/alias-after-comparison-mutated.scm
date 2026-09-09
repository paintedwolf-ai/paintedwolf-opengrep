(use-modules ((guile) #:select (string=? not)))
(define (handler value)
;; ruleid: predicate
 (if (string=? value "safe") (let ((alias value)) (mutate alias) (sink alias)) #f))
(register handler)
