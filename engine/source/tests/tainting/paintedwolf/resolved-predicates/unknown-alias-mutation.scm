(use-modules ((guile) #:select (string=? not)))
(define (handler value)
;; ruleid: predicate
 (let ((alias value)) (if (string=? value "safe") (begin (mutate alias) (sink value)) #f)))
(register handler)
