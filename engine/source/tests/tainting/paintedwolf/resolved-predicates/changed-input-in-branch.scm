(use-modules ((guile) #:select (string=? not)))
(define (handler value)
;; ruleid: predicate
 (if (string=? value "safe") (begin (set! value (source)) (sink value)) #f))
(register handler)
